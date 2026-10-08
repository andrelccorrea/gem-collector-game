import math
import random

from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
    LAPIDARY_CUT_FEE_RATIO,
    LAPIDARY_UPGRADES,
    TYPE_LAPIDARY,
    TYPE_SAVE,
    TYPE_SHOP,
    WIN_LIFETIME_EARNINGS,
)
from game.gems import get_gem_polished_value, get_gem_raw_value
from game.input import Action, InputState
from game.objects.registry import ENEMY_CATALOG, TOOL_CATALOG
from game.objects.tools.upgrades import TOOL_MAX_LEVEL, TOOL_UPGRADE_COSTS
from game.player import set_hud_message

# ---------------------------------------------------------------------------
# Building interaction gate
# ---------------------------------------------------------------------------

# Display-only RNG for the Lapidary price preview, which is rebuilt every frame; it must
# never draw from the gameplay RNG or the run would depend on the number of frames drawn.
_PREVIEW_RNG = random.Random()


def check_building_interaction(inp: InputState, state) -> None:
    """Check if player is on a building tile and Space was pressed."""
    if Action.USE not in inp.pressed:
        return
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((state.player_x, state.player_y), {})
    tile_type = meta.get("type", "")

    if tile_type == TYPE_SHOP:
        state.active_scene = "shop"
        state.shop_cursor = 0
        state.shop_tab = 0
    elif tile_type == TYPE_LAPIDARY:
        state.active_scene = "lapidary"
        state.lapidary_cursor = 0
    elif tile_type == TYPE_SAVE:
        state.active_scene = "save_point"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_shop_items(state) -> list:
    """Return the item list for the current shop tab.

    Each entry is a dict with at least:
        label: str          — display text
        enabled: bool       — whether the action is purchasable/sellable
        action: str         — "buy_tool", "upgrade_tool", "sell_gem",
                              "sell_all_gems", "sell_loot", "sell_all_loot"
        key: str | None     — gem/loot/tool name (where relevant)
        cost: int           — gold required (for buys/upgrades, or 0)
        value: int          — gold gained (for sells, or 0)
    """
    items = []
    tab = state.shop_tab

    if tab == 0:  # Buy Tools
        for tool_name, tool_def in TOOL_CATALOG.items():
            owned = tool_name in state.inventory.get("tools", {})
            cost = tool_def.cost
            if owned:
                label = f"  {tool_name.title():16s}  (Owned)"
                enabled = False
            elif cost == 0:
                label = f"  {tool_name.title():16s}  FREE"
                enabled = True
            else:
                label = f"  {tool_name.title():16s}  ${cost}"
                enabled = state.player_gold >= cost
            items.append(
                {
                    "label": label,
                    "enabled": enabled,
                    "action": "buy_tool",
                    "key": tool_name,
                    "cost": cost,
                    "value": 0,
                }
            )

    elif tab == 1:  # Upgrade Tools
        owned_tools = state.inventory.get("tools", {})
        for tool_name, tool_info in owned_tools.items():
            level = tool_info.get("level", 1)
            if level >= TOOL_MAX_LEVEL:
                label = f"  {tool_name.title():16s}  Lv{level}  (Max Level)"
                enabled = False
                cost = 0
            else:
                next_level = level + 1
                cost = TOOL_UPGRADE_COSTS.get(next_level, 9999)
                label = f"  {tool_name.title():16s}  Lv{level} -> Lv{next_level}  ${cost}"
                enabled = state.player_gold >= cost
            items.append(
                {
                    "label": label,
                    "enabled": enabled,
                    "action": "upgrade_tool",
                    "key": tool_name,
                    "cost": cost,
                    "value": 0,
                }
            )
        if not items:
            items.append(
                {
                    "label": "  No tools owned yet.",
                    "enabled": False,
                    "action": "none",
                    "key": None,
                    "cost": 0,
                    "value": 0,
                }
            )

    elif tab == 2:  # Sell Gems
        gems = state.inventory.get("gems", {})
        polished = state.polished_gem_values
        total = 0

        for gem_key, count in gems.items():
            if count <= 0:
                continue
            if gem_key.endswith("_polished"):
                raw_name = gem_key[: -len("_polished")]
                unit_val = polished.get(gem_key, get_gem_raw_value(raw_name))
                display_name = f"{raw_name.replace('_', ' ').title()} (Polished)"
            else:
                unit_val = get_gem_raw_value(gem_key)
                display_name = gem_key.replace("_", " ").title()
            subtotal = unit_val * count
            total += subtotal
            label = f"  {display_name:20s}  x{count}  ${unit_val} each"
            items.append(
                {
                    "label": label,
                    "enabled": True,
                    "action": "sell_gem",
                    "key": gem_key,
                    "cost": 0,
                    "value": unit_val,
                }
            )

        if items:
            items.append(
                {
                    "label": f"  >> Sell All Gems (${total} total)",
                    "enabled": True,
                    "action": "sell_all_gems",
                    "key": None,
                    "cost": 0,
                    "value": total,
                }
            )
        else:
            items.append(
                {
                    "label": "  No gems in inventory.",
                    "enabled": False,
                    "action": "none",
                    "key": None,
                    "cost": 0,
                    "value": 0,
                }
            )

    elif tab == 3:  # Sell Loot
        loot = state.inventory.get("loot", {})
        total = 0

        for loot_key, count in loot.items():
            if count <= 0:
                continue
            unit_val = 0
            for enemy_def in ENEMY_CATALOG.values():
                if enemy_def.loot == loot_key:
                    unit_val = enemy_def.loot_value
                    break
            subtotal = unit_val * count
            total += subtotal
            label = f"  {loot_key.replace('_', ' ').title():20s}  x{count}  ${unit_val} each"
            items.append(
                {
                    "label": label,
                    "enabled": True,
                    "action": "sell_loot",
                    "key": loot_key,
                    "cost": 0,
                    "value": unit_val,
                }
            )

        if items:
            items.append(
                {
                    "label": f"  >> Sell All Loot (${total} total)",
                    "enabled": True,
                    "action": "sell_all_loot",
                    "key": None,
                    "cost": 0,
                    "value": total,
                }
            )
        else:
            items.append(
                {
                    "label": "  No loot in inventory.",
                    "enabled": False,
                    "action": "none",
                    "key": None,
                    "cost": 0,
                    "value": 0,
                }
            )

    return items


