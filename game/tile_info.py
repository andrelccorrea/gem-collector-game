"""One-line description of the tile the player stands on, for the HUD."""

from game.constants import (
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
from game.death import bag_here
from game.input import Action, hint_label
from game.objects.registry import TOOL_CATALOG
from game.tools import MINEABLE_TYPES, WATER_GEM_TYPES

TILE_NAMES = {
    TYPE_GRASS: "Grass",
    TYPE_TREE: "Tree",
    TYPE_PATH: "Path",
    TYPE_ROCK: "Rock",
    TYPE_ORE: "Ore vein",
    TYPE_DIRT: "Dirt",
    TYPE_SHALLOW: "Shallow water",
    TYPE_BANK: "River bank",
    TYPE_DEEP: "Deep water",
    TYPE_CAVE_FLOOR: "Cave floor",
    TYPE_CAVE_WALL: "Cave wall",
    TYPE_RICH_ORE: "Rich ore vein",
    TYPE_TOWN: "Town square",
    TYPE_SHOP: "Shop",
    TYPE_LAPIDARY: "Lapidary",
    TYPE_SAVE: "Save point",
    TYPE_MINEABLE_GRASS: "Grassy mound",
    TYPE_MINEABLE_DIRT: "Loose dirt",
    TYPE_MINEABLE_ROCK: "Rocky seam",
    TYPE_STREAM: "Stream",
    TYPE_LAKE: "Lake",
}
_BUILDINGS = {TYPE_SHOP, TYPE_LAPIDARY, TYPE_SAVE}


def _tools_for(tile_type: str) -> str:
    """Names of the tools that work on this tile type, e.g. "Shovel/Pickaxe"."""
    names = [
        name.replace("_", " ").title()
        for name, tool in TOOL_CATALOG.items()
        if tile_type in tool.compatible_types
    ]
    return "/".join(names) or "no tool"


def describe_here(state) -> str:
    """What is on the player's tile and what Use would do there."""
    if state.world_tiles is None:
        return ""
    meta = state.world_tiles.meta.get((state.player_x, state.player_y), {})
    tile_type = meta.get("type", "")
    parts = [f"Here: {TILE_NAMES.get(tile_type, tile_type.replace('_', ' ').title())}"]

    if tile_type in _BUILDINGS:
        parts[0] += f" - {hint_label(Action.USE, 'Enter')}"
    elif tile_type in MINEABLE_TYPES or tile_type in WATER_GEM_TYPES:
        verb = "dig" if tile_type in MINEABLE_TYPES else "pan"
        if meta.get("depleted"):
            parts[0] += " (worked out)"
        else:
            parts[0] += f" - {verb} with {_tools_for(tile_type)}"

    gem = state.world_gems.get((state.player_x, state.player_y))
    if gem is not None:
        parts.append(f"Gem: {gem.title()} - pick up with {_tools_for(tile_type)}")
    if bag_here(state):
        parts.append(f"Your dropped bag - {hint_label(Action.USE, 'Recover')}")
    return " | ".join(parts)
