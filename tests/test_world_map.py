from clingine.renderer import StubRenderer
from game.constants import PLAYER_CHAR
from game.input import EMPTY_INPUT, Action
from game.loop import STEP
from game.scenes.world_map import render_map, update_map
from game.simulation import new_run, step_game
from tests.test_gameplay import press


def _screen(state):
    renderer = StubRenderer(79, 23)
    render_map(renderer, state)
    return renderer


def test_the_map_opens_from_play_and_closes_with_map_or_back():
    state = new_run(6)
    step_game(press(Action.MAP), state, STEP)
    assert state.active_scene == "map"
    game_time = state.game_time
    update_map(EMPTY_INPUT, state)
    assert state.active_scene == "map" and state.game_time == game_time
    update_map(press(Action.MAP), state)
    assert state.active_scene == "game"
    state.active_scene = "map"
    update_map(press(Action.CANCEL), state)
    assert state.active_scene == "game"


def test_only_explored_land_shows_and_the_player_is_marked():
    state = new_run(6)
    for tile in state.world_tiles.meta.values():
        tile["visibility"] = "unseen"
    renderer = _screen(state)
    world = [renderer.get_cell(x, y)[0] for y in range(1, 21) for x in range(79)]
    assert world.count(PLAYER_CHAR) == 1 and set(world) <= {" ", PLAYER_CHAR, "T"}
    for (x, _y), tile in state.world_tiles.meta.items():
        if x < 50:
            tile["visibility"] = "explored"
    state.fog_key = "explored more"  # what update_fog does when the view changes
    renderer = _screen(state)
    left = [renderer.get_cell(x, y)[0] for y in range(1, 21) for x in range(19)]
    right = [renderer.get_cell(x, y)[0] for y in range(1, 21) for x in range(60, 79)]
    assert sum(c != " " for c in left) > 300 and set(right) <= {" "}


def test_visited_landmarks_and_a_dropped_bag_are_marked():
    from game.landmarks import landmarks

    state = new_run(6)
    spot = next(iter(landmarks(state)))
    state.visited_landmarks = {spot}
    state.dropped_bag = {"x": 10, "y": 10}
    chars = "".join(_screen(state).get_cell(x, y)[0] for y in range(23) for x in range(79))
    assert "*" in chars and "&" in chars
