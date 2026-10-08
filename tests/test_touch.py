from game.enemies import Enemy
from game.input import Action
from game.loop import STEP
from game.simulation import step_game
from game.touch import TouchController
from tests.test_gameplay import make_state


def _seen(state):
    """Mark the whole test map as explored (tap paths only cross seen ground)."""
    for meta in state.world_tiles.meta.values():
        meta["visibility"] = "explored"
    return state


def _run(state, touch, frames):
    for _ in range(frames):
        step_game(touch.poll(state), state, STEP)
        if state.active_scene != "game":
            break


def test_tapping_a_tile_walks_there():
    state = make_state(x=5, y=5, active_scene="game")
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 9, 7)
    _run(state, touch, 120)
    assert (state.player_x, state.player_y) == (9, 7)
    assert touch.path == []


def test_walking_goes_around_obstacles():
    blocked = {(7, y): "tree" for y in range(0, 9)}
    state = make_state(blocked, x=5, y=5, active_scene="game")
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 9, 5)
    _run(state, touch, 300)
    assert (state.player_x, state.player_y) == (9, 5)


def test_tapping_a_dig_spot_walks_there_and_digs():
    state = make_state({(8, 5): "mineable_grass"}, x=5, y=5, active_scene="game")
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 8, 5)
    _run(state, touch, 120)
    assert (8, 5) in state.depleted_tiles


def test_tapping_plain_ground_only_walks():
    state = make_state(x=5, y=5, active_scene="game")
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 7, 5)
    _run(state, touch, 120)
    assert state.hud_message != "Nothing to prospect here."


def test_tapping_yourself_uses_the_tile():
    state = make_state({(5, 5): "mineable_grass"}, x=5, y=5, active_scene="game")
    _seen(state)
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
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 12, 5)
    touch.hold(Action.MOVE_UP, True)
    inp = touch.poll(state)
    assert inp.held == {Action.MOVE_UP}
    assert touch.path == []


def test_walk_stops_when_the_scene_changes():
    state = make_state(x=5, y=5, active_scene="game")
    _seen(state)
    touch = TouchController()
    touch.tap_world(state, 12, 5)
    state.active_scene = "shop"
    assert not touch.poll(state).held


def test_tap_paths_do_not_cross_unseen_ground():
    # Two routes to (9, 5): straight through unseen tiles, or around through seen ones.
    state = make_state({(7, y): "tree" for y in range(0, 5)}, x=5, y=5, active_scene="game")
    _seen(state)
    for y in range(5, 20):
        state.world_tiles.meta[(7, y)]["visibility"] = "unseen"
    touch = TouchController()
    touch.tap_world(state, 9, 5)
    assert touch.path == [] or all(
        state.world_tiles.meta[p]["visibility"] != "unseen" for p in touch.path
    )


def test_walk_moves_at_most_one_tile_per_frame_even_after_a_stall():
    from game.loop import FixedTimestep

    state = _seen(make_state(x=5, y=5, active_scene="game"))
    touch = TouchController()
    touch.tap_world(state, 15, 5)
    ts = FixedTimestep()
    ts.run(0.0, touch.poll(state), lambda i, d: step_game(i, state, d))
    before = state.player_x
    ts.run(0.25, touch.poll(state), lambda i, d: step_game(i, state, d))  # 7 steps at once
    assert state.player_x - before <= 1


def test_use_on_arrival_only_for_things_worth_using():
    from game.state import GameState  # noqa: F401

    state = _seen(make_state({(8, 5): "mineable_grass"}, x=5, y=5, active_scene="game"))
    touch = TouchController()
    touch.tap_world(state, 7, 5)  # plain grass
    assert not touch._use_on_arrival
    touch.tap_world(state, 8, 5)  # dig spot
    assert touch._use_on_arrival
    state.world_gems[(6, 6)] = "quartz"
    touch.tap_world(state, 6, 6)
    assert touch._use_on_arrival
    state.dropped_bag = {"x": 9, "y": 9, "gems": {}, "loot": {}, "polished": {}}
    touch.tap_world(state, 9, 9)
    assert touch._use_on_arrival


def test_walk_that_stops_short_does_not_use_the_wrong_tile():
    blocked = {(9, y): "tree" for y in range(0, 20)}
    state = _seen(make_state({**blocked, (12, 5): "mineable_grass"}, x=5, y=5, active_scene="game"))
    touch = TouchController()
    touch.tap_world(state, 12, 5)  # unreachable behind the wall
    assert not touch._use_on_arrival


def test_recall_during_a_walk_lands_exactly_on_the_town_spawn():
    from game.simulation import new_run

    state = new_run(42)
    for meta in state.world_tiles.meta.values():
        meta["visibility"] = "explored"
    state.player_x, state.player_y = 85, 40
    state.recall_charms = 1
    touch = TouchController()
    touch.tap_world(state, 80, 40)
    step_game(touch.poll(state), state, STEP)
    touch.press(Action.RECALL)
    for _ in range(10):
        step_game(touch.poll(state), state, STEP)
    assert (state.player_x, state.player_y) == state.world_tiles.start_pos


def test_attacking_mid_walk_cancels_the_queued_turn():
    state = _seen(make_state(x=5, y=5, active_scene="game"))
    state.queued_move = Action.MOVE_DOWN
    state.enemies = [Enemy(6, 5, "snake")]
    touch = TouchController()
    touch.tap_world(state, 6, 5)
    assert state.queued_move is None


def test_release_all_drops_held_buttons():
    state = make_state(active_scene="game")
    touch = TouchController()
    touch.hold(Action.MOVE_LEFT, True)
    touch.release_all()
    assert not touch.poll(state).held
