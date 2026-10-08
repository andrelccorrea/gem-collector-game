"""Terminal theme: how each tile type looks (glyph + RGB colors).

Game state stores tile *types* only; frontends turn them into visuals through a
theme, so a graphical frontend can map the same types to sprites instead.
"""

from game.constants import (
    CHAR_BANK,
    CHAR_CAVE_FLOOR,
    CHAR_CAVE_WALL,
    CHAR_DEEP,
    CHAR_DEPLETED,
    CHAR_DIRT,
    CHAR_GRASS,
    CHAR_LAKE,
    CHAR_LAPIDARY,
    CHAR_MINEABLE_DIRT,
    CHAR_MINEABLE_GRASS,
    CHAR_MINEABLE_ROCK,
    CHAR_ORE,
    CHAR_PATH,
    CHAR_RICH_ORE,
    CHAR_ROCK,
    CHAR_SAVE,
    CHAR_SHALLOW,
    CHAR_SHOP,
    CHAR_STREAM,
    CHAR_TOWN_GROUND,
    CHAR_TREE,
    COLOR_BUILDING,
    COLOR_CAVE,
    COLOR_HILLSIDE,
    COLOR_MEADOW,
    COLOR_RIVER,
    COLOR_TOWN,
    TYPE_BANK,
    TYPE_CAVE_FLOOR,
    TYPE_CAVE_WALL,
    TYPE_DEEP,
    TYPE_DIRT,
    TYPE_GRASS,
    TYPE_LAKE,
    TYPE_LAPIDARY,
    TYPE_MINEABLE_DIRT,
    TYPE_MINEABLE_GRASS,
    TYPE_MINEABLE_ROCK,
    TYPE_ORE,
    TYPE_PATH,
    TYPE_RICH_ORE,
    TYPE_ROCK,
    TYPE_SAVE,
    TYPE_SHALLOW,
    TYPE_SHOP,
    TYPE_STREAM,
    TYPE_TOWN,
    TYPE_TREE,
)

TILE_APPEARANCE = {
    TYPE_GRASS: (CHAR_GRASS, COLOR_MEADOW),
    TYPE_TREE: (CHAR_TREE, ((0, 100, 0), (0, 30, 0))),
    TYPE_PATH: (CHAR_PATH, ((180, 140, 60), (0, 30, 0))),
    TYPE_ROCK: (CHAR_ROCK, COLOR_HILLSIDE),
    TYPE_ORE: (CHAR_ORE, ((255, 220, 0), (40, 40, 40))),
    TYPE_DIRT: (CHAR_DIRT, ((120, 80, 40), (40, 40, 40))),
    TYPE_SHALLOW: (CHAR_SHALLOW, COLOR_RIVER),
    TYPE_BANK: (CHAR_BANK, ((180, 160, 100), (0, 0, 80))),
    TYPE_DEEP: (CHAR_DEEP, ((0, 0, 160), (0, 0, 80))),
    TYPE_CAVE_FLOOR: (CHAR_CAVE_FLOOR, COLOR_CAVE),
    TYPE_CAVE_WALL: (CHAR_CAVE_WALL, ((80, 60, 30), (10, 10, 10))),
    TYPE_RICH_ORE: (CHAR_RICH_ORE, ((100, 200, 255), (10, 10, 10))),
    TYPE_TOWN: (CHAR_TOWN_GROUND, COLOR_TOWN),
    TYPE_SHOP: (CHAR_SHOP, COLOR_BUILDING),
    TYPE_LAPIDARY: (CHAR_LAPIDARY, COLOR_BUILDING),
    TYPE_SAVE: (CHAR_SAVE, COLOR_BUILDING),
    TYPE_MINEABLE_GRASS: (CHAR_MINEABLE_GRASS, ((180, 230, 140), (0, 30, 0))),
    TYPE_MINEABLE_DIRT: (CHAR_MINEABLE_DIRT, ((210, 160, 90), (40, 40, 40))),
    TYPE_MINEABLE_ROCK: (CHAR_MINEABLE_ROCK, ((230, 230, 230), (40, 40, 40))),
    TYPE_STREAM: (CHAR_STREAM, ((150, 210, 255), (0, 50, 120))),
    TYPE_LAKE: (CHAR_LAKE, ((180, 220, 255), (30, 80, 160))),
}

DEPLETED_APPEARANCE = (CHAR_DEPLETED, ((80, 80, 80), (20, 20, 20)))

# ASCII stand-ins for the Unicode glyphs above (and for the player and gems), for
# frontends whose output or font cannot show them.
ASCII_FALLBACK = {
    "♣": "T",
    "▲": "^",
    "◇": "*",
    "◈": "@",
    "▓": "#",
    "·": ".",
    "∴": ".",
    "░": ":",
    "≈": "~",
    "☻": "@",
    "♦": "o",
    "♠": "t",
    "◊": "v",
}
UNSEEN_APPEARANCE = (" ", None)

# Decorations (game/decor.py) drawn in place of their base tile's look.
DECOR_APPEARANCE = {
    "flowers": ("*", ((255, 120, 180), (0, 30, 0))),
    "flowers_yellow": ("*", ((255, 225, 80), (0, 30, 0))),
    "mushroom": ("♠", ((200, 120, 255), (10, 10, 10))),
    "crystal": ("◊", ((120, 220, 255), (10, 10, 10))),
    "reeds": ("|", ((90, 170, 60), (0, 0, 80))),
    "lily": ("o", ((60, 170, 70), (0, 0, 80))),
    "pebbles": (".", ((150, 150, 150), (40, 40, 40))),
}


def dim(color_pair):
    """Halve every RGB component (explored-but-not-visible tiles)."""
    if color_pair is None:
        return None
    fg, bg = color_pair
    return (fg[0] // 2, fg[1] // 2, fg[2] // 2), (bg[0] // 2, bg[1] // 2, bg[2] // 2)


def tile_appearance(tile_meta: dict, decoration: str | None = None) -> tuple:
    """(char, color_pair) for a tile, including its decoration, depletion and fog of war."""
    visibility = tile_meta.get("visibility", "visible")
    if visibility == "unseen":
        return UNSEEN_APPEARANCE
    if decoration is not None:
        char, color_pair = DECOR_APPEARANCE[decoration]
    elif tile_meta.get("depleted"):
        char, color_pair = DEPLETED_APPEARANCE
    else:
        char, color_pair = TILE_APPEARANCE[tile_meta["type"]]
    if visibility == "explored":
        color_pair = dim(color_pair)
    return char, color_pair