def _check_win(state) -> None:
    """Trigger win scene if lifetime earnings threshold is reached."""
    if state.lifetime_earnings >= WIN_LIFETIME_EARNINGS and not state.has_won:
        state.has_won = True
        state.active_scene = "win"


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------


def render_shop(renderer, state) -> None:
    from game.menu import _clear_screen, _write_str

    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    width = math.floor(renderer.width) - 1

    title = "=== GENERAL STORE ==="
    _write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)

    tab_labels = ["[ Buy Tools ]", "[ Upgrade ]", "[ Sell Gems ]", "[ Sell Loot ]"]
    tab_x = 2
    for i, label in enumerate(tab_labels):
        color = COLOR_MENU_SELECTED if i == state.shop_tab else COLOR_MENU_NORMAL
        _write_str(renderer, 1, tab_x, label, color)
        tab_x += len(label) + 2

    gold_str = f"Your Gold: ${state.player_gold}"
    _write_str(renderer, 2, width - len(gold_str) - 1, gold_str, COLOR_MENU_NORMAL)

    _write_str(renderer, 4, 2, "Item", COLOR_MENU_DIMMED)

    items = _build_shop_items(state)
    cursor = max(0, min(state.shop_cursor, len(items) - 1))
    state.shop_cursor = cursor

    for idx, item in enumerate(items):
        row = 6 + idx
        if row > 18:
            break
        label = item["label"]
        if idx == cursor:
            color = COLOR_MENU_SELECTED
        elif not item["enabled"]:
            color = COLOR_MENU_DIMMED
        else:
            color = COLOR_MENU_NORMAL
        _write_str(renderer, row, 0, label, color)

    hint = "[Up/Down] Navigate  [Left/Right] Switch Tab  [Enter] Confirm  [Esc] Close"
    _write_str(
        renderer,
        math.floor(renderer.height) - 2,
        (width - len(hint)) // 2,
        hint,
        COLOR_MENU_DIMMED,
    )


