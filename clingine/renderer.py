import math
from abc import ABC, abstractmethod


class Renderer(ABC):
    @property
    @abstractmethod
    def width(self) -> int: ...

    @property
    @abstractmethod
    def height(self) -> int: ...

    @abstractmethod
    def set_cell(self, x: int, y: int, char: str, color_pair: tuple) -> None: ...

    @abstractmethod
    def get_cell(self, x: int, y: int) -> tuple: ...

    @abstractmethod
    def clear(self, color_pair: tuple | None = None) -> None: ...

    def set_sprite(self, x: int, y: int, layer: str, sprite: str, tint: tuple | None) -> None:
        """Show image ``sprite`` on cell (x, y) this frame, over the cell's character.

        ``layer`` is "ground" (fills the cell) or "object" (drawn on the ground). ``tint``
        is an RGB multiplier (None = original colors). Unlike cells, sprites last one
        frame: whatever is not set again is gone. Text frontends ignore sprites.
        """
        return None


class CursesRenderer(Renderer):
    """Renderer over a curses Window.

    curses raises when writing the bottom-right cell, so the last row and column are
    never drawn; width/height report only the usable area and callers need no guard.
    """

    def __init__(self, window) -> None:
        self._window = window

    @property
    def width(self) -> int:
        return math.floor(self._window.width) - 1

    @property
    def height(self) -> int:
        return math.floor(self._window.height) - 1

    def set_cell(self, x: int, y: int, char: str, color_pair: tuple) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            self._window.screen_array[y][x] = [True, char, color_pair]

    def get_cell(self, x: int, y: int) -> tuple:
        cell = self._window.screen_array[y][x]
        return (cell[1], cell[2])

    def clear(self, color_pair: tuple | None = None) -> None:
        if color_pair is None:
            color_pair = ((0, 0, 0), (0, 0, 0))
        for y in range(self.height):
            for x in range(self.width):
                self._window.screen_array[y][x] = [True, " ", color_pair]


class StubRenderer(Renderer):
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._cells = [[(" ", None) for _ in range(width)] for _ in range(height)]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def set_cell(self, x: int, y: int, char: str, color_pair: tuple) -> None:
        if 0 <= x < self._width and 0 <= y < self._height:
            self._cells[y][x] = (char, color_pair)

    def get_cell(self, x: int, y: int) -> tuple:
        return self._cells[y][x]

    def clear(self, color_pair: tuple | None = None) -> None:
        for y in range(self._height):
            for x in range(self._width):
                self._cells[y][x] = (" ", color_pair)
