import math


def draw_line(renderer, x1: int, x2: int, y: int, char: str, color_pair) -> None:
    y = math.floor(y)
    if x1 > x2:
        x1, x2 = x2, x1
    x1 = x1 if x1 > 0 else 0
    x2 = x2 if x2 < renderer.width - 2 else renderer.width - 2
    for x in range(math.floor(x1), math.floor(x2) + 1):
        if 0 <= y <= renderer.height - 2:
            existing_char, existing_cp = renderer.get_cell(x, y)
            if existing_char != char or existing_cp != color_pair:
                renderer.set_cell(x, y, char, color_pair)


def draw_endpoints(renderer, x1: int, x2: int, y: int, char: str, color_pair) -> None:
    y = math.floor(y)
    x1 = math.floor(x1)
    x2 = math.floor(x2)
    if 0 <= x1 <= renderer.width - 2 and 0 <= y <= renderer.height - 2:
        existing_char, existing_cp = renderer.get_cell(x1, y)
        if existing_char != char or existing_cp != color_pair:
            renderer.set_cell(x1, y, char, color_pair)
    if 0 <= x2 <= renderer.width - 2 and 0 <= y <= renderer.height - 2:
        existing_char, existing_cp = renderer.get_cell(x2, y)
        if existing_char != char or existing_cp != color_pair:
            renderer.set_cell(x2, y, char, color_pair)
