import json
import time

import pytest

from game.constants import FOG_RADIUS, MAP_HEIGHT, MAP_WIDTH
from game.fog import update_fog
from game.persistence import load_game, save_game
from game.state import GameState
from game.world import generate_world

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(player_x: int = 100, player_y: int = 40) -> GameState:
    """Build a minimal GameState with a real generated world."""
    state = GameState()
    state.seed = 42
    state.world_tiles, state.world_gems = generate_world(42)
    state.player_x = player_x
    state.player_y = player_y
    return state


# ---------------------------------------------------------------------------
# update_fog tests
# ---------------------------------------------------------------------------


def test_update_fog_marks_nearby_tiles_visible():
    """Tile at player position must be marked 'visible' after update_fog."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    assert state.world_tiles.meta[(100, 40)]["visibility"] == "visible"


def test_update_fog_visible_radius():
    """All meta tiles within Chebyshev distance <= FOG_RADIUS should be 'visible'."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    # Check a tile exactly at the edge of the radius
    edge_x = 100 + FOG_RADIUS
    edge_y = 40
    if (edge_x, edge_y) in state.world_tiles.meta:
        assert state.world_tiles.meta[(edge_x, edge_y)]["visibility"] == "visible"

    # Check a tile closer than radius
    near_x = 100 + (FOG_RADIUS - 1)
    if (near_x, edge_y) in state.world_tiles.meta:
        assert state.world_tiles.meta[(near_x, edge_y)]["visibility"] == "visible"


def test_update_fog_marks_old_visible_as_explored():
    """Tiles visible from prior position should become 'explored' when player moves away."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    # Confirm center tile is visible
    assert state.world_tiles.meta[(100, 40)]["visibility"] == "visible"

    # Move player well outside the original radius
    state.player_x = 100 + FOG_RADIUS + 5
    state.player_y = 40
    update_fog(state)

    # Original center tile should now be 'explored'
    assert state.world_tiles.meta[(100, 40)]["visibility"] == "explored"


def test_update_fog_unseen_far_tile_stays_unseen():
    """Tile far from the player should remain 'unseen' after update_fog."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)

    # (0, 0) is far from (100, 40) — Chebyshev distance is 100, >> FOG_RADIUS
    if (0, 0) in state.world_tiles.meta:
        assert state.world_tiles.meta[(0, 0)]["visibility"] == "unseen"

    # Also check a tile near the map edge
    far_x = min(199, MAP_WIDTH - 1)
    far_y = min(79, MAP_HEIGHT - 1)
    if (far_x, far_y) in state.world_tiles.meta:
        assert state.world_tiles.meta[(far_x, far_y)]["visibility"] == "unseen"


def test_update_fog_updates_visible_tiles_set():
    """After update_fog, visible_tiles set must be non-empty and match meta."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)

    assert len(state.visible_tiles) > 0
    for coord in state.visible_tiles:
        assert state.world_tiles.meta[coord]["visibility"] == "visible"


def test_update_fog_visible_tiles_cleared_on_move():
    """After moving, the old visible_tiles should no longer be in the set."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    old_visible = set(state.visible_tiles)

    state.player_x = 100 + FOG_RADIUS + 5
    state.player_y = 40
    update_fog(state)

    # Old center (100,40) must not be visible anymore (it's now explored)
    assert old_visible  # sanity: we did have visible tiles before
    assert (100, 40) not in state.visible_tiles


def test_update_fog_performance():
    """30 frames of update_fog should complete in under 0.1 seconds."""
    state = _make_state(player_x=100, player_y=40)

    start = time.perf_counter()
    for _ in range(30):
        update_fog(state)
    elapsed = time.perf_counter() - start

    assert elapsed < 0.1, f"update_fog 30x took {elapsed:.3f}s (> 0.1s threshold)"


def test_update_fog_boundary_clamp():
    """Player at map corner should not crash (radius is clamped to map bounds)."""
    state = _make_state(player_x=0, player_y=0)
    update_fog(state)
    # Tile at origin should be visible if it's in meta
    if (0, 0) in state.world_tiles.meta:
        assert state.world_tiles.meta[(0, 0)]["visibility"] == "visible"


