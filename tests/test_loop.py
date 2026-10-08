import pytest

from clingine.clock import Clock
from game.combat import enemy_attacks
from game.constants import HP_REGEN_INTERVAL, TOWN_CENTER_X, TOWN_CENTER_Y
from game.input import EMPTY_INPUT, Action, InputState
from game.loop import MAX_FRAME_DT, STEP, FixedTimestep
from game.player import update_player
from game.state import GameState

ATTACK = InputState(pressed=frozenset({Action.ATTACK}))


def _recorder():
    calls = []

    def update(inp, dt):
        calls.append((inp, dt))
        return True

    return calls, update


def _running(frames=1):
    """A FixedTimestep past its post-reset discarded frame, on an exact step boundary."""
    ts = FixedTimestep()
    for _ in range(frames):
        ts.run(0.0, EMPTY_INPUT, lambda i, d: True)
    ts.accumulator = 0.0
    return ts


# ── Clock ─────────────────────────────────────────────────────────────────────


class FakeTime:
    def __init__(self):
        self.now = 100.0
        self.slept = []

    def timer(self):
        return self.now

    def sleep(self, sec):
        self.slept.append(sec)
        self.now += sec


def test_clock_sleeps_only_the_remainder_of_the_frame():
    t = FakeTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    t.now += 0.01  # 10 ms of frame work
    dt = clock.tick(30)
    assert t.slept == [pytest.approx(1 / 30 - 0.01)]
    assert dt == pytest.approx(1 / 30)


def test_clock_does_not_sleep_when_frame_overran():
    t = FakeTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    t.now += 0.1
    dt = clock.tick(30)
    assert t.slept == []
    assert dt == pytest.approx(0.1)


def test_clock_dt_includes_frame_work():
    # Real frame duration must count the work, so game time keeps pace with real time.
    t = FakeTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    total = 0.0
    for _ in range(30):
        t.now += 0.02
        total += clock.tick(30)
    assert total == pytest.approx(1.0)


class OversleepingTime(FakeTime):
    """Every sleep runs 5 ms long, like macOS timer coalescing."""

    def sleep(self, sec):
        super().sleep(sec + 0.005)


def test_clock_sleep_overshoot_does_not_lower_frame_rate():
    t = OversleepingTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    total = 0.0
    for _ in range(300):
        t.now += 0.002  # frame work
        total += clock.tick(30)
    assert 300 / total == pytest.approx(30, abs=0.1)


def test_clock_resyncs_after_a_long_stall_instead_of_bursting():
    t = FakeTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    t.now += 2.0  # e.g. world generation
    clock.tick(30)
    t.now += 0.002
    dt = clock.tick(30)
    assert dt == pytest.approx(1 / 30)


# ── FixedTimestep ─────────────────────────────────────────────────────────────


def test_steps_have_fixed_size_and_count_matches_elapsed_time():
    ts = _running()
    calls, update = _recorder()
    ts.run(STEP * 3 + STEP / 2, EMPTY_INPUT, update)
    assert len(calls) == 3
    assert all(dt == STEP for _, dt in calls)
    assert ts.accumulator == pytest.approx(STEP / 2)


def test_leftover_time_carries_to_next_frame():
    ts = _running()
    calls, update = _recorder()
    ts.run(STEP * 0.6, EMPTY_INPUT, update)
    assert calls == []
    ts.run(STEP * 0.6, EMPTY_INPUT, update)
    assert len(calls) == 1


def test_long_frame_is_clamped():
    ts = _running()
    calls, update = _recorder()
    ts.run(10.0, EMPTY_INPUT, update)
    assert len(calls) == int(MAX_FRAME_DT / STEP)


def test_pressed_input_survives_a_zero_step_frame():
    ts = _running()
    calls, update = _recorder()
    ts.run(STEP * 0.5, ATTACK, update)
    assert calls == []
    ts.run(STEP * 0.5, EMPTY_INPUT, update)
    assert [inp.pressed for inp, _ in calls] == [{Action.ATTACK}]


def test_pressed_input_is_delivered_to_only_one_step():
    ts = _running()
    calls, update = _recorder()
    ts.run(STEP * 3, ATTACK, update)
    assert [inp.pressed for inp, _ in calls] == [{Action.ATTACK}, set(), set()]


def test_held_input_is_visible_to_every_step():
    ts = _running()
    calls, update = _recorder()
    held = InputState(held=frozenset({Action.MOVE_UP}))
    ts.run(STEP * 2, held, update)
    assert all(inp.held == {Action.MOVE_UP} for inp, _ in calls)


def test_update_returning_false_stops_stepping():
    ts = _running()
    calls = []

    def update(inp, dt):
        calls.append(dt)
        return False

    ts.run(STEP * 5, EMPTY_INPUT, update)
    assert len(calls) == 1


def test_reset_discards_time_input_and_the_pause_frame():
    ts = _running()
    calls, update = _recorder()
    ts.run(STEP * 0.9, ATTACK, update)
    ts.reset()
    assert ts.accumulator == pytest.approx(STEP / 2)
    # The frame right after a reset spans the pause (e.g. world generation): skip it.
    ts.run(2.0, EMPTY_INPUT, update)
    assert calls == []
    # Leftover pre-reset time would push this frame over a step; it must be gone.
    ts.run(STEP * 0.4, EMPTY_INPUT, update)
    assert calls == []
    ts.run(STEP * 0.2, EMPTY_INPUT, update)
    assert [inp.pressed for inp, _ in calls] == [set()]


class JitteryTime(FakeTime):
    """Sleep overshoot varying 0-5 ms in a fixed pseudo-random pattern."""

    def __init__(self):
        super().__init__()
        self.i = 0

    def sleep(self, sec):
        self.i += 1
        super().sleep(sec + (self.i * 7919 % 11) * 0.0005)


def test_one_step_per_frame_despite_sleep_jitter():
    t = JitteryTime()
    clock = Clock(timer=t.timer, sleep=t.sleep)
    ts = FixedTimestep()
    counts = []
    for _ in range(600):
        t.now += 0.003  # frame work
        counts.append(ts.run(clock.tick(30), EMPTY_INPUT, lambda i, d: True))
    assert set(counts[2:]) == {1}


# ── Game time ─────────────────────────────────────────────────────────────────


def _town_state():
    state = GameState()
    state.player_x, state.player_y = TOWN_CENTER_X, TOWN_CENTER_Y
    state.player_hp = 10
    return state


def test_regen_works_on_a_fresh_game():
    state = _town_state()
    update_player(EMPTY_INPUT, state, HP_REGEN_INTERVAL)
    assert state.player_hp > 10


def test_regen_blocked_for_five_seconds_of_game_time_after_combat():
    state = _town_state()
    state.game_time = 100.0
    state.last_combat_time = 97.0
    update_player(EMPTY_INPUT, state, HP_REGEN_INTERVAL)
    assert state.player_hp == 10

    state.game_time = 102.5
    update_player(EMPTY_INPUT, state, HP_REGEN_INTERVAL)
    assert state.player_hp > 10


def test_enemy_hit_records_game_time_not_wall_clock():
    class Dummy:
        x, y = TOWN_CENTER_X + 1, TOWN_CENTER_Y
        attack_cooldown = 0.0
        attack_cooldown_max = 1.0
        attack = 1
        name = "Snake"

    state = _town_state()
    state.game_time = 42.0
    state.enemies = [Dummy()]
    enemy_attacks(state, STEP)
    assert state.last_combat_time == 42.0
