from clingine.renderer import StubRenderer
from game.constants import TILE_PROPS, TYPE_MINEABLE_DIRT, TYPE_SHOP, TYPE_STREAM
from game.hud import render_hud
from game.simulation import new_run
from game.tile_info import TILE_NAMES, describe_here


def _standing_on(tile_type, **meta):
    state = new_run(4)
    pos = (state.player_x, state.player_y)
    state.world_tiles.meta[pos] = {**state.world_tiles.meta[pos], "type": tile_type, **meta}
    state.world_gems.pop(pos, None)
    return state


def test_every_tile_type_has_a_name():
    assert set(TILE_NAMES) == set(TILE_PROPS)


def test_diggable_tile_names_the_tools_that_work_there():
    text = describe_here(_standing_on(TYPE_MINEABLE_DIRT))
    assert text == "Here: Loose dirt - dig with Pickaxe/Shovel"


def test_worked_out_tile_says_so():
    text = describe_here(_standing_on(TYPE_STREAM, depleted=True))
    assert text == "Here: Stream (worked out)"


def test_building_tells_how_to_enter():
    assert describe_here(_standing_on(TYPE_SHOP)) == "Here: Shop - [Space]Enter"


def test_gem_and_dropped_bag_are_listed():
    state = _standing_on(TYPE_STREAM)
    state.world_gems[(state.player_x, state.player_y)] = "amethyst"
    state.dropped_bag = {"x": state.player_x, "y": state.player_y, "gems": {}, "loot": {}}
    parts = describe_here(state).split(" | ")
    assert parts[1] == "Gem: Amethyst - pick up with Gold Pan"
    assert parts[2] == "Your dropped bag - [Space]Recover"


def test_hud_shows_the_tile_between_status_and_hints():
    renderer = StubRenderer(79, 23)  # an 80x24 terminal's usable area
    state = _standing_on(TYPE_SHOP)
    render_hud(renderer, state)
    rows = ["".join(renderer.get_cell(x, y)[0] for x in range(79)) for y in (20, 21, 22)]
    assert "HP:" in rows[0]
    assert rows[1].strip() == "Here: Shop - [Space]Enter"
    assert "Bag:" in rows[2]
