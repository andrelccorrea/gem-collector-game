import random

from clingine.renderer import StubRenderer
from game.gems import (
    add_polished_gem,
    get_gem_polished_value,
    polished_prices,
    polished_value_range,
)
from game.input import Action, InputState
from game.scenes.lapidary import _build_lapidary_items, render_lapidary, update_lapidary
from game.scenes.shop import _build_shop_items, update_shop
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def _screen(renderer):
    return "\n".join(
        "".join(renderer.get_cell(x, y)[0] for x in range(renderer.width))
        for y in range(renderer.height)
    )


def _cut(state, gem):
    state.lapidary_cursor = next(
        i for i, item in enumerate(_build_lapidary_items(state)) if item.get("key") == gem
    )
    update_lapidary(CONFIRM, state)


def test_each_cut_keeps_its_own_price():
    state = GameState(player_gold=10_000)
    state.inventory["gems"] = {"ruby": 2}
    _cut(state, "ruby")
    first = list(polished_prices(state, "ruby_polished"))
    _cut(state, "ruby")
    prices = polished_prices(state, "ruby_polished")
    assert len(prices) == 2 and state.inventory["gems"]["ruby_polished"] == 2
    assert first[0] in prices  # the first gem was not re-priced by the second cut


def test_rolled_prices_stay_inside_the_advertised_range():
    rng = random.Random(3)
    for level in (1, 3, 5):
        low, high = polished_value_range("ruby", level)
        rolls = [get_gem_polished_value("ruby", level, rng) for _ in range(300)]
        assert low <= min(rolls) and max(rolls) <= high
        assert max(rolls) > min(rolls)


def test_machine_upgrades_raise_the_top_of_the_range():
    # Each machine level's maximum multiplier now counts, not only its minimum.
    highs = [polished_value_range("ruby", level)[1] for level in (1, 2, 3, 4, 5)]
    assert highs == sorted(highs) and highs[1] > highs[0]


def test_preview_shows_a_stable_range():
    state = GameState(player_gold=10_000)
    state.inventory["gems"] = {"ruby": 1}
    low, high = polished_value_range("ruby", state.lapidary_level)
    frames = []
    for _ in range(5):
        renderer = StubRenderer(80, 24)
        render_lapidary(renderer, state)
        frames.append(_screen(renderer))
    assert len(set(frames)) == 1
    assert f"${low}-${high}" in frames[0]


def test_selling_polished_gems_sells_the_most_valuable_first():
    state = GameState(active_scene="shop", shop_tab=2)
    for price in (120, 300, 180):
        add_polished_gem(state, "opal", price)
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "opal_polished")
    assert "$120-$300" in items[state.shop_cursor]["label"]

    update_shop(CONFIRM, state)
    assert state.player_gold == 50 + 300
    assert polished_prices(state, "opal_polished") == [180, 120]
    assert state.inventory["gems"]["opal_polished"] == 2


def test_sell_all_adds_every_individual_price():
    state = GameState(active_scene="shop", shop_tab=2)
    for price in (120, 300):
        add_polished_gem(state, "opal", price)
    state.inventory["gems"]["quartz"] = 2
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["action"] == "sell_all_gems")
    update_shop(CONFIRM, state)
    assert state.player_gold == 50 + 420 + 2 * 5
    assert state.inventory["gems"] == {} and state.polished_gem_values == {}