def update_shop(inp: InputState, state) -> None:
    """Handle input for the shop scene."""
    pressed = inp.pressed

    # Tab switching: Left/Right or Tab (next tab)
    if Action.MOVE_LEFT in pressed:
        state.shop_tab = (state.shop_tab - 1) % 4
        state.shop_cursor = 0
        return
    if Action.MOVE_RIGHT in pressed or Action.NEXT_TAB in pressed:
        state.shop_tab = (state.shop_tab + 1) % 4
        state.shop_cursor = 0
        return

    items = _build_shop_items(state)
    if not items:
        if Action.CANCEL in pressed:
            state.active_scene = "game"
        return

    # Clamp cursor
    state.shop_cursor = max(0, min(state.shop_cursor, len(items) - 1))

    if Action.MOVE_UP in pressed:
        state.shop_cursor = max(0, state.shop_cursor - 1)
        return
    if Action.MOVE_DOWN in pressed:
        state.shop_cursor = min(len(items) - 1, state.shop_cursor + 1)
        return

    if Action.CANCEL in pressed:
        state.active_scene = "game"
        return

    if Action.CONFIRM not in pressed:
        return

    item = items[state.shop_cursor]
    action = item["action"]

    if action == "buy_tool":
        tool_name = item["key"]
        cost = item["cost"]
        if tool_name in state.inventory.get("tools", {}):
            set_hud_message(state, "Already owned!", 1.5)
        elif state.player_gold < cost:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= cost
            state.inventory.setdefault("tools", {})[tool_name] = {"level": 1}
            set_hud_message(state, f"Bought {tool_name.title()}!", 2.0)

    elif action == "upgrade_tool":
        tool_name = item["key"]
        cost = item["cost"]
        tools = state.inventory.get("tools", {})
        if tool_name not in tools:
            set_hud_message(state, "Tool not owned!", 1.5)
        elif tools[tool_name].get("level", 1) >= TOOL_MAX_LEVEL:
            set_hud_message(state, "Already at max level!", 1.5)
        elif state.player_gold < cost:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= cost
            tools[tool_name]["level"] += 1
            new_level = tools[tool_name]["level"]
            set_hud_message(state, f"{tool_name.title()} upgraded to Lv{new_level}!", 2.0)

    elif action == "sell_gem":
        gem_key = item["key"]
        unit_val = item["value"]
        gems = state.inventory.get("gems", {})
        if gems.get(gem_key, 0) <= 0:
            set_hud_message(state, "None left!", 1.5)
        else:
            gems[gem_key] -= 1
            if gems[gem_key] == 0:
                del gems[gem_key]
                # Also remove from polished_gem_values if it was polished
                if gem_key.endswith("_polished") and gem_key in state.polished_gem_values:
                    del state.polished_gem_values[gem_key]
            state.player_gold += unit_val
            state.lifetime_earnings += unit_val
            set_hud_message(state, f"Sold for ${unit_val}!", 2.0)
            _check_win(state)
            if state.active_scene == "win":
                return

    elif action == "sell_all_gems":
        gems = state.inventory.get("gems", {})
        total = 0
        for gem_key, count in list(gems.items()):
            if count <= 0:
                continue
            if gem_key.endswith("_polished"):
                raw_name = gem_key[: -len("_polished")]
                unit_val = state.polished_gem_values.get(gem_key, get_gem_raw_value(raw_name))
            else:
                unit_val = get_gem_raw_value(gem_key)
            total += unit_val * count
        state.inventory["gems"] = {}
        state.polished_gem_values.clear()
        state.player_gold += total
        state.lifetime_earnings += total
        set_hud_message(state, f"Sold all gems for ${total}!", 2.5)
        state.shop_cursor = 0
        _check_win(state)
        if state.active_scene == "win":
            return

    elif action == "sell_loot":
        loot_key = item["key"]
        unit_val = item["value"]
        loot = state.inventory.get("loot", {})
        if loot.get(loot_key, 0) <= 0:
            set_hud_message(state, "None left!", 1.5)
        else:
            loot[loot_key] -= 1
            if loot[loot_key] == 0:
                del loot[loot_key]
            state.player_gold += unit_val
            state.lifetime_earnings += unit_val
            set_hud_message(state, f"Sold for ${unit_val}!", 2.0)
            _check_win(state)
            if state.active_scene == "win":
                return

    elif action == "sell_all_loot":
        loot = state.inventory.get("loot", {})
        total = 0
        for loot_key, count in loot.items():
            if count <= 0:
                continue
            unit_val = 0
            for enemy_def in ENEMY_CATALOG.values():
                if enemy_def.loot == loot_key:
                    unit_val = enemy_def.loot_value
                    break
            total += unit_val * count
        state.inventory["loot"] = {}
        state.player_gold += total
        state.lifetime_earnings += total
        set_hud_message(state, f"Sold all loot for ${total}!", 2.5)
        state.shop_cursor = 0
        _check_win(state)
        if state.active_scene == "win":
            return


