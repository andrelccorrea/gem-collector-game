"""Frontend-agnostic player input.

Game code reads an InputState of Actions, never raw keys, so any frontend
(curses, Kivy, touch) can drive the game by producing the same InputState.
"""

from dataclasses import dataclass
from enum import Enum, auto


class Action(Enum):
    MOVE_UP = auto()
    MOVE_DOWN = auto()
    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    USE = auto()
    ATTACK = auto()
    CYCLE_TOOL = auto()
    NEXT_TAB = auto()
    CONFIRM = auto()
    CANCEL = auto()
    RECALL = auto()


@dataclass(frozen=True)
class InputState:
    # Actions triggered this frame (a new key press or an OS key-repeat event).
    pressed: frozenset = frozenset()
    # Actions whose key/button is currently held down. Only frontends that report
    # releases (e.g. touch) fill this; terminals express holding as repeated presses.
    held: frozenset = frozenset()


EMPTY_INPUT = InputState()

DEFAULT_KEYMAP = {
    "up": Action.MOVE_UP,
    "w": Action.MOVE_UP,
    "down": Action.MOVE_DOWN,
    "s": Action.MOVE_DOWN,
    "left": Action.MOVE_LEFT,
    "a": Action.MOVE_LEFT,
    "right": Action.MOVE_RIGHT,
    "d": Action.MOVE_RIGHT,
    "space": Action.USE,
    "f": Action.ATTACK,
    "e": Action.CYCLE_TOOL,
    "tab": Action.NEXT_TAB,
    "enter": Action.CONFIRM,
    "esc": Action.CANCEL,
    "r": Action.RECALL,
}


def map_keys(pressed_keys, held_keys=(), keymap=DEFAULT_KEYMAP) -> InputState:
    """Translate raw key names into an InputState; unmapped keys are ignored."""
    return InputState(
        pressed=frozenset(keymap[k] for k in pressed_keys if k in keymap),
        held=frozenset(keymap[k] for k in held_keys if k in keymap),
    )
