from game import daylight
from game.input import Action
from game.lantern import lantern_capacity, update_lantern
from game.market import sell_one
from game.persistence import load_game, save_game
from game.player import update_player
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from game.state import gameplay_rng
from game.tools import use_tool
from tests.test_gameplay import make_state, press


def _buy(state, key):
    state.active_scene, state.shop_tab = "shop", 0
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == key)
    update_shop(press(Action.CONFIRM), state)


def test_one_trinket_is_worn_at_a_time_and_owned_ones_are_free_to_swap():
    state = make_state(player_gold=2000)
    _buy(state, "clover")
    _buy(state, "scale")
    assert state.trinket == "scale" and state.trinkets == ["clover", "scale"]
    gold = state.player_gold
    _buy(state, "clover")
    assert state.trinket == "clover" and state.player_gold == gold


def test_lucky_clover_finds_more():
    def finds(trinket):
        total = 0
        for seed in range(150):
            state = make_state({(5, 5): "mineable_grass"}, trinket=trinket)
            state.rng = gameplay_rng(seed)
            use_tool(press(Action.USE), state)
            total += sum(state.inventory["gems"].values())
        return total

    assert finds("clover") > finds(None)


def test_night_pin_saves_fuel_only_at_night():
    state = new_run(3)
    state.player_x, state.player_y, state.trinket = 150, 40, "night_pin"
    state.game_time = 0.8 * daylight.DAY_SECONDS
    update_lantern(state, 10.0)
    assert state.lantern_fuel == lantern_capacity(state)
    state.game_time = 10.0
    update_lantern(state, 10.0)
    assert state.lantern_fuel < lantern_capacity(state)


def test_merchants_scale_halves_the_price_drop():
    plain = make_state()
    plain.inventory["gems"] = {"quartz": 2}
    sell_one(plain, "quartz")
    weighed = make_state(trinket="scale")
    weighed.inventory["gems"] = {"quartz": 2}
    sell_one(weighed, "quartz")
    assert weighed.market["quartz"] == plain.market["quartz"] / 2


def test_homing_feather_recalls_once_a_day_and_trinkets_are_saved():
    state = new_run(3)
    state.trinket, state.trinkets = "feather", ["feather"]
    state.player_x, state.player_y = 150, 60
    update_player(press(Action.RECALL), state, 0.1)
    assert (state.player_x, state.player_y) == state.world_tiles.start_pos
    state.player_x, state.player_y = 150, 60
    update_player(press(Action.RECALL), state, 0.1)
    assert (state.player_x, state.player_y) != state.world_tiles.start_pos  # not twice a day
    assert save_game(state) is None
    loaded = load_game()
    assert loaded.trinket == "feather" and loaded.feather_day == state.feather_day
