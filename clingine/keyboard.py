import curses

_SPECIAL_KEYS = {
    curses.KEY_UP: "up",
    curses.KEY_DOWN: "down",
    curses.KEY_LEFT: "left",
    curses.KEY_RIGHT: "right",
    curses.KEY_ENTER: "enter",
    10: "enter",
    13: "enter",
    27: "esc",
    32: "space",
    9: "tab",
}


def key_name(code: int) -> str | None:
    """Map a curses getch() code to a lowercase key name, or None if unsupported."""
    if code in _SPECIAL_KEYS:
        return _SPECIAL_KEYS[code]
    if 33 <= code <= 126:
        return chr(code).lower()
    return None


class Keyboard:
    """Terminal keyboard read through curses getch(); no OS-level key hooks.

    Terminals report key presses and OS auto-repeats but never releases, so there is
    no reliable "held" state: holding a key shows up as a stream of pressed events.
    """

    def __init__(self, screen):
        self.screen = screen
        self.pressed = set()

    def poll(self) -> None:
        """Drain all pending key events; call exactly once per frame."""
        self.pressed = set()
        while (code := self.screen.getch()) != -1:
            name = key_name(code)
            if name is not None:
                self.pressed.add(name)
