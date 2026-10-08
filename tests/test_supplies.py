import pytest

from game.input import Action
from game.lantern import lantern_capacity
from game.objects.registry import SUPPLIES
from game.persistence import load_game, save_game
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from game.supplies import supplies_label, use_supply
from tests.test_gameplay import make_state, press

ITEM = press(Action.USE_ITEM)


def test_bandage_heals_and_is_used_up():
    state = make_state(player_hp=5, supplies={"bandage": 1})
    use_supply(ITEM, state)
    assert state.player_hp == 5 + SUPPLIES["bandage"]["heal"]
    assert state.supplies["bandage"] == 0
    assert state.events[-1].kind == "heal"


def test_heal_never_goes_past_max_hp():
    state = make_state(supplies={"bandage": 1})
    state.player_hp = state.player_max_hp - 2
    use_supply(ITEM, state)
    assert state.player_hp == state.player_max_hp


def test_the_most_needed_supply_is_used():
    state = make_state(player_hp=18, supplies={"bandage": 1, "lamp_oil": 1})
    state.lantern_fuel = lantern_capacity(state) * 0.2  # light is the bigger need
    use_supply(ITEM, state)
    assert state.supplies == {"bandage": 1, "lamp_oil": 0}
    assert state.lantern_fuel == pytest.approx(lantern_capacity(state) * 0.7)


@pytest.mark.parametrize("supplies,says", [({}, "No supplies"), ({"bandage": 2}, "don't need")])
def test_nothing_is_wasted(supplies, says):
    state = make_state(supplies=dict(supplies))
    use_supply(ITEM, state)
    assert says in state.hud_message and state.supplies == supplies


def test_supplies_are_sold_at_the_shop_and_shown_in_the_hud():
    state = make_state(active_scene="shop", shop_tab=0, player_gold=100)
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "lamp_oil")
    update_shop(press(Action.CONFIRM), state)
    assert state.supplies == {"lamp_oil": 1}
    assert state.player_gold == 100 - SUPPLIES["lamp_oil"]["cost"]
    assert supplies_label(state) == "Oil x1"


def test_supplies_round_trip_through_the_save():
    state = new_run(5)
    state.supplies = {"bandage": 2, "lamp_oil": 1}
    assert save_game(state) is None
    assert load_game().supplies == {"bandage": 2, "lamp_oil": 1}
