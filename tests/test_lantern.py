import json

import pytest

from game.constants import COLOR_HUD_HP_LOW, FOG_RADIUS
from game.fog import update_fog
from game.hud import render_hud
from game.input import EMPTY_INPUT, Action, InputState
from game.lantern import fuel_share, lantern_capacity, light_radius, update_lantern
from game.loop import STEP
from game.objects.registry import LANTERN
from game.persistence import load_game, save_game, save_path
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run, step_game
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def test_light_radius_follows_fuel():
    state = GameState()
    state.lantern_fuel = lantern_capacity(state)
    assert light_radius(state) == FOG_RADIUS
    state.lantern_fuel = 0
    assert light_radius(state) == LANTERN["min_radius"]
    state.lantern_fuel = lantern_capacity(state) / 2
    assert LANTERN["min_radius"] < light_radius(state) < FOG_RADIUS


@pytest.mark.parametrize(
    "x,y,biome", [(20, 20, "meadow"), (80, 20, "hillside"), (80, 60, "river"), (150, 40, "cave")]
)
def test_fuel_burns_at_the_biome_rate(x, y, biome):
    state = GameState(player_x=x, player_y=y, lantern_fuel=100.0)
    update_lantern(state, 10.0)
    assert state.lantern_fuel == pytest.approx(100.0 - 10.0 * LANTERN["drain"][biome])


def test_caves_burn_fastest_and_town_refills():
    state = GameState(player_x=150, player_y=40, lantern_fuel=50.0)
    update_lantern(state, 1000.0)
    assert state.lantern_fuel == 0.0
    state.player_x, state.player_y = 100, 40
    update_lantern(state, STEP)
    assert fuel_share(state) == 1.0


def test_seen_area_shrinks_as_the_light_fades():
    state = new_run(3)
    state.player_x, state.player_y = 60, 20
    update_fog(state)
    full = len(state.visible_tiles)
    state.lantern_fuel = 0
    update_fog(state)
    assert len(state.visible_tiles) < full


def test_running_out_of_light_never_hurts():
    state = new_run(3)
    state.player_x, state.player_y = 150, 40
    state.lantern_fuel = 0
    state.enemies = []
    state.spawn_timer = -1e9  # keep enemies away; this is about the lantern alone
    for _ in range(300):
        step_game(EMPTY_INPUT, state, STEP)
    assert state.player_hp == state.player_max_hp
    assert state.active_scene == "game"


def test_better_lantern_can_be_bought_and_comes_full():
    state = GameState(active_scene="shop", shop_tab=1, player_gold=1000, lantern_fuel=1.0)
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "lantern")
    update_shop(CONFIRM, state)
    assert state.lantern_level == 1
    assert state.lantern_fuel == lantern_capacity(state) == LANTERN["capacities"][1]
    assert state.player_gold == 1000 - LANTERN["costs"][1]


def test_hud_shows_light_and_warns_when_low(stub_renderer):
    state = GameState()
    render_hud(stub_renderer, state)
    row = "".join(stub_renderer.get_cell(x, 22)[0] for x in range(80))
    assert "Light:100%" in row
    state.lantern_fuel = lantern_capacity(state) * 0.1
    render_hud(stub_renderer, state)
    row = "".join(stub_renderer.get_cell(x, 22)[0] for x in range(80))
    at = row.index("Light:")
    assert stub_renderer.get_cell(at, 22)[1] == COLOR_HUD_HP_LOW


def test_lantern_is_saved_and_older_saves_get_a_full_basic_lantern():
    state = new_run(4)
    state.lantern_level, state.lantern_fuel = 2, 123.5
    save_game(state)
    loaded = load_game()
    assert (loaded.lantern_level, loaded.lantern_fuel) == (2, 123.5)

    with open(save_path()) as f:
        data = json.load(f)
    data["schema_version"] = 4
    del data["lantern"]
    with open(save_path(), "w") as f:
        json.dump(data, f)
    loaded = load_game()
    assert loaded.lantern_level == 0 and fuel_share(loaded) == 1.0
