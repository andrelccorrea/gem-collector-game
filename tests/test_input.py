import curses

import pytest

from clingine.keyboard import Keyboard, key_name
from game.constants import MOVE_COOLDOWN
from game.input import EMPTY_INPUT, Action, InputState, map_keys
from game.menu import update_menu
from game.player import update_player
from game.scenes.shop import update_shop
from game.state import GameState

FRAME = 1 / 30


class FakeScreen:
    """Stands in for a curses window: getch() pops queued key codes, then returns -1."""

    def __init__(self):
        self.queue = []

    def getch(self):
        return self.queue.pop(0) if self.queue else -1


@pytest.fixture
def kb():
    screen = FakeScreen()
    return Keyboard(screen), screen


# ── key_name ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "code,name",
    [
        (curses.KEY_UP, "up"),
        (curses.KEY_DOWN, "down"),
        (curses.KEY_LEFT, "left"),
        (curses.KEY_RIGHT, "right"),
        (10, "enter"),
        (13, "enter"),
        (curses.KEY_ENTER, "enter"),
        (27, "esc"),
        (32, "space"),
        (9, "tab"),
        (ord("w"), "w"),
        (ord("W"), "w"),
        (ord("F"), "f"),
    ],
)
def test_key_name_maps_curses_codes(code, name):
    assert key_name(code) == name


def test_key_name_ignores_unsupported_codes():
    assert key_name(curses.KEY_RESIZE) is None
    assert key_name(0) is None


# ── map_keys ──────────────────────────────────────────────────────────────────


def test_map_keys_arrows_and_wasd_share_actions():
    inp = map_keys({"up", "a"}, {"down", "d"})
    assert inp.pressed == {Action.MOVE_UP, Action.MOVE_LEFT}
    assert inp.held == {Action.MOVE_DOWN, Action.MOVE_RIGHT}


def test_map_keys_ignores_unmapped_keys():
    assert map_keys({"z", "1"}, {"q"}) == EMPTY_INPUT


def test_map_keys_accepts_custom_keymap():
    inp = map_keys({"k"}, set(), keymap={"k": Action.MOVE_UP})
    assert inp.pressed == {Action.MOVE_UP}


# ── Keyboard ──────────────────────────────────────────────────────────────────


def test_poll_drains_all_pending_events(kb):
    keyboard, screen = kb
    screen.queue = [ord("e"), 32, curses.KEY_LEFT]
    keyboard.poll()
    assert keyboard.pressed == {"e", "space", "left"}
    assert screen.queue == []


def test_tap_is_pressed_for_exactly_one_frame(kb):
    keyboard, screen = kb
    screen.queue = [ord("f")]
    keyboard.poll()
    assert keyboard.pressed == {"f"}

    keyboard.poll()
    assert keyboard.pressed == set()


# ── Movement driven by terminal key events ────────────────────────────────────


def _simulate(events, duration=1.0):
    """Run update_player at 30 FPS; events is a list of (time, key_code).

    Returns the list of player positions after every frame.
    """
    screen = FakeScreen()
    keyboard = Keyboard(screen)
    state = GameState()
    state.player_x, state.player_y = 50, 50
    pending = sorted(events)
    positions = []
    now = 0.0
    while now < duration:
        while pending and pending[0][0] <= now:
            screen.queue.append(pending.pop(0)[1])
        keyboard.poll()
        update_player(map_keys(keyboard.pressed), state, FRAME)
        positions.append((state.player_x, state.player_y))
        now += FRAME
    return positions


def _repeats(key, start, end, interval):
    """OS auto-repeat: one event at `start`, then every `interval` until `end`."""
    count = int((end - start) / interval) + 1
    return [(start + i * interval, key) for i in range(count)]


def test_single_tap_moves_exactly_one_tile():
    positions = _simulate([(0.0, curses.KEY_RIGHT)])
    assert positions[-1] == (51, 50)


def test_held_key_moves_continuously_at_cooldown_rate():
    positions = _simulate(_repeats(curses.KEY_RIGHT, 0.0, 1.0, 0.03))
    moved = positions[-1][0] - 50
    max_steps = int(1.0 / MOVE_COOLDOWN) + 1
    assert 5 <= moved <= max_steps


def test_no_step_after_release():
    # Hold Right for 0.5 s, then release: no movement may happen after the last event
    # beyond the step already in progress.
    events = _repeats(curses.KEY_RIGHT, 0.0, 0.5, 0.03)
    positions = _simulate(events, duration=1.5)
    last_event_frame = int(events[-1][0] / FRAME) + 1
    assert positions[-1] == positions[last_event_frame]


def test_quick_turn_during_cooldown_is_not_lost():
    # Right, then Up one frame later (mid-cooldown): both steps must happen.
    positions = _simulate([(0.0, curses.KEY_RIGHT), (FRAME, curses.KEY_UP)])
    assert positions[-1] == (51, 49)


def test_same_direction_repeat_during_cooldown_is_dropped():
    positions = _simulate([(0.0, curses.KEY_RIGHT), (FRAME, curses.KEY_RIGHT)])
    assert positions[-1] == (51, 50)


def test_held_actions_from_touch_frontend_move_player():
    # Frontends that report releases drive movement through `held` alone.
    state = GameState()
    state.player_x, state.player_y = 50, 50
    held = InputState(held=frozenset({Action.MOVE_DOWN}))
    for _ in range(31):
        update_player(held, state, FRAME)
    assert state.player_y - 50 >= 5
    for _ in range(30):
        update_player(EMPTY_INPUT, state, FRAME)
    assert state.player_y - 50 <= 7


# ── Scene wiring ──────────────────────────────────────────────────────────────


def test_menu_cancel_requests_quit():
    state = GameState()
    update_menu(InputState(pressed=frozenset({Action.CANCEL})), state)
    assert state.quit_requested is True


def test_shop_next_tab_advances_tab():
    state = GameState()
    state.shop_tab = 0
    update_shop(InputState(pressed=frozenset({Action.NEXT_TAB})), state)
    assert state.shop_tab == 1


def test_shop_move_left_goes_to_previous_tab():
    state = GameState()
    state.shop_tab = 0
    update_shop(InputState(pressed=frozenset({Action.MOVE_LEFT})), state)
    assert state.shop_tab == 3
