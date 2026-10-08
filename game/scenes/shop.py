"""General Store: buy and upgrade tools, sell gems and loot."""

from game import market
from game.buildings import check_win
from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
    RECALL_CHARM_COST,
)
from game.gems import polished_prices
from game.input import Action, InputState
from game.input import hint as hint_of
from game.lantern import lantern_capacity
from game.objects.registry import (
    BAG_CAPACITIES,
    BAG_COSTS,
    BAG_UNLOCK_AT,
    GEM_CATALOG,
    LANTERN,
    TOOL_CATALOG,
    TOOL_MAX_LEVEL,
    TOOL_UPGRADE_COSTS,
    TOOL_UPGRADE_UNLOCK_AT,
)
from game.player import set_hud_message
from game.ui import clear_screen, render_list, write_str

SHOP_TABS = ["Buy", "Upgrade", "Sell Gems", "Sell Loot", "Museum"]


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
        charm_label = (
            f"  {'Recall Charm':16s}  ${RECALL_CHARM_COST}  (have {state.recall_charms}, R)"
        )
        items.append(
            {
                "label": charm_label,
                "enabled": state.player_gold >= RECALL_CHARM_COST,
                "action": "buy_charm",
                "key": "recall_charm",
                "cost": RECALL_CHARM_COST,
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
                unlock = TOOL_UPGRADE_UNLOCK_AT.get(next_level, 0)
                if state.lifetime_earnings < unlock:
                    label = f"  {tool_name.title():16s}  Lv{next_level} unlocks at ${unlock} earned"
                    enabled = False
                else:
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
        items.append(_gear_upgrade_item(state, "bag"))
        items.append(_gear_upgrade_item(state, "lantern"))

    elif tab == 2:  # Sell Gems
        gems = state.inventory.get("gems", {})
        for gem_key, count in gems.items():
            if count <= 0:
                continue
            if gem_key.endswith("_polished"):
                raw_name = gem_key[: -len("_polished")]
                display_name = f"{raw_name.replace('_', ' ').title()} (Polished)"
            else:
                display_name = gem_key.replace("_", " ").title()
            items.append(_sell_row(state, gem_key, display_name, count, "sell_gem"))
        _add_sell_all_row(items, state, list(gems), "sell_all_gems", "Gems")

    elif tab == 3:  # Sell Loot
        loot = state.inventory.get("loot", {})
        for loot_key, count in loot.items():
            if count <= 0:
                continue
            display_name = loot_key.replace("_", " ").title()
            items.append(_sell_row(state, loot_key, display_name, count, "sell_loot"))
        _add_sell_all_row(items, state, list(loot), "sell_all_loot", "Loot")

    elif tab == 4:  # Museum
        bonus = round((market.museum_bonus(state) - 1) * 100)
        items.append(
            {
                "label": f"  Donated {len(state.museum)}/{len(GEM_CATALOG)} gem kinds"
                f"  |  all sale prices +{bonus}%"
                f"  (+{round(market.MUSEUM_BONUS * 100)}% every {market.MUSEUM_MILESTONE})",
                "enabled": False,
                "action": "none",
                "key": None,
                "cost": 0,
                "value": 0,
            }
        )
        for gem_key, count in state.inventory.get("gems", {}).items():
            if count > 0 and gem_key in GEM_CATALOG and gem_key not in state.museum:
                name = gem_key.replace("_", " ").title()
                items.append(
                    {
                        "label": f"  Donate a {name}",
                        "enabled": True,
                        "action": "donate",
                        "key": gem_key,
                        "cost": 0,
                        "value": 0,
                    }
                )

    return items


def _sell_row(state, key: str, name: str, count: int, action: str) -> dict:
    """Shop row for selling one kind; shows the price spread and any market discount."""
    if key.endswith("_polished"):
        multiplier = market.price_multiplier(state.market.get(key, 0.0))
        prices = polished_prices(state, key)
        low, high = int(prices[-1] * multiplier), int(prices[0] * multiplier)
        price_text = f"${low}-${high}" if low != high else f"${high}"
    else:
        price_text = f"${market.unit_price(state, key)}"
    discount = market.discount_percent(state, key)
    note = f"  (-{discount}% sold recently)" if discount > 0 else ""
    return {
        "label": f"  {name:20s}  x{count}  {price_text} each{note}",
        "enabled": True,
        "action": action,
        "key": key,
        "cost": 0,
        "value": market.unit_price(state, key),
    }


def _add_sell_all_row(items: list, state, keys: list, action: str, kind: str) -> None:
    if items:
        total = market.preview_sell_all(state, keys)
        label = f"  >> Sell All {kind} (${total} total)"
        row = {"label": label, "enabled": True, "action": action, "key": None, "cost": 0}
        items.append({**row, "value": total})
    else:
        items.append(
            {
                "label": f"  No {kind.lower()} in inventory.",
                "enabled": False,
                "action": "none",
                "key": None,
                "cost": 0,
                "value": 0,
            }
        )


# Gear bought in levels: (state attribute, capacities, costs, unlock_at, unit of capacity)
_GEAR = {
    "bag": ("bag_level", BAG_CAPACITIES, BAG_COSTS, BAG_UNLOCK_AT, "items"),
    "lantern": (
        "lantern_level",
        LANTERN["capacities"],
        LANTERN["costs"],
        LANTERN["unlock_at"],
        "s of light",
    ),
}


def _gear_upgrade_item(state, gear: str) -> dict:
    """Shop row for the next level of a piece of gear (disabled when unavailable)."""
    attr, capacities, costs, unlock_at, unit = _GEAR[gear]
    level = getattr(state, attr)
    name = gear.title()
    item = {"action": "upgrade_gear", "key": gear, "cost": 0, "value": 0, "enabled": False}
    if level + 1 >= len(capacities):
        item["label"] = f"  {name:16s}  {capacities[level]} {unit}  (Best)"
    elif state.lifetime_earnings < unlock_at[level + 1]:
        item["label"] = f"  {name:16s}  better {gear} unlocks at ${unlock_at[level + 1]} earned"
    else:
        cost = costs[level + 1]
        upgrade = f"{capacities[level]} -> {capacities[level + 1]} {unit}"
        item["label"] = f"  {name:16s}  {upgrade}  ${cost}"
        item["cost"] = cost
        item["enabled"] = state.player_gold >= cost
    return item


def render_shop(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    width = renderer.width

    title = "=== GENERAL STORE ==="
    write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)

    tab_labels = [f"[ {name} ]" for name in SHOP_TABS]
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

    hint = (
        f"[{hint_of(Action.MOVE_UP)}/{hint_of(Action.MOVE_DOWN)}] Navigate  "
        f"[{hint_of(Action.MOVE_LEFT)}/{hint_of(Action.MOVE_RIGHT)}] Tab  "
        f"[{hint_of(Action.CONFIRM)}] Confirm  [{hint_of(Action.CANCEL)}] Close"
    )
    write_str(
        renderer,
        renderer.height - 1,
        (width - len(hint)) // 2,
        hint,
        COLOR_MENU_DIMMED,
    )


def update_shop(inp: InputState, state) -> None:
    """Handle input for the shop scene."""
    pressed = inp.pressed

    # Tab switching: Left/Right or Tab (next tab)
    if Action.MOVE_LEFT in pressed:
        state.shop_tab = (state.shop_tab - 1) % len(SHOP_TABS)
        state.shop_cursor = 0
        return
    if Action.MOVE_RIGHT in pressed or Action.NEXT_TAB in pressed:
        state.shop_tab = (state.shop_tab + 1) % len(SHOP_TABS)
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

    if action == "buy_charm":
        if state.player_gold < RECALL_CHARM_COST:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= RECALL_CHARM_COST
            state.recall_charms += 1
            set_hud_message(state, "Bought a Recall Charm (press R to return to town).", 2.0)

    elif action == "buy_tool":
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
        elif not item["enabled"] and state.player_gold >= cost:
            set_hud_message(state, "Not available yet: earn more first!", 1.5)
        elif state.player_gold < cost:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= cost
            tools[tool_name]["level"] += 1
            new_level = tools[tool_name]["level"]
            set_hud_message(state, f"{tool_name.title()} upgraded to Lv{new_level}!", 2.0)

    elif action == "donate":
        gem_key = item["key"]
        gems = state.inventory["gems"]
        gems[gem_key] -= 1
        if gems[gem_key] == 0:
            del gems[gem_key]
        state.museum.append(gem_key)
        set_hud_message(state, f"The museum thanks you for the {gem_key.replace('_', ' ')}!", 2.5)

    elif action == "upgrade_gear":
        gear = item["key"]
        if not item["enabled"]:
            set_hud_message(state, f"Can't buy a better {gear} yet!", 1.5)
        else:
            attr = _GEAR[gear][0]
            state.player_gold -= item["cost"]
            setattr(state, attr, getattr(state, attr) + 1)
            if gear == "lantern":
                state.lantern_fuel = lantern_capacity(state)
            set_hud_message(state, f"Bought a better {gear}!", 2.0)

    elif action in ("sell_gem", "sell_loot"):
        price = market.sell_one(state, item["key"])
        if price == 0:
            set_hud_message(state, "None left!", 1.5)
            return
        set_hud_message(state, f"Sold for ${price}!", 2.0)
        check_win(state)

    elif action in ("sell_all_gems", "sell_all_loot"):
        total = market.sell_all(state, loot=action == "sell_all_loot")
        kind = "loot" if action == "sell_all_loot" else "gems"
        set_hud_message(state, f"Sold all {kind} for ${total}!", 2.5)
        state.shop_cursor = 0
        check_win(state)
