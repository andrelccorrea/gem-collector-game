from game import merchant
from game.daylight import DAY_SECONDS
from game.input import Action
from game.persistence import load_game, save_game
from game.scenes.merchant_cart import update_merchant
from game.simulation import new_run
from game.tile_info import describe_here
from game.tools import use_tool
from tests.test_gameplay import press


def _merchant_day(seed=5):
    state = new_run(seed)
    for d in range(200):
        state.game_time = d * DAY_SECONDS + 1
        if merchant.today(state):
            return state
    raise AssertionError("no merchant in 200 days")


def test_the_merchant_comes_on_some_days_beside_a_landmark():
    state = new_run(5)
    days = 0
    for d in range(200):
        state.game_time = d * DAY_SECONDS + 1
        visit = merchant.today(state)
        if visit:
            days += 1
            assert len(set(visit["stock"])) == 2
            assert state.world_tiles.meta[visit["pos"]]["walkable"]
    assert 0.25 < days / 200 < 0.55


def test_use_on_the_cart_opens_trade_and_stock_sells_out():
    state = _merchant_day()
    state.player_x, state.player_y = merchant.today(state)["pos"]
    assert "traveling merchant" in describe_here(state)
    use_tool(press(Action.USE), state)
    assert state.active_scene == "merchant"
    state.player_gold = 1000
    key = merchant.today(state)["stock"][0]
    assert merchant.buy(state, key) is None
    assert merchant.buy(state, key) == "Sold out!"
    update_merchant(press(Action.CANCEL), state)
    assert state.active_scene == "game"


def test_the_wanted_gem_pays_double_a_few_times_a_day():
    state = _merchant_day()
    wanted = merchant.today(state)["wants"]
    state.inventory["gems"] = {wanted: 9}
    paid = [merchant.sell_wanted(state) for _ in range(7)]
    assert paid[: merchant.WANTED_PER_DAY] == [merchant.wanted_price(state)] * 5
    assert paid[5:] == [0, 0]
    assert save_game(state) is None
    assert len(load_game().merchant_log) == merchant.WANTED_PER_DAY
