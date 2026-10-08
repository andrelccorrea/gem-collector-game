import pytest

from clingine.renderer import StubRenderer
from game import camera
from game.constants import TILE_PROPS
from game.state import GameState
from game.theme import (
    DEPLETED_APPEARANCE,
    TILE_APPEARANCE,
    UNSEEN_APPEARANCE,
    dim,
    tile_appearance,
)
from game.tilemap import TileMap


def test_tilemap_has_meta_attribute():
    s = TileMap(10, 10)
    assert s.meta == {}


def test_tilemap_meta_is_independent_per_instance():
    s1 = TileMap(10, 10)
    s2 = TileMap(10, 10)
    s1.meta[(0, 0)] = {"type": "grass"}
    assert s2.meta == {}


def test_tilemap_has_start_pos_attribute():
    s = TileMap(10, 10)
    assert s.start_pos is None


def test_tilemap_start_pos_can_be_set():
    s = TileMap(10, 10)
    s.start_pos = (5, 3)
    assert s.start_pos == (5, 3)


def test_every_tile_type_has_an_appearance():
    assert set(TILE_APPEARANCE) == set(TILE_PROPS)


def test_world_tiles_store_types_not_glyphs():
    from game.world import generate_world

    tiles, _ = generate_world(9)
    assert isinstance(tiles, TileMap)
    assert all(m["type"] in TILE_PROPS for m in tiles.meta.values())
    assert not hasattr(tiles, "tiles")


@pytest.mark.parametrize(
    "meta,expected",
    [
        ({"type": "tree", "visibility": "visible"}, TILE_APPEARANCE["tree"]),
        ({"type": "tree", "visibility": "unseen"}, UNSEEN_APPEARANCE),
        (
            {"type": "tree", "visibility": "explored"},
            (TILE_APPEARANCE["tree"][0], dim(TILE_APPEARANCE["tree"][1])),
        ),
        ({"type": "ore", "visibility": "visible", "depleted": True}, DEPLETED_APPEARANCE),
        (
            {"type": "ore", "visibility": "explored", "depleted": True},
            (DEPLETED_APPEARANCE[0], dim(DEPLETED_APPEARANCE[1])),
        ),
    ],
)
def test_tile_appearance_applies_depletion_and_fog(meta, expected):
    assert tile_appearance(meta) == expected


def test_dim_halves_rgb_and_keeps_none():
    assert dim(((100, 201, 60), (10, 20, 31))) == ((50, 100, 30), (5, 10, 15))
    assert dim(None) is None


def test_viewport_draws_tiles_through_the_theme():
    tiles = TileMap(100, 40)
    for y in range(40):
        for x in range(100):
            tiles.meta[(x, y)] = {"type": "grass", "visibility": "visible", "depleted": False}
    tiles.meta[(3, 2)] = {"type": "tree", "visibility": "visible", "depleted": False}
    tiles.meta[(4, 2)] = {"type": "tree", "visibility": "explored", "depleted": False}
    tiles.meta[(5, 2)] = {"type": "tree", "visibility": "unseen", "depleted": False}
    state = GameState(world_tiles=tiles, world_gems={}, camera_x=0, camera_y=0)
    renderer = StubRenderer(80, 24)

    camera.render_viewport(renderer, state, camera.View(state.camera_x, state.camera_y, 79, 21))

    assert renderer.get_cell(3, 2) == TILE_APPEARANCE["tree"]
    assert renderer.get_cell(4, 2) == (TILE_APPEARANCE["tree"][0], dim(TILE_APPEARANCE["tree"][1]))
    assert renderer.get_cell(5, 2) == UNSEEN_APPEARANCE


def test_depleting_a_tile_changes_how_it_is_drawn():
    from game.simulation import new_run
    from game.tools import _deplete_tile

    state = new_run(4)
    x, y = state.player_x, state.player_y
    state.world_tiles.meta[(x + 1, y)]["visibility"] = "visible"
    _deplete_tile(state, x + 1, y)
    renderer = StubRenderer(80, 24)
    camera.render_viewport(renderer, state, camera.View(state.camera_x, state.camera_y, 79, 21))
    assert renderer.get_cell(x + 1 - state.camera_x, y - state.camera_y) == DEPLETED_APPEARANCE


class CountingRenderer(StubRenderer):
    def __init__(self, *args):
        super().__init__(*args)
        self.writes = 0

    def set_cell(self, x, y, char, color_pair):
        self.writes += 1
        super().set_cell(x, y, char, color_pair)


def test_redrawing_an_unchanged_viewport_writes_no_cells():
    from game.simulation import new_run

    state = new_run(6)
    state.world_gems = {}
    renderer = CountingRenderer(80, 24)
    camera.render_viewport(renderer, state, camera.View(state.camera_x, state.camera_y, 79, 21))
    assert renderer.writes > 0
    renderer.writes = 0
    camera.render_viewport(renderer, state, camera.View(state.camera_x, state.camera_y, 79, 21))
    assert renderer.writes == 0
