"""Lapidary: cut raw gems into polished ones and upgrade the cutting machine."""

import math

from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_TITLE,
    LAPIDARY_CUT_FEE_RATIO,
    LAPIDARY_UPGRADES,
)
from game.gems import (
    add_polished_gem,
    get_gem_polished_value,
    get_gem_raw_value,
    polished_value_range,
)
from game.input import Action, InputState
from game.player import set_hud_message
from game.ui import clear_screen, render_list, write_str


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
        low, high = polished_value_range(gem_key, state.lapidary_level)
        label = (
            f"  {gem_key.replace('_', ' ').title():16s}  x{count}"
            f"  |  Cut fee: ${cut_fee}"
            f"  |  Result: ${low}-${high} ea"
        )
        items.append(
            {
                "label": label,
                "enabled": state.player_gold >= cut_fee,
                "action": "cut_gem",
                "key": gem_key,
                "cut_fee": cut_fee,
                "polished_range": (low, high),
            }
        )

    # Upgrade option (if not at max level)
    max_level = max(LAPIDARY_UPGRADES.keys())
    if state.lapidary_level < max_level:
        next_level = state.lapidary_level + 1
        upgrade_cost = LAPIDARY_UPGRADES[next_level]["cost"]
        unlock = LAPIDARY_UPGRADES[next_level].get("unlock_at", 0)
        if state.lifetime_earnings < unlock:
            label = f"  >> Machine level {next_level} unlocks at ${unlock} earned"
            enabled = False
        else:
            label = f"  >> Upgrade Machine (${upgrade_cost})"
            enabled = state.player_gold >= upgrade_cost
        items.append(
            {
                "label": label,
                "enabled": enabled,
                "action": "upgrade_lapidary",
                "key": None,
                "cut_fee": upgrade_cost,
                "polished_range": (0, 0),
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
                "polished_range": (0, 0),
            }
        )

    return items


def render_lapidary(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    width = renderer.width
    max_level = max(LAPIDARY_UPGRADES.keys())

    title = "=== LAPIDARY ==="
    write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)

    if state.lapidary_level >= max_level:
        machine_str = f"Machine Level: {state.lapidary_level}  |  Max Level"
    else:
        next_level = state.lapidary_level + 1
        upgrade_cost = LAPIDARY_UPGRADES[next_level]["cost"]
        machine_str = f"Machine Level: {state.lapidary_level}  |  Upgrade Cost: ${upgrade_cost}"
    write_str(renderer, 2, 2, machine_str, COLOR_MENU_NORMAL)

    gold_str = f"Your Gold: ${state.player_gold}"
    write_str(renderer, 3, 2, gold_str, COLOR_MENU_NORMAL)

    items = _build_lapidary_items(state)
    cursor = max(0, min(state.lapidary_cursor, len(items) - 1))
    state.lapidary_cursor = cursor

    render_list(renderer, items, cursor, top=5, bottom=17)

    hint = "[Up/Down] Navigate  [Enter] Cut/Upgrade  [Esc] Close"
    write_str(
        renderer,
        renderer.height - 1,
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

            # Each polished gem keeps the price rolled for its own cut.
            polished_val = get_gem_polished_value(gem_key, state.lapidary_level, state.rng)
            add_polished_gem(state, gem_key, polished_val)

            set_hud_message(
                state,
                f"Cut a {gem_key.replace('_', ' ').title()}: polished gem worth ${polished_val}!",
                3.0,
            )

    elif action == "upgrade_lapidary":
        upgrade_cost = item["cut_fee"]
        max_level = max(LAPIDARY_UPGRADES.keys())

        if state.lapidary_level >= max_level:
            set_hud_message(state, "Already at max level!", 1.5)
        elif not item["enabled"] and state.player_gold >= upgrade_cost:
            set_hud_message(state, "Not available yet: earn more first!", 1.5)
        elif state.player_gold < upgrade_cost:
            set_hud_message(state, "Not enough gold!", 1.5)
        else:
            state.player_gold -= upgrade_cost
            state.lapidary_level += 1
            set_hud_message(state, f"Lapidary upgraded to level {state.lapidary_level}!", 2.5)
