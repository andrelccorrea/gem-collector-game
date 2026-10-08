import random

from game import camera
from game.buildings import _build_lapidary_items, render_lapidary
from game.input import Action, InputState
from game.loop import STEP, FixedTimestep
from game.menu import _select_menu_item
from game.simulation import new_run, step_game
from game.state import GameState, gameplay_rng


def test_gameplay_rng_is_reproducible_per_seed():
    a, b = gameplay_rng(7), gameplay_rng(7)
    assert [a.random() for _ in range(5)] == [b.random() for _ in range(5)]


def test_gameplay_rng_differs_between_seeds():
    assert gameplay_rng(7).random() != gameplay_rng(8).random()


def test_gameplay_stream_is_independent_of_world_generation_stream():
    assert gameplay_rng(7).random() != random.Random(7).random()


_SCRIPT = [
    Action.MOVE_LEFT,
    Action.USE,
    Action.MOVE_LEFT,
    Action.USE,
    Action.MOVE_UP,
    Action.USE,
    Action.ATTACK,
    Action.MOVE_DOWN,
    Action.USE,
    Action.CYCLE_TOOL,
]


def _snapshot(state):
    return (
        state.player_x,
        state.player_y,
        state.player_hp,
        state.player_gold,
        dict(state.inventory["gems"]),
        sorted(state.depleted_tiles),
        [(e.name, e.x, e.y, e.hp) for e in state.enemies],
        state.rng.getstate(),
    )


def _replay(state, frame_durations):
    """Drive the real fixed-step loop with scripted input, as the game does each frame."""
    ts = FixedTimestep()
    for i, frame_dt in enumerate(frame_durations):
        pressed = {_SCRIPT[(i // 6) % len(_SCRIPT)]} if i % 6 == 0 else set()
        ts.run(
            frame_dt,
            InputState(pressed=frozenset(pressed)),
            lambda inp, dt: step_game(inp, state, dt),
        )
        if state.active_scene != "game":
            state.active_scene = "game"
            ts.reset()
    return _snapshot(state)


def test_same_seed_and_inputs_replay_the_same_run():
    frames = [STEP] * 1800  # one minute of play
    assert _replay(new_run(7), frames) == _replay(new_run(7), frames)


def test_rendering_does_not_affect_the_simulation(stub_renderer):
    # Same per-step inputs; one run is drawn after every step (rendering updates the
    # camera), the other is headless. Spawning reads the camera, so it must be kept in
    # sync by the simulation itself or the two runs diverge.
    def run(render):
        state = new_run(7)
        for i in range(1800):
            pressed = {_SCRIPT[(i // 5) % len(_SCRIPT)]} if i % 5 == 0 else set()
            step_game(InputState(pressed=frozenset(pressed)), state, STEP)
            state.active_scene = "game"
            if render:
                camera.update_camera(state)
                camera.render_viewport(stub_renderer, state)
        return state

    drawn, headless = run(render=True), run(render=False)
    assert drawn.enemies, "the scripted run should spawn enemies"
    assert _snapshot(drawn) == _snapshot(headless)


def test_new_game_after_a_played_run_matches_a_fresh_run(monkeypatch):
    played = new_run(5)
    _replay(played, [STEP] * 900)
    played.lapidary_level = 3
    played.active_scene = "menu"
    played.menu_cursor = 0

    monkeypatch.setattr(random, "randint", lambda a, b: 1234)
    _select_menu_item(played, save_exists=False)

    assert _snapshot(played) == _snapshot(new_run(1234))
    assert played.lapidary_level == 1
    assert played.game_time == 0.0
    assert played.spawn_timer == 0.0


def test_lapidary_preview_does_not_consume_gameplay_rng(stub_renderer):
    state = GameState()
    state.inventory["gems"] = {"ruby": 2, "quartz": 1}
    before = state.rng.getstate()
    for _ in range(10):
        _build_lapidary_items(state)
        render_lapidary(stub_renderer, state)
    assert state.rng.getstate() == before
