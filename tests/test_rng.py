import random

from clingine.renderer import StubRenderer
from game.input import Action, InputState
from game.loop import STEP, FixedTimestep
from game.menu import _select_menu_item
from game.scenes.game import GameScene
from game.scenes.lapidary import _build_lapidary_items, render_lapidary
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


def test_rendering_and_screen_size_do_not_affect_the_simulation():
    # Same per-step inputs; runs are drawn through the real game scene on different
    # screens (terminal, portrait phone, tablet) or not at all. Spawning depends on the
    # simulation view, so the screen must never leak into it.
    def run(screen):
        state, scene = new_run(7), GameScene()
        renderer = StubRenderer(*screen) if screen else None
        for i in range(900):
            pressed = {_SCRIPT[(i // 5) % len(_SCRIPT)]} if i % 5 == 0 else set()
            step_game(InputState(pressed=frozenset(pressed)), state, STEP)
            state.active_scene = "game"
            if renderer:
                scene.render(renderer, state)
        return state

    headless = run(None)
    assert headless.enemies, "the scripted run should spawn enemies"
    for screen in [(80, 24), (40, 60), (220, 90)]:
        assert _snapshot(run(screen)) == _snapshot(headless), screen


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
