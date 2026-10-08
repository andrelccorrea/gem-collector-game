"""Day and night: a tint over the world that follows game time.

A few hand-picked tints (day, dusk, night, dawn) instead of a smooth fade keep the
terminal's color pairs bounded and the pixel art crisp. At night the lantern keeps a
warm glow around the player, so the dark reads as a gradient rather than a flat shade.
Drawing only: the simulation never reads it.
"""

DAY_SECONDS = 360.0  # game seconds per full day
# (end of the phase as a share of the day, name, RGB multiplier or None for full daylight)
PHASES = [
    (0.55, "day", None),
    (0.65, "dusk", (255, 196, 150)),
    (0.92, "night", (90, 105, 175)),
    (1.00, "dawn", (225, 200, 225)),
]
# Lantern glow at night: (half-width, half-height in tiles, tint), inner ring first. Cells
# are about twice as tall as wide, so a 2:1 ellipse of cells looks round on screen.
GLOW_RINGS = [(3.2, 1.6, (215, 190, 150)), (5.5, 2.75, (150, 145, 170))]
LANTERN_GLOW = GLOW_RINGS[0][2]


def phase(state) -> tuple:
    """(name, tint) of the time of day."""
    share = (state.game_time % DAY_SECONDS) / DAY_SECONDS
    for end, name, tint in PHASES:
        if share < end:
            return name, tint
    return PHASES[-1][1], PHASES[-1][2]


def tint_at(state, now: tuple, x: int, y: int):
    """The tint for world tile (x, y) given the current ``phase`` (None = no change)."""
    name, tint = now
    if name == "night":
        dx, dy = x - state.player_x, y - state.player_y
        for half_w, half_h, glow in GLOW_RINGS:
            if (dx / half_w) ** 2 + (dy / half_h) ** 2 <= 1:
                return glow
    return tint


def mix(a, b):
    """Two RGB multipliers combined (None = white)."""
    if a is None or b is None:
        return a if b is None else b
    return tuple(p * q // 255 for p, q in zip(a, b, strict=True))


def shade(color_pair, tint):
    """A color pair multiplied by ``tint``."""
    if tint is None or color_pair is None:
        return color_pair
    return mix(color_pair[0], tint), mix(color_pair[1], tint)
