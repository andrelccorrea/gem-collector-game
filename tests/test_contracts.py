from game import contracts
from game.daylight import DAY_SECONDS
from game.input import Action
from game.persistence import load_game, save_game
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from tests.test_gameplay import press


def test_the_board_changes_each_day_and_pays_above_value():
    state = new_run(9)
    today = contracts.offers(state)
    assert contracts.offers(state) == today and len(today) == 3
    boards = []
    for day in range(30):
        state.game_time = day * DAY_SECONDS
        boards.append(tuple(o["item"] for o in contracts.offers(state)))
    assert len(set(boards)) > 20
    for offer in today:
        value = contracts._value(offer["item"]) * offer["count"]
        assert offer["reward"] > value and 2 <= offer["count"] <= 4
    assert today[1]["loot"] and not today[0]["loot"]


def test_delivering_takes_the_items_pays_and_counts_as_earnings_once_per_day():
    state = new_run(9)
    offer = contracts.offers(state)[0]
    state.inventory["gems"] = {offer["item"]: offer["count"] + 1}
    gold, earned = state.player_gold, state.lifetime_earnings
    state.active_scene, state.shop_tab = "shop", 6
    _build_shop_items(state)
    state.shop_cursor = 0
    update_shop(press(Action.CONFIRM), state)
    assert state.inventory["gems"] == {offer["item"]: 1}
    assert state.player_gold == gold + offer["reward"]
    assert state.lifetime_earnings == earned + offer["reward"]
    update_shop(press(Action.CONFIRM), state)  # already delivered today
    assert state.player_gold == gold + offer["reward"]
    assert "(Done)" in _build_shop_items(state)[0]["label"]
    assert save_game(state) is None
    assert (0, 0) in load_game().contracts_done


def test_a_contract_needs_the_whole_order():
    state = new_run(9)
    offer = contracts.offers(state)[2]
    state.inventory["gems"] = {offer["item"]: offer["count"] - 1}
    assert contracts.deliver(state, 2) == 0
    assert state.inventory["gems"] == {offer["item"]: offer["count"] - 1}
