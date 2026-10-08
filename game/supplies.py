"""Supplies: scarce consumables bought at the shop and used with one Item action.

The Item action picks the supply that helps most right now (the lower of health and
light), so a single button is enough on a phone.
"""

from game.events import HEAL, HEAL_COLOR, emit
from game.input import Action, InputState
from game.lantern import fuel_share, lantern_capacity
from game.objects.registry import SUPPLIES
from game.player import set_hud_message

LIGHT_COLOR = (255, 230, 120)


def count(state, key: str) -> int:
    return state.supplies.get(key, 0)


def _needs(state) -> dict:
    """How much each owned, useful supply is needed (0 = full, 1 = empty)."""
    needs = {}
    if count(state, "bandage") and state.player_hp < state.player_max_hp:
        needs["bandage"] = 1 - state.player_hp / state.player_max_hp
    if count(state, "lamp_oil") and fuel_share(state) < 0.95:
        needs["lamp_oil"] = 1 - fuel_share(state)
    return needs


def use_supply(inp: InputState, state) -> None:
    """Item action: use the most needed supply."""
    if Action.USE_ITEM not in inp.pressed:
        return
    if not any(state.supplies.values()):
        set_hud_message(state, "No supplies. Bandages and Lamp Oil are sold at the Shop.", 2.0)
        return
    needs = _needs(state)
    if not needs:
        set_hud_message(state, "You don't need a supply right now.", 1.5)
        return
    key = max(needs, key=needs.get)
    state.supplies[key] -= 1
    if key == "bandage":
        healed = min(SUPPLIES["bandage"]["heal"], state.player_max_hp - state.player_hp)
        state.player_hp += healed
        emit(state, HEAL, f"+{healed}", HEAL_COLOR, "heart")
        set_hud_message(state, f"Bandaged up (+{healed} HP).", 1.5)
    else:
        capacity = lantern_capacity(state)
        state.lantern_fuel = min(
            capacity, state.lantern_fuel + capacity * SUPPLIES["lamp_oil"]["fuel_share"]
        )
        emit(state, HEAL, "+Light", LIGHT_COLOR)
        set_hud_message(state, "You refill the lantern.", 1.5)


def supplies_label(state) -> str:
    """Short HUD summary, e.g. "Bandage x2 Oil x1" ("" when carrying none)."""
    names = {"bandage": "Bandage", "lamp_oil": "Oil"}
    return " ".join(f"{names[k]} x{n}" for k, n in state.supplies.items() if n > 0)
