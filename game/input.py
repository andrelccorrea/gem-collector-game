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
    USE_ITEM = auto()
    MAP = auto()


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
    "q": Action.USE_ITEM,
    "m": Action.MAP,
}


def map_keys(pressed_keys, held_keys=(), keymap=DEFAULT_KEYMAP) -> InputState:
    """Translate raw key names into an InputState; unmapped keys are ignored."""
    return InputState(
        pressed=frozenset(keymap[k] for k in pressed_keys if k in keymap),
        held=frozenset(keymap[k] for k in held_keys if k in keymap),
    )


# How on-screen hints name each action. Keyboard by default; a frontend with other
# controls (touch buttons) installs its own names with set_hints().
KEYBOARD_HINTS = {
    Action.MOVE_UP: "Up",
    Action.MOVE_DOWN: "Down",
    Action.MOVE_LEFT: "Left",
    Action.MOVE_RIGHT: "Right",
    Action.USE: "Space",
    Action.ATTACK: "F",
    Action.CYCLE_TOOL: "E",
    Action.NEXT_TAB: "Tab",
    Action.CONFIRM: "Enter",
    Action.CANCEL: "Esc",
    Action.RECALL: "R",
    Action.USE_ITEM: "Q",
    Action.MAP: "M",
}
_hints = dict(KEYBOARD_HINTS)


def set_hints(hints: dict) -> None:
    _hints.clear()
    _hints.update(KEYBOARD_HINTS)
    _hints.update(hints)


def hint(action: Action) -> str:
    """Name of the control that triggers ``action`` (e.g. "Enter", or "OK" on touch)."""
    return _hints[action]


def hint_label(action: Action, verb: str) -> str:
    """ "[Space]Use" style hint; just "[Use]" when the control is already named so."""
    key = hint(action)
    return f"[{key}]" if key.lower() == verb.lower() else f"[{key}]{verb}"