# ---------------------------------------------------------------------------
# Lapidary
# ---------------------------------------------------------------------------


def _build_lapidary_items(state) -> list:
    """Return items for the lapidary screen."""
    items = []
    gems = state.inventory.get("gems", {})

    for gem_key, count in gems.items():
        # Only raw gems (no polished suffix)
        if gem_key.endswith("_polished") or count <= 0:
            continue
        raw_val = get_gem_raw_value(gem_key)
        cut_fee = int(math.ceil(raw_val * LAPIDARY_CUT_FEE_RATIO))
        polished_val = get_gem_polished_value(gem_key, state.lapidary_level, _PREVIEW_RNG)
        label = (
            f"  {gem_key.replace('_', ' ').title():16s}  x{count}"
            f"  |  Cut fee: ${cut_fee}"
            f"  |  Result: ~${polished_val} ea"
        )
        items.append(
            {
                "label": label,
                "enabled": state.player_gold >= cut_fee,
                "action": "cut_gem",
                "key": gem_key,
                "cut_fee": cut_fee,
                "polished_val": polished_val,
            }
        )

    # Upgrade option (if not at max level)
    max_level = max(LAPIDARY_UPGRADES.keys())
    if state.lapidary_level < max_level:
        next_level = state.lapidary_level + 1
        upgrade_cost = LAPIDARY_UPGRADES[next_level]["cost"]
        enabled = state.player_gold >= upgrade_cost
        items.append(
            {
                "label": f"  >> Upgrade Machine (${upgrade_cost})",
                "enabled": enabled,
                "action": "upgrade_lapidary",
                "key": None,
                "cut_fee": upgrade_cost,
                "polished_val": 0,
            }
        )

    if not items:
        items.append(
            {
                "label": "  No raw gems to cut.",
                "enabled": False,
                "action": "none",
                "key": None,
                "cut_fee": 0,
                "polished_val": 0,
            }
        )

    return items


def render_lapidary(renderer, state) -> None:
    from game.menu import _clear_screen, _write_str

    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    width = math.floor(renderer.width) - 1
    max_level = max(LAPIDARY_UPGRADES.keys())

    title = "=== LAPIDARY ==="
    _write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)

    if state.lapidary_level >= max_level:
        machine_str = f"Machine Level: {state.lapidary_level}  |  Max Level"
    else:
        next_level = state.lapidary_level + 1
        upgrade_cost = LAPIDARY_UPGRADES[next_level]["cost"]
        machine_str = f"Machine Level: {state.lapidary_level}  |  Upgrade Cost: ${upgrade_cost}"
    _write_str(renderer, 2, 2, machine_str, COLOR_MENU_NORMAL)

    gold_str = f"Your Gold: ${state.player_gold}"
    _write_str(renderer, 3, 2, gold_str, COLOR_MENU_NORMAL)

    items = _build_lapidary_items(state)
    cursor = max(0, min(state.lapidary_cursor, len(items) - 1))
    state.lapidary_cursor = cursor

    for idx, item in enumerate(items):
        row = 5 + idx
        if row > 17:
            break
        label = item["label"]
        if idx == cursor:
            color = COLOR_MENU_SELECTED
        elif not item["enabled"]:
            color = COLOR_MENU_DIMMED
        else:
            color = COLOR_MENU_NORMAL
        _write_str(renderer, row, 0, label, color)

    hint = "[Up/Down] Navigate  [Enter] Cut/Upgrade  [Esc] Close"
    _write_str(
        renderer,
        math.floor(renderer.height) - 2,
        (width - len(hint)) // 2,
        hint,
        COLOR_MENU_DIMMED,
    )


