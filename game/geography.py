"""Where things are: the town rectangle and the biome regions of the map."""

from game.constants import (
    BIOME_CAVE_MIN_X,
    BIOME_HILLSIDE_MAX_Y,
    BIOME_MEADOW_MAX_X,
    BIOME_NAMES,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
)

# Town: 12 wide x 8 tall around TOWN_CENTER, i.e. x 94..105, y 36..43
TOWN_LEFT = TOWN_CENTER_X - 6
TOWN_RIGHT = TOWN_CENTER_X + 5
TOWN_TOP = TOWN_CENTER_Y - 4
TOWN_BOTTOM = TOWN_CENTER_Y + 3


def in_town(x: int, y: int, margin: int = 0) -> bool:
    """Whether (x, y) is in town, or within ``margin`` tiles of it."""
    return (
        TOWN_LEFT - margin <= x <= TOWN_RIGHT + margin
        and TOWN_TOP - margin <= y <= TOWN_BOTTOM + margin
    )


def biome_at(x: int, y: int) -> str:
    """Biome region of (x, y): "meadow", "cave", "hillside" or "river"."""
    if x <= BIOME_MEADOW_MAX_X:
        return "meadow"
    if x >= BIOME_CAVE_MIN_X:
        return "cave"
    if y <= BIOME_HILLSIDE_MAX_Y:
        return "hillside"
    return "river"


def region_name(x: int, y: int) -> str:
    """Display name of where (x, y) is, with the town taking precedence."""
    return BIOME_NAMES["town"] if in_town(x, y) else BIOME_NAMES[biome_at(x, y)]
