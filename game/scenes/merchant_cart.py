"""The traveling merchant's cart: today's two offers and the gem it is buying."""

from game import merchant
from game.constants import COLOR_MENU_DIMMED, COLOR_MENU_NORMAL, COLOR_MENU_TITLE
from game.feedback import chime, refuse
from game.input import Action, InputState
from game.input import hint as hint_of
from game.player import set_hud_message
from game.ui import clear_screen, render_list, write_str


def _items(state) -> list:
    visit = merchant.today(state)
    if visit is None:
        return []
    items = []
    for key in visit["stock"]:
        name, price, _ = merchant.OFFERS[key]
        sold = merchant.bought_today(state, key) > 0
        items.append({
            "label": f"  {name:22s}  " + ("(Sold out)" if sold else f"${price}"),
            "enabled": not sold and state.player_gold >= price,
            "action": "buy", "key": key, "icon": None,
        })  # fmt: skip
    wanted = visit["wants"]
    left = merchant.WANTED_PER_DAY - merchant.bought_today(state, "sell")
    have = state.inventory.get("gems", {}).get(wanted, 0)
    items.append({
        "label": f"  Sell {wanted.replace('_', ' ').title():17s}  "
        f"${merchant.wanted_price(state)} each  (have {have}, wants {left} more)",
        "enabled": have > 0 and left > 0,
        "action": "sell", "key": wanted, "icon": ("gem", None),
    })  # fmt: skip
    return items


def render_merchant(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    width = renderer.width
    title = "=== TRAVELING MERCHANT ==="
    write_str(renderer, 1, (width - len(title)) // 2, title, COLOR_MENU_TITLE)
    line = '"Rare goods, today only. Tomorrow I\'m gone."'
    write_str(renderer, 3, (width - len(line)) // 2, line, COLOR_MENU_NORMAL)
    gold = f"Your Gold: ${state.player_gold}"
    write_str(renderer, 4, width - len(gold) - 1, gold, COLOR_MENU_NORMAL)
    items = _items(state)
    state.shop_cursor = max(0, min(state.shop_cursor, len(items) - 1))
    render_list(renderer, items, state.shop_cursor, top=6, bottom=12)
    if items and items[state.shop_cursor]["action"] == "buy":
        about = merchant.OFFERS[items[state.shop_cursor]["key"]][2]
        write_str(renderer, 14, 2, about, COLOR_MENU_NORMAL)
    if state.hud_message:
        write_str(renderer, 16, 2, state.hud_message[: width - 4], COLOR_MENU_TITLE)
    hint = (f"[{hint_of(Action.MOVE_UP)}/{hint_of(Action.MOVE_DOWN)}] Navigate  "
            f"[{hint_of(Action.CONFIRM)}] Trade  [{hint_of(Action.CANCEL)}] Leave")  # fmt: skip
    write_str(renderer, renderer.height - 1, (width - len(hint)) // 2, hint, COLOR_MENU_DIMMED)


def update_merchant(inp: InputState, state) -> None:
    pressed = inp.pressed
    items = _items(state)
    if Action.CANCEL in pressed or not items:
        state.active_scene = "game"
        return
    if Action.MOVE_UP in pressed:
        state.shop_cursor = (state.shop_cursor - 1) % len(items)
    if Action.MOVE_DOWN in pressed:
        state.shop_cursor = (state.shop_cursor + 1) % len(items)
    if Action.CONFIRM not in pressed:
        return
    item = items[state.shop_cursor]
    if item["action"] == "buy":
        reason = merchant.buy(state, item["key"])
        if reason:
            refuse(state, reason)
        else:
            set_hud_message(state, f"Bought: {merchant.OFFERS[item['key']][0]}!", 2.0)
            chime(state)
    else:
        paid = merchant.sell_wanted(state)
        if paid:
            set_hud_message(state, f"Sold for ${paid}!", 2.0)
            chime(state)
        else:
            refuse(state, "The merchant can't take that.")