def update_lapidary(inp: InputState, state) -> None:
    """Handle input for the lapidary scene."""
    pressed = inp.pressed

    if Action.CANCEL in pressed:
        state.active_scene = "game"
        return

    items = _build_lapidary_items(state)
    if not items:
        return

    # Clamp cursor
    state.lapidary_cursor = max(0, min(state.lapidary_cursor, len(items) - 1))

    if Action.MOVE_UP in pressed:
        state.lapidary_cursor = max(0, state.lapidary_cursor - 1)
        return
    if Action.MOVE_DOWN in pressed:
        state.lapidary_cursor = min(len(items) - 1, state.lapidary_cursor + 1)
        return

    if Action.CONFIRM not in pressed:
        return

    item = items[state.lapidary_cursor]
    action = item["action"]

    if action == "cut_gem":
        gem_key = item["key"]
        cut_fee = item["cut_fee"]
        gems = state.inventory.get("gems", {})

        if gems.get(gem_key, 0) <= 0:
            set_hud_message(state, "No gems to cut!", 1.5)
        elif state.player_gold < cut_fee:
            set_hud_message(state, "Not enough gold for the cut fee!", 1.5)
        else:
            # Deduct fee and remove one raw gem
            state.player_gold -= cut_fee
            gems[gem_key] -= 1
            if gems[gem_key] == 0:
                del gems[gem_key]

            # Add one polished gem
            polished_key = f"{gem_key}_polished"
            gems[polished_key] = gems.get(polished_key, 0) + 1

            # Compute and store polished sell price
            polished_val = get_gem_polished_value(gem_key, state.lapidary_level, state.rng)
            state.polished_gem_values[polished_key] = polished_val

            set_hud_message(
                state,
                f"Cut {gem_key.replace('_', ' ').title()} into a polished gem! (~${polished_val})",
                3.0,
            )

    elif action == "upgrade_lapidary":
        upgrade_cost = item["cut_fee"]
        max_level = max(LAPIDARY_UPGRADES.keys())

        if state.lapidary_level >= max_level:
            set_hud_message(state, "Already at max level!", 1.5)
        elif state.player_gold < upgrade_cost:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= upgrade_cost
            state.lapidary_level += 1
            set_hud_message(state, f"Lapidary upgraded to level {state.lapidary_level}!", 2.5)


# ---------------------------------------------------------------------------
# Save point
# ---------------------------------------------------------------------------


def render_save_point(renderer, state) -> None:
    from game.menu import _clear_screen, _write_str

    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    _write_str(renderer, mid_y - 2, mid_x - 8, "  SAVE POINT  ", COLOR_MENU_TITLE)
    _write_str(
        renderer,
        mid_y,
        mid_x - 16,
        "Save your progress? [Enter] Yes  [Esc] Cancel",
        COLOR_MENU_NORMAL,
    )


def update_save_point(inp: InputState, state) -> None:
    """Handle save point input."""
    if Action.CANCEL in inp.pressed:
        state.active_scene = "game"
    elif Action.CONFIRM in inp.pressed:
        from game import persistence

        error = persistence.save_game(state)
        set_hud_message(state, error or "Game Saved!", 3.0)
        state.active_scene = "game"
