import random

from clingine.renderer import StubRenderer
from game.gems import (
    add_polished_gem,
    get_gem_polished_value,
    polished_prices,
    polished_value_range,
)
from game.input import EMPTY_INPUT, Action, InputState
from game.market import price_multiplier
from game.scenes.lapidary import (
    CUT_BAR_WIDTH,
    CUT_SWEEP_SECONDS,
    _build_lapidary_items,
    cut_quality,
    marker_position,
    render_lapidary,
    update_lapidary,
)
from game.scenes.shop import _build_shop_items, update_shop
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def _screen(renderer):
    return "\n".join(
        "".join(renderer.get_cell(x, y)[0] for x in range(renderer.width))
        for y in range(renderer.height)
    )


def _cut(state, gem, elapsed=None):
    """Start cutting ``gem`` and stop the marker after ``elapsed`` seconds (center)."""
    state.lapidary_cursor = next(
        i for i, item in enumerate(_build_lapidary_items(state)) if item.get("key") == gem
    )
    update_lapidary(CONFIRM, state)
    update_lapidary(EMPTY_INPUT, state, CUT_SWEEP_SECONDS / 4 if elapsed is None else elapsed)
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
    sell_all = next(i for i, it in enumerate(items) if it["action"] == "sell_all_gems")
    # Highest polished first at full price, then each repeat sale a little cheaper.
    expected = 300 + int(120 * price_multiplier(1)) + 5 + int(5 * price_multiplier(1))
    assert f"${expected} total" in items[sell_all]["label"]
    state.shop_cursor = sell_all
    update_shop(CONFIRM, state)
    assert state.player_gold == 50 + expected
    assert state.inventory["gems"] == {} and state.polished_gem_values == {}


def test_selling_the_last_polished_gem_leaves_no_empty_price_list():
    state = GameState(active_scene="shop", shop_tab=2)
    add_polished_gem(state, "opal", 150)
    state.shop_cursor = 0
    update_shop(CONFIRM, state)
    assert "opal_polished" not in state.polished_gem_values


# ── Cutting minigame ──────────────────────────────────────────────────────────


def test_marker_sweeps_across_the_bar_and_back():
    positions = [marker_position(CUT_SWEEP_SECONDS * i / 20) for i in range(21)]
    assert positions[0] == 0 and positions[-1] == 0
    assert max(positions) == CUT_BAR_WIDTH - 1
    assert marker_position(CUT_SWEEP_SECONDS / 4) == CUT_BAR_WIDTH // 2


def test_quality_depends_on_distance_from_the_center():
    center = CUT_BAR_WIDTH // 2
    assert cut_quality(center)[0] == "Flawless"
    assert cut_quality(center + 3)[0] == "Excellent"
    assert cut_quality(center - 7)[0] == "Good"
    assert cut_quality(0)[0] == "Poor"


def test_a_centered_cut_is_worth_the_top_of_the_range():
    state = GameState(player_gold=10_000)
    state.inventory["gems"] = {"ruby": 1}
    low, high = polished_value_range("ruby", 1)
    _cut(state, "ruby")
    price = polished_prices(state, "ruby_polished")[0]
    assert low + 0.9 * (high - low) <= price <= high
    assert "Flawless" in state.hud_message


def test_a_mistimed_cut_is_worth_the_bottom_of_the_range():
    state = GameState(player_gold=10_000)
    state.inventory["gems"] = {"ruby": 1}
    low, high = polished_value_range("ruby", 1)
    _cut(state, "ruby", elapsed=0.0)  # marker still at the left edge
    price = polished_prices(state, "ruby_polished")[0]
    assert low <= price <= low + 0.25 * (high - low) + 1


def test_the_fee_is_paid_and_the_gem_used_only_when_the_cut_is_made():
    state = GameState(player_gold=1000)
    state.inventory["gems"] = {"ruby": 1}
    items = _build_lapidary_items(state)
    state.lapidary_cursor = next(i for i, it in enumerate(items) if it.get("key") == "ruby")
    fee = items[state.lapidary_cursor]["cut_fee"]
    update_lapidary(CONFIRM, state)
    assert state.cutting is not None
    assert state.player_gold == 1000 and state.inventory["gems"] == {"ruby": 1}

    update_lapidary(InputState(pressed=frozenset({Action.CANCEL})), state)
    assert state.cutting is None and state.active_scene != "game"
    assert state.player_gold == 1000 and state.inventory["gems"] == {"ruby": 1}

    _cut(state, "ruby")
    assert state.player_gold == 1000 - fee and "ruby" not in state.inventory["gems"]


def test_the_minigame_is_drawn_while_cutting():
    state = GameState(player_gold=1000)
    state.inventory["gems"] = {"ruby": 1}
    state.cutting = {"gem": "ruby", "fee": 10, "elapsed": CUT_SWEEP_SECONDS / 4}
    renderer = StubRenderer(80, 24)
    render_lapidary(renderer, state)
    screen = _screen(renderer)
    assert "stop the marker" in screen and "^" in screen


def test_each_quality_has_its_own_cue_and_the_result_stays_on_screen():
    from game.scenes.lapidary import CUT_SOUNDS, RESULT_SECONDS

    state = GameState(player_gold=10_000)
    state.inventory["gems"] = {"quartz": 2}
    _cut(state, "quartz")  # dead center
    assert state.events[-1].kind == CUT_SOUNDS["Flawless"]
    assert state.cut_result["quality"] == "Flawless"
    renderer = StubRenderer(79, 23)
    render_lapidary(renderer, state)
    assert "Flawless cut (dead center)" in _screen(renderer)
    update_lapidary(EMPTY_INPUT, state, RESULT_SECONDS + 0.1)
    assert state.cut_result is None
    _cut(state, "quartz", elapsed=0.0)  # left edge
    assert state.events[-1].kind == CUT_SOUNDS["Poor"]
    assert "off center" in state.cut_result["text"]


def test_great_cuts_in_a_row_earn_a_streak_bonus():
    from game.scenes.lapidary import STREAK_BONUS

    state = GameState(player_gold=10_000, rng=random.Random(1))
    state.inventory["gems"] = {"quartz": 3}
    _cut(state, "quartz")
    _cut(state, "quartz")
    assert state.cut_streak == 2 and "Streak +5%" in state.hud_message
    _cut(state, "quartz", elapsed=0.0)
    assert state.cut_streak == 0
    assert STREAK_BONUS == 0.05


def test_refusals_sound_like_refusals():
    state = GameState(player_gold=0)
    state.inventory["gems"] = {"quartz": 1}
    _cut(state, "quartz")
    assert state.events and state.events[-1].kind == "denied"
