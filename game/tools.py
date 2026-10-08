from game.constants import (
    TYPE_LAKE,
    TYPE_LAPIDARY,
    TYPE_MINEABLE_DIRT,
    TYPE_MINEABLE_GRASS,
    TYPE_MINEABLE_ROCK,
    TYPE_SAVE,
    TYPE_SHOP,
    TYPE_STREAM,
)
from game.gems import bag_has_room
from game.geography import biome_at
from game.input import Action, InputState
from game.objects.registry import TOOL_CATALOG
from game.player import set_hud_message

_MINEABLE_TYPES = {TYPE_MINEABLE_GRASS, TYPE_MINEABLE_DIRT, TYPE_MINEABLE_ROCK}
_WATER_GEM_TYPES = {TYPE_STREAM, TYPE_LAKE}
_DIGGABLE = _MINEABLE_TYPES | _WATER_GEM_TYPES


def update_tools(inp: InputState, state) -> None:
    """Handle E key: cycle through owned tools."""
    if Action.CYCLE_TOOL not in inp.pressed:
        return

    owned = list(state.inventory.get("tools", {}).keys())
    if not owned:
        state.equipped_tool = None
        return

    if state.equipped_tool not in owned:
        state.equipped_tool = owned[0]
        return

    idx = owned.index(state.equipped_tool)
    state.equipped_tool = owned[(idx + 1) % len(owned)]


def use_tool(inp: InputState, state) -> None:
    """Handle Space key: pickup visible gem, or dig mineable tile, or dig water gem."""
    if Action.USE not in inp.pressed:
        return

    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((state.player_x, state.player_y), {})
    tile_type = meta.get("type", "")

    # Building interaction takes priority — handled elsewhere.
    if tile_type in (TYPE_SHOP, TYPE_LAPIDARY, TYPE_SAVE):
        return

    if state.equipped_tool is None:
        set_hud_message(state, "No tool equipped! Press E to equip.", 2.0)
        return

    tool_def = TOOL_CATALOG.get(state.equipped_tool)
    compatible_types = tool_def.compatible_types if tool_def is not None else ()

    pos = (state.player_x, state.player_y)

    if not bag_has_room(state) and (pos in state.world_gems or tile_type in _DIGGABLE):
        set_hud_message(state, "Your bag is full! Sell at the shop.", 2.0)
        return

    # Priority 1: visible gem at player tile
    if pos in state.world_gems:
        if tile_type in compatible_types:
            _pickup_visible_gem(state, pos)
        else:
            tool_label = state.equipped_tool.replace("_", " ").title()
            set_hud_message(state, f"{tool_label} can't pick that up here.", 2.0)
        return

    # Priority 2: mineable tile
    if tile_type in _MINEABLE_TYPES:
        if tile_type not in compatible_types:
            tool_label = state.equipped_tool.replace("_", " ").title()
            set_hud_message(state, f"{tool_label} won't work on this ground.", 2.0)
            return
        if meta.get("depleted", False):
            set_hud_message(state, "Already worked. Try elsewhere.", 2.0)
            return
        _dig_mineable_tile(state, state.player_x, state.player_y, tile_type)
        return

    # Priority 3: prospect in water (no visible gem here, but pan can still try)
    if tile_type in _WATER_GEM_TYPES and tile_type in compatible_types:
        if meta.get("depleted", False):
            set_hud_message(state, "Already panned. Move along.", 2.0)
            return
        _pan_water(state, state.player_x, state.player_y, tile_type)
        return

    set_hud_message(state, "Nothing to prospect here.", 1.5)


def _pickup_visible_gem(state, pos: tuple[int, int]) -> None:
    """Collect a visible gem at the given position."""
    gem_name = state.world_gems.pop(pos, None)
    if gem_name is None:
        return

    from game import gems as gems_module

    gems_module.add_gem_to_inventory(state, gem_name)
    set_hud_message(state, f"Picked up a {gem_name.title()}!", 3.0)


def _dig_mineable_tile(state, x: int, y: int, tile_type: str) -> None:
    """Deplete a mineable tile and roll for a hidden gem drop."""
    _deplete_tile(state, x, y)

    from game import gems as gems_module

    biome = biome_at(x, y)
    gem_name = gems_module.roll_gem_drop(biome, _equipped_tier(state), state.rng)

    if gem_name:
        gems_module.add_gem_to_inventory(state, gem_name)
        set_hud_message(state, f"Found a {gem_name.title()}!", 3.0)
    else:
        set_hud_message(state, "You dig... but find nothing.", 1.5)


def _pan_water(state, x: int, y: int, tile_type: str) -> None:
    """Pan a water tile that has no visible gem — small chance of an extra find."""
    _deplete_tile(state, x, y)

    from game import gems as gems_module

    gem_name = gems_module.roll_gem_drop("river", _equipped_tier(state), state.rng)
    if gem_name:
        gems_module.add_gem_to_inventory(state, gem_name)
        set_hud_message(state, f"Panned up a {gem_name.title()}!", 3.0)
    else:
        set_hud_message(state, "You pan the water... nothing.", 1.5)


def _equipped_tier(state) -> int:
    from game import gems as gems_module

    level = state.inventory.get("tools", {}).get(state.equipped_tool, {}).get("level", 1)
    return gems_module.effective_tier(state.equipped_tool, level)


def _deplete_tile(state, x: int, y: int) -> None:
    """Mark a tile as depleted and update its visual."""
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((x, y), {})
    meta["depleted"] = True
    meta["interactable"] = False
    state.depleted_tiles.add((x, y))
    state.world_tiles.meta[(x, y)] = meta
