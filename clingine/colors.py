"""RGB colors on top of the terminal's fixed palette.

Callers use ((r, g, b), (r, g, b)) foreground/background pairs. Each RGB value is
mapped to the nearest color the terminal already has (the xterm 256-color palette,
or the 16/8 ANSI colors on simpler terminals), so the player's terminal palette is
never redefined. Pairs are allocated lazily and cached.
"""

_ANSI = [
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
]
_CUBE_LEVELS = (0, 95, 135, 175, 215, 255)


def terminal_palette(n_colors: int) -> dict:
    """Color index -> RGB for the colors a terminal with ``n_colors`` can show.

    With 256 colors only indices 16-255 are used: the 6x6x6 cube and the gray ramp
    have standard RGB values, while 0-15 depend on the user's terminal theme.
    Direct-color terminals (more than 256 colors) treat numbers from 8 up as packed
    RGB values, so only the 8 basic ANSI colors are safe there.
    """
    if n_colors > 256:
        n_colors = 8
    if n_colors == 256:
        palette = {}
        for i, rgb in enumerate(
            (r, g, b) for r in _CUBE_LEVELS for g in _CUBE_LEVELS for b in _CUBE_LEVELS
        ):
            palette[16 + i] = rgb
        for i in range(24):
            level = 8 + 10 * i
            palette[232 + i] = (level, level, level)
        return palette
    return {i: rgb for i, rgb in enumerate(_ANSI[: max(n_colors, 1)])}


def _distance(a, b) -> int:
    # Weighted RGB distance: cheap and a good-enough match for human perception.
    dr, dg, db = a[0] - b[0], a[1] - b[1], a[2] - b[2]
    return 2 * dr * dr + 4 * dg * dg + 3 * db * db


class ColorPairs:
    """Maps RGB pairs to curses color-pair attributes."""

    def __init__(self, n_colors: int, n_pairs: int, init_pair, color_pair):
        self.palette = terminal_palette(n_colors)
        # curses.color_pair() encodes only 8 bits of pair number in an attribute.
        self.n_pairs = min(n_pairs, 256)
        self._init_pair = init_pair
        self._color_pair = color_pair
        self._nearest: dict = {}
        self._pair_numbers: dict = {}
        self._attrs: dict = {}

    def nearest(self, rgb) -> int:
        index = self._nearest.get(rgb)
        if index is None:
            index = min(self.palette, key=lambda i: _distance(self.palette[i], rgb))
            self._nearest[rgb] = index
        return index

    def get_color_pair(self, rgb_pair) -> int:
        attr = self._attrs.get(rgb_pair)
        if attr is not None:
            return attr
        key = (self.nearest(rgb_pair[0]), self.nearest(rgb_pair[1]))
        number = self._pair_numbers.get(key)
        if number is None:
            number = len(self._pair_numbers) + 1
            if number >= self.n_pairs:
                number = 0  # out of pairs: fall back to the terminal default
            else:
                self._init_pair(number, key[0], key[1])
                self._pair_numbers[key] = number
        attr = self._color_pair(number)
        self._attrs[rgb_pair] = attr
        return attr
