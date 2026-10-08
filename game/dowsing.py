"""Dowsing rod: hot/cold hints toward the nearest gem on the ground.

Clues (how warm, which way) instead of a marker on the map: following them is the fun
part. The rod pings (a "detect" event) whenever the trail gets warmer.
"""

from game.events import emit
from game.objects.registry import DOWSING

DETECT = "detect"
# (largest distance in tiles, word), warmest first; anything else in range is "cold"
TIERS = [(2, "hot"), (5, "warm")]
_DIRECTIONS = {(0, -1): "N", (1, -1): "NE", (1, 0): "E", (1, 1): "SE",
               (0, 1): "S", (-1, 1): "SW", (-1, 0): "W", (-1, -1): "NW"}  # fmt: skip


def radius(state) -> int:
    return DOWSING["radii"][state.dowsing_level]


def nearest_gem(state):
    """(distance, dx, dy) to the nearest ground gem within the rod's reach, or None."""
    reach = radius(state)
    best = None
    for gx, gy in state.world_gems:
        dx, dy = gx - state.player_x, gy - state.player_y
        distance = max(abs(dx), abs(dy))
        if 0 < distance <= reach and (best is None or distance < best[0]):
            best = (distance, dx, dy)
    return best


def _tier(distance: int) -> int:
    """0 = hot, 1 = warm, 2 = cold."""
    return next((i for i, (limit, _) in enumerate(TIERS) if distance <= limit), len(TIERS))


def hint(state) -> str:
    """e.g. "Rod: warm NE (4)"; "" without a rod or with nothing in reach."""
    found = nearest_gem(state) if state.dowsing_level else None
    if found is None:
        return ""
    distance, dx, dy = found
    word = TIERS[_tier(distance)][1] if _tier(distance) < len(TIERS) else "cold"
    direction = _DIRECTIONS[((dx > 0) - (dx < 0), (dy > 0) - (dy < 0))]
    return f"Rod: {word} {direction} ({distance})"


def update_dowsing(state) -> None:
    """Ping when the trail gets warmer."""
    found = nearest_gem(state) if state.dowsing_level else None
    tier = _tier(found[0]) if found else None
    if tier is not None and (state.dowse_tier is None or tier < state.dowse_tier):
        emit(state, DETECT, "", (255, 230, 120))
    state.dowse_tier = tier
