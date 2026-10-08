"""Lapidary: cut raw gems into polished ones and upgrade the cutting machine."""

import math

from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
    LAPIDARY_CUT_FEE_RATIO,
    LAPIDARY_UPGRADES,
)
from game.gems import (
    GEODE,
    GEODE_CRACK_FEE,
    add_polished_gem,
    crack_geode,
    effective_tier,
    get_gem_raw_value,
    polished_value_range,
    roll_cut_value,
)
from game.input import Action, InputState
from game.input import hint as hint_of
from game.player import set_hud_message
from game.scenes import Scene
from game.ui import clear_screen, render_list, write_str

# Cutting minigame: a marker sweeps back and forth across the bar; stopping it near
# the center gives a better cut. Quality tiers: (name, max distance from center,
# share of the gem's polished price range the cut lands in).
CUT_BAR_WIDTH = 31
CUT_SWEEP_SECONDS = 1.4  # one full left-right-left sweep
CUT_QUALITIES = [
    ("Flawless", 1, (0.9, 1.0)),
    ("Excellent", 4, (0.6, 0.9)),
    ("Good", 9, (0.25, 0.6)),
    ("Poor", CUT_BAR_WIDTH, (0.0, 0.25)),
]


def marker_position(elapsed: float) -> int:
    """Marker cell (0 .. CUT_BAR_WIDTH - 1) after ``elapsed`` seconds of sweeping."""
    phase = (elapsed % CUT_SWEEP_SECONDS) / CUT_SWEEP_SECONDS
    triangle = 1 - abs(2 * phase - 1)  # 0 -> 1 -> 0
    return round(triangle * (CUT_BAR_WIDTH - 1))


def cut_quality(position: int) -> tuple:
    distance = abs(position - CUT_BAR_WIDTH // 2)
    return next(q for q in CUT_QUALITIES if distance <= q[1])


def _build_lapidary_items(state) -> list:
    """Return items for the lapidary screen."""
    items = []
    gems = state.inventory.get("gems", {})

    for gem_key, count in gems.items():
        # Only raw gems (no polished suffix)
        if gem_key.endswith("_polished") or count <= 0:
            continue
        if gem_key == GEODE:
            items.append(
                {
                    "label": f"  {'Geode':16s}  x{count}  |  Crack fee: ${GEODE_CRACK_FEE}"
                    "  |  Result: a random gem",
                    "enabled": state.player_gold >= GEODE_CRACK_FEE,
                    "action": "crack_geode",
                    "key": GEODE,
                    "cut_fee": GEODE_CRACK_FEE,
                    "polished_range": (0, 0),
                }
            )
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

    if state.cutting is not None:
        _render_cutting(renderer, state)
        return

    items = _build_lapidary_items(state)
    cursor = max(0, min(state.lapidary_cursor, len(items) - 1))
    state.lapidary_cursor = cursor

    render_list(renderer, items, cursor, top=5, bottom=16)
    if state.hud_message:
        write_str(renderer, 18, 2, state.hud_message, COLOR_MENU_TITLE)

    hint = (
        f"[{hint_of(Action.MOVE_UP)}/{hint_of(Action.MOVE_DOWN)}] Navigate  "
        f"[{hint_of(Action.CONFIRM)}] Cut/Upgrade  [{hint_of(Action.CANCEL)}] Close"
    )
    write_str(
        renderer,
        renderer.height - 1,
        (width - len(hint)) // 2,
        hint,
        COLOR_MENU_DIMMED,
    )


def update_lapidary(inp: InputState, state, dt: float = 0.0) -> None:
    """Handle input for the lapidary scene (and the cutting minigame while it runs)."""
    pressed = inp.pressed

    if state.cutting is not None:
        _update_cutting(pressed, state, dt)
        return

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
            state.cutting = {"gem": gem_key, "fee": cut_fee, "elapsed": 0.0}

    elif action == "crack_geode":
        gems = state.inventory["gems"]
        if gems.get(GEODE, 0) <= 0:
            set_hud_message(state, "No geodes to crack!", 1.5)
        elif state.player_gold < GEODE_CRACK_FEE:
            set_hud_message(state, "Not enough gold for the crack fee!", 1.5)
        else:
            state.player_gold -= GEODE_CRACK_FEE
            gems[GEODE] -= 1
            if gems[GEODE] == 0:
                del gems[GEODE]
            found = crack_geode(_best_tier(state), state.rng)
            gems[found] = gems.get(found, 0) + 1
            set_hud_message(state, f"The geode held a {found.replace('_', ' ').title()}!", 3.0)

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


def _best_tier(state) -> int:
    """Effective tier of the best tool owned (geodes reward a well-equipped prospector)."""
    tools = state.inventory.get("tools", {})
    return max((effective_tier(t, info["level"]) for t, info in tools.items()), default=1)


def _update_cutting(pressed, state, dt: float) -> None:
    cut = state.cutting
    if Action.CANCEL in pressed:
        state.cutting = None
        set_hud_message(state, "Cut cancelled.", 1.5)
        return
    if Action.CONFIRM not in pressed and Action.USE not in pressed:
        cut["elapsed"] += dt
        return

    # Stop the marker: pay the fee, use up the raw gem, add the polished one.
    gem_key = cut["gem"]
    name, _distance, band = cut_quality(marker_position(cut["elapsed"]))
    state.cutting = None
    gems = state.inventory["gems"]
    state.player_gold -= cut["fee"]
    gems[gem_key] -= 1
    if gems[gem_key] == 0:
        del gems[gem_key]
    value = roll_cut_value(gem_key, state.lapidary_level, band, state.rng)
    add_polished_gem(state, gem_key, value)
    set_hud_message(
        state, f"{name} cut! Polished {gem_key.replace('_', ' ').title()} worth ${value}.", 3.0
    )


def _render_cutting(renderer, state) -> None:
    cut = state.cutting
    width = renderer.width
    title = f"Cutting {cut['gem'].replace('_', ' ').title()}: stop the marker at the center!"
    write_str(renderer, 7, (width - len(title)) // 2, title, COLOR_MENU_NORMAL)
    left = (width - CUT_BAR_WIDTH) // 2
    center = CUT_BAR_WIDTH // 2
    for x in range(CUT_BAR_WIDTH):
        distance = abs(x - center)
        name, _d, _band = cut_quality(x)
        char = "=" if name in ("Flawless", "Excellent") else "-"
        color = COLOR_MENU_TITLE if distance <= 1 else COLOR_MENU_NORMAL
        write_str(renderer, 9, left + x, char, color)
    marker = marker_position(cut["elapsed"])
    write_str(renderer, 10, left + marker, "^", COLOR_MENU_SELECTED)
    hint = f"[{hint_of(Action.CONFIRM)}] Cut   [{hint_of(Action.CANCEL)}] Cancel (no fee)"
    write_str(renderer, 12, (width - len(hint)) // 2, hint, COLOR_MENU_DIMMED)


class LapidaryScene(Scene):
    """The lapidary needs frame time for the cutting minigame."""

    def update(self, inp: InputState, state, frame_dt: float) -> None:
        update_lapidary(inp, state, frame_dt)

    def render(self, renderer, state) -> None:
        render_lapidary(renderer, state)
