import json
import os

import pytest

from game import persistence
from game.gems import add_polished_gem
from game.input import Action, InputState
from game.loop import STEP
from game.menu import MENU_ITEMS, _select_menu_item, render_menu, update_menu
from game.persistence import (
    SCHEMA_VERSION,
    SaveLoadError,
    _decode_fog,
    has_save,
    import_legacy_files,
    load_game,
    save_game,
    save_path,
)
from game.scenes.save_point import update_save_point
from game.simulation import new_run, step_game
from game.state import GameState
from game.tools import _deplete_tile
from game.world import WORLDGEN_VERSION

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def _played_run(seed=11, steps=600):
    state = new_run(seed)
    script = [Action.MOVE_LEFT, Action.USE, Action.MOVE_UP, Action.USE, Action.MOVE_DOWN]
    for i in range(steps):
        pressed = {script[(i // 5) % len(script)]} if i % 5 == 0 else set()
        step_game(InputState(pressed=frozenset(pressed)), state, STEP)
        state.active_scene = "game"
    for coord in [(5, 5), (60, 10), (150, 70)]:
        _deplete_tile(state, *coord)
    state.world_gems.pop(next(iter(state.world_gems)))  # a gem the player picked up
    state.player_gold = 321
    state.lifetime_earnings = 999
    state.lapidary_level = 2
    state.inventory["gems"]["ruby"] = 3
    state.inventory["tools"]["pickaxe"] = {"level": 2}
    add_polished_gem(state, "ruby", 77)
    add_polished_gem(state, "ruby", 91)
    return state


def _fog_cells(state):
    return [
        state.world_tiles.meta[(x, y)]["visibility"]
        for y in range(state.world_tiles.height)
        for x in range(state.world_tiles.width)
    ]


def _progress(state):
    return (
        state.seed,
        state.player_x,
        state.player_y,
        state.player_hp,
        state.player_gold,
        state.lifetime_earnings,
        state.equipped_tool,
        state.inventory,
        state.polished_gem_values,
        state.lapidary_level,
    )


@pytest.fixture(scope="module")
def played():
    return _played_run()


# ── Round trip ────────────────────────────────────────────────────────────────


def test_round_trip_restores_progress_map_and_rng(played):
    assert save_game(played) is None
    loaded = load_game()

    assert _progress(loaded) == _progress(played)
    assert loaded.depleted_tiles == played.depleted_tiles
    assert loaded.world_gems == played.world_gems
    assert _fog_cells(loaded) == _fog_cells(played)
    assert loaded.visible_tiles == played.visible_tiles
    assert loaded.rng.getstate() == played.rng.getstate()


def test_continued_run_keeps_the_same_roll_sequence(played):
    save_game(played)
    loaded = load_game()
    assert [loaded.rng.random() for _ in range(5)] == [played.rng.random() for _ in range(5)]


def test_save_is_versioned_and_compact():
    state = new_run(3)
    for coord in state.world_tiles.meta:
        state.world_tiles.meta[coord]["visibility"] = "explored"
    save_game(state)

    with open(save_path()) as f:
        raw = f.read()
    data = json.loads(raw)
    assert data["schema_version"] == SCHEMA_VERSION
    assert data["worldgen_version"] == WORLDGEN_VERSION
    # A fully explored map used to take ~800 KB with one JSON entry per tile.
    assert len(raw) < 20_000
    assert set(_decode_fog(data["fog"])) == {"explored"}


# ── Migration ─────────────────────────────────────────────────────────────────


def _legacy_save():
    legacy = {
        "seed": 42,
        "player": {
            "x": 100,
            "y": 40,
            "hp": 17,
            "max_hp": 20,
            "gold": 80,
            "lifetime_earnings": 30,
            "equipped_tool": "shovel",
            "has_won": False,
        },
        "inventory": {"gems": {"quartz": 2}, "tools": {"shovel": 1}, "loot": {}},
        "polished_gem_values": {},
        "lapidary_level": 1,
        "depleted_tiles": [[10, 10]],
        "fog": [[100, 40, "visible"], [101, 40, "explored"]],
    }
    with open(save_path(), "w") as f:
        json.dump(legacy, f)


def test_unversioned_legacy_save_is_migrated(monkeypatch):
    # Unversioned saves were written by world generator v1; pin it to check the map data.
    monkeypatch.setattr("game.world.WORLDGEN_VERSION", 1)
    _legacy_save()
    loaded = load_game()

    assert loaded.player_gold == 80
    assert loaded.inventory["gems"] == {"quartz": 2}
    assert (10, 10) in loaded.depleted_tiles
    assert loaded.world_tiles.meta[(100, 40)]["visibility"] == "visible"
    assert loaded.world_tiles.meta[(101, 40)]["visibility"] == "explored"
    assert loaded.world_tiles.meta[(0, 0)]["visibility"] == "unseen"


def test_legacy_save_from_an_older_world_generator_keeps_progress():
    _legacy_save()
    loaded = load_game()
    assert loaded.player_gold == 80
    assert loaded.inventory["gems"] == {"quartz": 2}
    assert loaded.depleted_tiles == set()
    assert "update" in loaded.hud_message


def test_save_from_a_newer_version_is_refused_and_left_untouched():
    with open(save_path(), "w") as f:
        json.dump({"schema_version": SCHEMA_VERSION + 1}, f)

    with pytest.raises(SaveLoadError, match="newer version"):
        load_game()
    assert has_save()
    assert not os.path.exists(save_path() + ".bak")


def test_world_generator_change_keeps_progress_and_resets_the_map(played, monkeypatch):
    save_game(played)
    monkeypatch.setattr("game.world.WORLDGEN_VERSION", WORLDGEN_VERSION + 1)

    loaded = load_game()

    assert loaded.player_gold == played.player_gold
    assert loaded.inventory == played.inventory
    assert loaded.depleted_tiles == set()
    assert (loaded.player_x, loaded.player_y) == loaded.world_tiles.start_pos
    assert "update" in loaded.hud_message


# ── Failures ──────────────────────────────────────────────────────────────────


def test_damaged_save_is_backed_up_and_reported():
    with open(save_path(), "w") as f:
        f.write('{"seed": 1, "player": ')

    with pytest.raises(SaveLoadError, match="damaged"):
        load_game()
    assert not has_save()
    assert os.path.exists(save_path() + ".bak")


def test_menu_shows_load_error_instead_of_crashing():
    with open(save_path(), "w") as f:
        f.write("not json")
    state = GameState()
    state.menu_cursor = [item_id for item_id, _ in MENU_ITEMS].index("continue")
    _select_menu_item(state, save_exists=True)
    assert state.active_scene == "menu"
    assert "damaged" in state.menu_notice


def test_failed_save_returns_an_error_and_the_hud_says_so(tmp_path, monkeypatch, played):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("")
    monkeypatch.setenv(persistence.DATA_DIR_ENV, str(blocker / "data"))

    assert save_game(played).startswith("Save failed")

    played.active_scene = "save_point"
    update_save_point(CONFIRM, played)
    assert played.hud_message.startswith("Save failed")


def test_successful_save_point_confirms(played):
    played.active_scene = "save_point"
    update_save_point(CONFIRM, played)
    assert played.hud_message == "Game Saved!"
    assert has_save()


# ── Locations ─────────────────────────────────────────────────────────────────


def test_data_dir_honors_override(isolated_data_dir):
    assert save_path() == str(isolated_data_dir / "save.json")
    assert isolated_data_dir.is_dir()


def test_legacy_files_are_imported_once(tmp_path):
    legacy_dir = tmp_path / "game_folder"
    legacy_dir.mkdir()
    (legacy_dir / "save.json").write_text('{"old": 1}')
    (legacy_dir / "leaderboard.json").write_text('{"runs": []}')

    import_legacy_files(str(tmp_path / "elsewhere"), str(legacy_dir))
    assert json.loads(open(save_path()).read()) == {"old": 1}

    # Even if the current save later disappears (e.g. moved aside as damaged), the
    # stale legacy save must not come back.
    os.remove(save_path())
    import_legacy_files(str(legacy_dir))
    assert not has_save()


@pytest.mark.parametrize(
    "payload",
    ["null", "[]", '"text"', '{"seed": 1, "player": {}, "inventory": []}'],
)
def test_wrongly_shaped_save_is_reported_as_damaged(payload):
    with open(save_path(), "w") as f:
        f.write(payload)
    with pytest.raises(SaveLoadError, match="damaged"):
        load_game()
    assert os.path.exists(save_path() + ".bak")


def test_damaged_fog_field_is_reported_as_damaged(played):
    save_game(played)
    with open(save_path()) as f:
        data = json.load(f)
    data["fog"] = [1]
    with open(save_path(), "w") as f:
        json.dump(data, f)
    with pytest.raises(SaveLoadError):
        load_game()


def test_unusable_data_dir_does_not_crash_the_menu(tmp_path, monkeypatch, stub_renderer):
    blocker = tmp_path / "not_a_dir"
    blocker.write_text("")
    monkeypatch.setenv(persistence.DATA_DIR_ENV, str(blocker / "data"))

    import_legacy_files(str(tmp_path))
    assert not has_save()
    assert persistence.load_leaderboard() == []
    render_menu(stub_renderer, GameState())
    update_menu(InputState(pressed=frozenset({Action.MOVE_DOWN})), GameState())


def test_first_save_creates_the_data_dir(tmp_path, monkeypatch, played):
    target = tmp_path / "fresh" / "nested"
    monkeypatch.setenv(persistence.DATA_DIR_ENV, str(target))
    assert not target.exists()
    assert save_game(played) is None
    assert (target / "save.json").is_file()


def test_v1_polished_prices_become_one_price_per_gem(monkeypatch):
    monkeypatch.setattr("game.world.WORLDGEN_VERSION", 1)
    v1 = {
        "schema_version": 1,
        "worldgen_version": 1,
        "seed": 42,
        "player": {
            "x": 100,
            "y": 40,
            "hp": 20,
            "max_hp": 20,
            "gold": 50,
            "lifetime_earnings": 0,
            "equipped_tool": "shovel",
            "has_won": False,
        },
        "inventory": {"gems": {"ruby_polished": 3, "opal_polished": 0}, "tools": {}, "loot": {}},
        "polished_gem_values": {"ruby_polished": 400, "opal_polished": 90},
        "lapidary_level": 1,
        "depleted_tiles": [],
        "fog": "",
    }
    with open(save_path(), "w") as f:
        json.dump(v1, f)
    loaded = load_game()
    assert loaded.polished_gem_values == {"ruby_polished": [400, 400, 400]}


def test_bag_level_round_trips_and_older_saves_get_the_basic_bag(played):
    played.bag_level = 2
    save_game(played)
    assert load_game().bag_level == 2

    with open(save_path()) as f:
        data = json.load(f)
    data["schema_version"] = 2
    del data["bag_level"]
    with open(save_path(), "w") as f:
        json.dump(data, f)
    assert load_game().bag_level == 0


def test_autosave_only_while_a_run_is_being_played(played):
    from game.persistence import autosave_allowed

    for scene in ("game", "shop", "lapidary", "save_point"):
        played.active_scene = scene
        assert autosave_allowed(played)
    for scene in ("menu", "death", "win", "daily_end", "perks", "leaderboard"):
        played.active_scene = scene
        assert not autosave_allowed(played)
    played.active_scene, played.daily = "game", "2026-10-08"
    assert not autosave_allowed(played)
    played.daily = None


def test_migrated_run_id_is_stable_across_reloads(played):
    save_game(played)
    with open(save_path()) as f:
        data = json.load(f)
    data["schema_version"] = 9
    del data["run_id"]
    with open(save_path(), "w") as f:
        json.dump(data, f)
    first, second = load_game().run_id, load_game().run_id
    assert first == second and len(first) == 32
