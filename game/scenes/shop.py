"""General Store: buy and upgrade tools, sell gems and loot."""

import math

from game.buildings import check_win
from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
)
from game.gems import get_gem_raw_value
from game.input import Action, InputState
from game.objects.registry import ENEMY_CATALOG, TOOL_CATALOG
from game.objects.tools.upgrades import TOOL_MAX_LEVEL, TOOL_UPGRADE_COSTS
from game.player import set_hud_message
from game.ui import clear_screen, render_list, write_str


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


def render_shop(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    width = math.floor(renderer.width) - 1

    title = "=== GENERAL STORE ==="
    write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)

    tab_labels = ["[ Buy Tools ]", "[ Upgrade ]", "[ Sell Gems ]", "[ Sell Loot ]"]
    tab_x = 2
    for i, label in enumerate(tab_labels):
        color = COLOR_MENU_SELECTED if i == state.shop_tab else COLOR_MENU_NORMAL
        write_str(renderer, 1, tab_x, label, color)
        tab_x += len(label) + 2

    gold_str = f"Your Gold: ${state.player_gold}"
    write_str(renderer, 2, width - len(gold_str) - 1, gold_str, COLOR_MENU_NORMAL)

    write_str(renderer, 4, 2, "Item", COLOR_MENU_DIMMED)

    items = _build_shop_items(state)
    cursor = max(0, min(state.shop_cursor, len(items) - 1))
    state.shop_cursor = cursor

    render_list(renderer, items, cursor, top=6, bottom=18)

    hint = "[Up/Down] Navigate  [Left/Right] Switch Tab  [Enter] Confirm  [Esc] Close"
    write_str(
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
            check_win(state)
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
        check_win(state)
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
            check_win(state)
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
        check_win(state)
        if state.active_scene == "win":
            return
