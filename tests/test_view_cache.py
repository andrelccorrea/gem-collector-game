from clingine.renderer import StubRenderer
from game import camera
from game.input import Action
from game.simulation import new_run
from game.tools import use_tool
from tests.test_gameplay import press


def _draw(state):
    renderer = StubRenderer(80, 24)
    view = camera.render_view(state, renderer)
    camera.render_viewport(renderer, state, view)
    return renderer, view


def test_an_unchanged_view_reuses_its_cells():
    state = new_run(7)
    _draw(state)
    first = camera._view_cache["cells"]
    _draw(state)
    assert camera._view_cache["cells"] is first


def test_digging_a_tile_redraws_it():
    state = new_run(7)
    pos = next(p for p, t in state.world_tiles.meta.items()
               if t["type"] == "mineable_grass" and t["visibility"] != "unseen")  # fmt: skip
    state.player_x, state.player_y = pos
    state.inventory["tools"]["shovel"] = {"level": 1}
    state.equipped_tool = "shovel"
    renderer, view = _draw(state)
    before = renderer.get_cell(pos[0] - view.x, pos[1] - view.y)
    use_tool(press(Action.USE), state)
    renderer, view = _draw(state)
    assert renderer.get_cell(pos[0] - view.x, pos[1] - view.y) != before


def test_light_changes_redraw_the_view():
    state = new_run(7)
    renderer, view = _draw(state)
    beside = (state.player_x + 1 - view.x, state.player_y - view.y)  # always lit
    day = renderer.get_cell(*beside)
    state.game_time = 0.8 * 360  # night: the lantern's warm glow
    renderer, view = _draw(state)
    assert day[1] is not None and renderer.get_cell(*beside) != day
