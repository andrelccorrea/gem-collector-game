from collections import Counter

from game import deals
from game.daylight import DAY_SECONDS
from game.input import Action
from game.objects.registry import TOOL_CATALOG
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from tests.test_gameplay import press


def test_the_deal_changes_every_game_day_and_covers_the_whole_shop():
    state = new_run(4)
    picks = []
    for day in range(200):
        state.game_time = day * DAY_SECONDS + 10
        picks.append(deals.deal_key(state))
    state.game_time = 10
    assert deals.deal_key(state) == picks[0]  # the same all day
    assert len(set(picks)) >= len(deals._candidates()) - 2
    assert Counter(picks).most_common(1)[0][1] < 60


def test_the_deal_is_cheaper_in_the_shop_and_charged_at_that_price():
    state = new_run(4)
    for day in range(100):
        state.game_time = day * DAY_SECONDS
        if deals.deal_key(state) in TOOL_CATALOG:
            break
    tool = deals.deal_key(state)
    base = TOOL_CATALOG[tool].cost
    state.active_scene, state.shop_tab, state.player_gold = "shop", 0, 5000
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == tool)
    assert "DEAL" in items[state.shop_cursor]["label"]
    update_shop(press(Action.CONFIRM), state)
    assert state.player_gold == 5000 - round(base * (1 - deals.DISCOUNT))


def test_banner_names_the_deal_and_counts_down():
    state = new_run(4)
    state.game_time = DAY_SECONDS - 75
    assert deals.banner(state).endswith("(new deal in 1:15)")
