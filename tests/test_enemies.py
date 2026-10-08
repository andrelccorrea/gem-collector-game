import pytest

from game import camera, enemies
from game.constants import (
    ENEMY_MAX_DISTANCE,
    ENEMY_PATH_RECALC_INTERVAL,
    TYPE_LAPIDARY,
    TYPE_SAVE,
    TYPE_SHOP,
    TYPE_TOWN,
)
from game.enemies import ENEMY_TOWN_MARGIN, find_path_bfs
from game.geography import biome_at, in_town, region_name
from game.loop import STEP
from game.simulation import new_run
from game.tilemap import TileMap

# ── Geography ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def world():
    return new_run(21)


def test_town_rectangle_matches_the_generated_town(world):
    town_types = {TYPE_TOWN, TYPE_SHOP, TYPE_LAPIDARY, TYPE_SAVE}
    town_tiles = {c for c, m in world.world_tiles.meta.items() if m["type"] in town_types}
    assert town_tiles
    assert all(in_town(x, y) for x, y in town_tiles)


def test_town_rectangle_coordinates():
    assert in_town(94, 36) and in_town(105, 43)
    assert not in_town(93, 40) and not in_town(106, 40)
    assert not in_town(100, 35) and not in_town(100, 44)
    assert in_town(107, 45, 2) and not in_town(108, 40, 2) and not in_town(100, 46, 2)


@pytest.mark.parametrize(
    "x,y,biome",
    [
        (0, 0, "meadow"),
        (49, 79, "meadow"),
        (50, 39, "hillside"),
        (50, 40, "river"),
        (120, 0, "cave"),
    ],
)
def test_biome_boundaries(x, y, biome):
    assert biome_at(x, y) == biome


def test_hud_says_town_exactly_where_hp_regenerates():
    from game.constants import HP_REGEN_INTERVAL
    from game.input import EMPTY_INPUT
    from game.player import update_player
    from game.state import GameState

    for x in range(85, 116):
        for y in range(30, 50):
            state = GameState(player_x=x, player_y=y, player_hp=10)
            update_player(EMPTY_INPUT, state, HP_REGEN_INTERVAL)
            regenerated = state.player_hp > 10
            assert regenerated == (region_name(x, y) == "Town"), (x, y)


# ── Spawning ──────────────────────────────────────────────────────────────────


def _spawn_many(state, attempts):
    for _ in range(attempts):
        state.enemies.clear()
        enemies.spawn_enemies(state, 999.0)
        yield from state.enemies


def test_spawns_are_off_screen_out_of_town_and_within_despawn_distance():
    state = new_run(4)
    spawned = list(_spawn_many(state, 400))
    assert len(spawned) > 300
    for e in spawned:
        assert not camera.on_screen(state, e.x, e.y)
        assert not in_town(e.x, e.y, ENEMY_TOWN_MARGIN)
        assert abs(e.x - state.player_x) + abs(e.y - state.player_y) <= ENEMY_MAX_DISTANCE
        assert state.world_tiles.meta[(e.x, e.y)]["walkable"]


def test_spawned_enemies_survive_the_player_walking_a_few_steps_away():
    state = new_run(4)
    home_x = state.player_x
    for i in range(300):
        state.player_x = home_x
        camera.update_camera(state)
        enemies.spawn_enemies(state, 999.0)
        before = len(state.enemies)
        state.player_x = home_x + (5 if i % 2 else -5)
        enemies.update_enemies(state, STEP)
        assert len(state.enemies) == before
        state.enemies.clear()


def test_no_spawns_in_or_next_to_town_when_town_is_off_screen():
    state = new_run(4)
    state.player_x, state.player_y = 55, 40  # town is ~45 tiles east, outside the view
    camera.update_camera(state)
    assert not camera.on_screen(state, 100, 40)
    spawned = list(_spawn_many(state, 1500))
    assert any(abs(e.x - 100) < 20 for e in spawned), "spawns should reach the town area"
    assert not any(in_town(e.x, e.y, ENEMY_TOWN_MARGIN) for e in spawned)


def test_path_recalculation_times_are_spread_out():
    state = new_run(4)
    timers = [e.path_timer for e in _spawn_many(state, 50)]
    assert all(0.0 <= t <= ENEMY_PATH_RECALC_INTERVAL for t in timers)
    assert len(set(timers)) > 40


# ── Pathfinding ───────────────────────────────────────────────────────────────


def _grid(rows):
    """TileMap from strings: '#' wall, anything else walkable."""
    tiles = TileMap(len(rows[0]), len(rows))
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            tiles.meta[(x, y)] = {"walkable": ch != "#"}
    return tiles


def _assert_valid_walk(tiles, start, path):
    prev = start
    for step in path:
        assert abs(step[0] - prev[0]) + abs(step[1] - prev[1]) == 1
        assert tiles.meta[step]["walkable"]
        prev = step


def test_path_goes_around_walls_by_the_shortest_route():
    tiles = _grid(
        [
            ".......",
            ".#####.",
            ".......",
        ]
    )
    path = find_path_bfs(tiles, 0, 1, 6, 1)
    _assert_valid_walk(tiles, (0, 1), path)
    assert path[-1] == (6, 1)
    assert len(path) == 8


def test_unreachable_target_leads_to_the_closest_reachable_tile_without_crossing_walls():
    tiles = _grid(
        [
            "....#...",
            "....#.T.",
            "....#...",
        ]
    )
    path = find_path_bfs(tiles, 0, 1, 6, 1)
    _assert_valid_walk(tiles, (0, 1), path)
    assert path[-1] == (3, 1)


def test_search_depth_is_limited():
    tiles = _grid(["." * 120])
    path = find_path_bfs(tiles, 0, 0, 119, 0, max_steps=10)
    _assert_valid_walk(tiles, (0, 0), path)
    assert len(path) == 10


def test_blocked_tiles_are_avoided():
    tiles = _grid(
        [
            ".....",
            ".....",
            ".....",
        ]
    )
    path = find_path_bfs(tiles, 0, 1, 4, 1, blocked=lambda x, y: x == 2 and y != 0)
    _assert_valid_walk(tiles, (0, 1), path)
    assert (2, 0) in path and (2, 1) not in path and (2, 2) not in path
    assert path[-1] == (4, 1)


def test_enemies_never_enter_town_while_chasing_a_player_inside_it():
    state = new_run(12)
    state.player_x, state.player_y = 100, 40  # town center
    camera.update_camera(state)
    enemy = enemies.Enemy(100, 30, "snake")
    enemy.aggro_range = 99
    state.enemies = [enemy]
    for _ in range(600):
        enemies.update_enemies(state, STEP)
        assert not in_town(enemy.x, enemy.y, ENEMY_TOWN_MARGIN)
