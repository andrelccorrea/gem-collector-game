from game.enemies import Enemy
from game.input import Action
from game.loop import STEP
from game.simulation import step_game
from game.touch import TouchController
from tests.test_gameplay import make_state


def _run(state, touch, frames):
    for _ in range(frames):
        step_game(touch.poll(state), state, STEP)
        if state.active_scene != "game":
            break


def test_tapping_a_tile_walks_there():
    state = make_state(x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 9, 7)
    _run(state, touch, 120)
    assert (state.player_x, state.player_y) == (9, 7)
    assert touch.path == []


def test_walking_goes_around_obstacles():
    blocked = {(7, y): "tree" for y in range(0, 9)}
    state = make_state(blocked, x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 9, 5)
    _run(state, touch, 300)
    assert (state.player_x, state.player_y) == (9, 5)


def test_tapping_a_dig_spot_walks_there_and_digs():
    state = make_state({(8, 5): "mineable_grass"}, x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 8, 5)
    _run(state, touch, 120)
    assert (8, 5) in state.depleted_tiles


def test_tapping_plain_ground_only_walks():
    state = make_state(x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 7, 5)
    _run(state, touch, 120)
    assert state.hud_message != "Nothing to prospect here."


def test_tapping_yourself_uses_the_tile():
    state = make_state({(5, 5): "mineable_grass"}, x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 5, 5)
    assert Action.USE in touch.poll(state).pressed


def test_tapping_an_adjacent_enemy_attacks_it():
    state = make_state(x=5, y=5, active_scene="game")
    state.enemies = [Enemy(6, 6, "snake")]
    touch = TouchController()
    touch.tap_world(state, 6, 6)
    inp = touch.poll(state)
    assert Action.ATTACK in inp.pressed and not inp.held


def test_buttons_fire_once_and_dpad_holds():
    state = make_state(active_scene="game")
    touch = TouchController()
    touch.press(Action.CYCLE_TOOL)
    assert touch.poll(state).pressed == {Action.CYCLE_TOOL}
    assert touch.poll(state).pressed == frozenset()
    touch.hold(Action.MOVE_RIGHT, True)
    assert Action.MOVE_RIGHT in touch.poll(state).held
    assert Action.MOVE_RIGHT in touch.poll(state).held
    touch.hold(Action.MOVE_RIGHT, False)
    assert not touch.poll(state).held


def test_dpad_cancels_a_tap_walk():
    state = make_state(x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 12, 5)
    touch.hold(Action.MOVE_UP, True)
    inp = touch.poll(state)
    assert inp.held == {Action.MOVE_UP}
    assert touch.path == []


def test_walk_stops_when_the_scene_changes():
    state = make_state(x=5, y=5, active_scene="game")
    touch = TouchController()
    touch.tap_world(state, 12, 5)
    state.active_scene = "shop"
    assert not touch.poll(state).held
