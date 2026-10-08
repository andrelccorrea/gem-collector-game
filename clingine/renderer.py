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


class CursesRenderer(Renderer):
    def __init__(self, window) -> None:
        self._window = window

    @property
    def width(self) -> int:
        return self._window.width

    @property
    def height(self) -> int:
        return self._window.height

    def set_cell(self, x: int, y: int, char: str, color_pair: tuple) -> None:
        max_y = math.floor(self._window.height) - 1
        max_x = math.floor(self._window.width) - 1
        if 0 <= x < max_x and 0 <= y < max_y:
            self._window.screen_array[y][x] = [True, char, color_pair]

    def get_cell(self, x: int, y: int) -> tuple:
        cell = self._window.screen_array[y][x]
        return (cell[1], cell[2])

    def clear(self, color_pair: tuple | None = None) -> None:
        if color_pair is None:
            color_pair = ((0, 0, 0), (0, 0, 0))
        max_y = math.floor(self._window.height) - 1
        max_x = math.floor(self._window.width) - 1
        for y in range(max_y):
            for x in range(max_x):
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
        max_x = self._width - 1
        max_y = self._height - 1
        if 0 <= x < max_x and 0 <= y < max_y:
            self._cells[y][x] = (char, color_pair)

    def get_cell(self, x: int, y: int) -> tuple:
        return self._cells[y][x]

    def clear(self, color_pair: tuple | None = None) -> None:
        for y in range(self._height):
            for x in range(self._width):
                self._cells[y][x] = (" ", color_pair)
