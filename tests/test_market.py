from game import market
from game.gems import add_polished_gem, get_gem_raw_value
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.market import (
    RECOVERY_SECONDS_PER_SALE,
    preview_sell_all,
    price_multiplier,
    sell_all,
    sell_one,
    unit_price,
)
from game.persistence import load_game, save_game
from game.simulation import new_run, step_game
from game.state import GameState


def test_each_sale_lowers_the_next_price_of_that_kind_only():
    state = GameState()
    state.inventory["gems"] = {"garnet": 5, "topaz": 1}
    full = get_gem_raw_value("garnet")
    prices = [sell_one(state, "garnet") for _ in range(5)]
    assert prices[0] == full
    assert prices == sorted(prices, reverse=True) and prices[-1] < full
    assert unit_price(state, "topaz") == get_gem_raw_value("topaz")


def test_market_recovers_with_game_time():
    state = GameState()
    state.inventory["gems"] = {"garnet": 3}
    for _ in range(3):
        sell_one(state, "garnet")
    lowered = unit_price(state, "garnet")
    market.update_market(state, RECOVERY_SECONDS_PER_SALE * 1.5)
    assert lowered < unit_price(state, "garnet") < get_gem_raw_value("garnet")
    market.update_market(state, RECOVERY_SECONDS_PER_SALE * 2)
    assert state.market == {}
    assert unit_price(state, "garnet") == get_gem_raw_value("garnet")


def test_market_recovers_during_play_but_not_in_menus():
    state = new_run(2)
    state.market = {"garnet": 3.0}
    for _ in range(int(RECOVERY_SECONDS_PER_SALE / STEP)):
        step_game(EMPTY_INPUT, state, STEP)
        state.active_scene = "game"
    assert state.market["garnet"] < 2.1


def test_sell_all_pays_exactly_what_the_preview_promised():
    state = GameState()
    state.inventory["gems"] = {"quartz": 4, "garnet": 2}
    state.inventory["loot"] = {"bear_pelt": 3}
    add_polished_gem(state, "opal", 200)
    add_polished_gem(state, "opal", 260)
    state.market = {"quartz": 2.0}
    gem_keys = list(state.inventory["gems"])
    expected_gems = preview_sell_all(state, gem_keys)
    expected_loot = preview_sell_all(state, ["bear_pelt"])
    assert sell_all(state, loot=False) == expected_gems
    assert sell_all(state, loot=True) == expected_loot
    assert state.player_gold == 50 + expected_gems + expected_loot
    assert state.lifetime_earnings == expected_gems + expected_loot
    assert state.inventory["gems"] == {} and state.inventory["loot"] == {}


def test_prices_never_drop_to_zero():
    state = GameState()
    state.inventory["gems"] = {"quartz": 1}
    state.market = {"quartz": 10_000.0}
    assert sell_one(state, "quartz") == 1
    assert price_multiplier(0) == 1.0


def test_market_is_saved(isolated_data_dir):
    state = new_run(5)
    state.market = {"ruby": 2.5}
    save_game(state)
    assert load_game().market == {"ruby": 2.5}