def test_update_fog_no_unseen_in_visible_tiles():
    """No coord in visible_tiles should have visibility != 'visible' in meta."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)

    for coord in state.visible_tiles:
        vis = state.world_tiles.meta.get(coord, {}).get("visibility")
        assert vis == "visible", f"Coord {coord} in visible_tiles but meta says {vis!r}"


# ---------------------------------------------------------------------------
# Save / load fog persistence tests
# ---------------------------------------------------------------------------


@pytest.fixture
def save_path():
    from game.persistence import save_path as current_save_path

    return current_save_path()


def test_fog_save_is_run_length_encoded_and_covers_the_map(save_path):
    """'fog' is a run-length string covering every tile, with explored/visible runs."""
    from game.persistence import _decode_fog

    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    assert save_game(state) is None

    with open(save_path) as f:
        data = json.load(f)

    cells = _decode_fog(data["fog"])
    assert len(cells) == MAP_WIDTH * MAP_HEIGHT
    assert cells.count("visible") == len(state.visible_tiles)
    assert set(cells) <= {"unseen", "explored", "visible"}


def test_fog_load_restores_visibility(save_path, monkeypatch):
    """load_game must restore previously explored tiles from the saved fog list."""
    # Save with explored tiles: first update at (100,40), then move away to explore
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    # Move player far away so (100,40) becomes 'explored'
    state.player_x = 100 + FOG_RADIUS + 5
    state.player_y = 40
    update_fog(state)

    assert state.world_tiles.meta[(100, 40)]["visibility"] == "explored"
    save_game(state)

    # load_game also reads SAVE_FILE — monkeypatch already covers it via the fixture
    loaded = load_game()

    assert loaded is not None
    assert loaded.world_tiles.meta[(100, 40)]["visibility"] == "explored"


def test_fog_load_missing_fog_key_defaults_unseen(save_path):
    """A legacy (unversioned) save without a 'fog' key loads with every tile 'unseen'."""
    minimal_save = {
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
        "inventory": {"gems": {}, "tools": {"shovel": 1}, "loot": {}},
        "polished_gem_values": {},
        "lapidary_level": 1,
        "depleted_tiles": [],
        # intentionally no "fog" key
    }
    with open(save_path, "w") as f:
        json.dump(minimal_save, f)

    loaded = load_game()

    assert loaded is not None
    for coord, tile_meta in loaded.world_tiles.meta.items():
        assert tile_meta["visibility"] == "unseen", f"Tile {coord} is {tile_meta['visibility']!r}"


def test_fog_load_rebuilds_visible_tiles_set(save_path):
    """load_game must rebuild state.visible_tiles from the restored meta."""
    state = _make_state(player_x=100, player_y=40)
    update_fog(state)
    save_game(state)

    loaded = load_game()

    assert loaded is not None
    # visible_tiles should contain coords whose meta says 'visible'
    for coord in loaded.visible_tiles:
        assert loaded.world_tiles.meta[coord]["visibility"] == "visible"
    # All meta tiles with 'visible' should appear in visible_tiles
    expected = {
        coord for coord, m in loaded.world_tiles.meta.items() if m.get("visibility") == "visible"
    }
    assert loaded.visible_tiles == expected


# ---------------------------------------------------------------------------
# Line of sight
# ---------------------------------------------------------------------------


def _open_field_state():
    """30x30 grass world with the player in the middle and a full lantern."""
    from game.tilemap import TileMap
    from game.world import _apply_tile

    tiles = TileMap(30, 30)
    for y in range(30):
        for x in range(30):
            _apply_tile(tiles, x, y, "grass")
    return GameState(world_tiles=tiles, player_x=15, player_y=15)


def test_walls_hide_what_is_behind_them_but_not_themselves():
    from game.world import _apply_tile

    state = _open_field_state()
    for y in range(10, 21):
        _apply_tile(state.world_tiles, 18, y, "rock")  # a wall 3 tiles east
    update_fog(state)
    assert (18, 15) in state.visible_tiles  # the wall face
    assert (20, 15) not in state.visible_tiles  # behind it
    assert (12, 15) in state.visible_tiles  # open side


def test_open_ground_shows_the_whole_light_square():
    state = _open_field_state()
    update_fog(state)
    side = 2 * FOG_RADIUS + 1
    assert len(state.visible_tiles) == side * side


def test_water_and_dirt_do_not_block_sight():
    from game.world import _apply_tile

    state = _open_field_state()
    _apply_tile(state.world_tiles, 17, 15, "deep")
    _apply_tile(state.world_tiles, 18, 15, "dirt")
    update_fog(state)
    assert (19, 15) in state.visible_tiles


def test_fog_is_recomputed_only_when_the_player_moves_or_the_light_changes():
    state = _open_field_state()
    update_fog(state)
    state.world_tiles.meta[(16, 15)]["visibility"] = "unseen"  # tamper
    update_fog(state)
    assert state.world_tiles.meta[(16, 15)]["visibility"] == "unseen"  # cached, untouched

    state.player_x += 1
    update_fog(state)
    assert state.world_tiles.meta[(16, 15)]["visibility"] == "visible"

    before = set(state.visible_tiles)
    state.lantern_fuel = 0
    update_fog(state)
    assert state.visible_tiles < before
