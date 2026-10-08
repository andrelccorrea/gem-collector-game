"""Tool tiers, bag capacity and earnings-gated shop stock."""

import random

import pytest

from game.gems import bag_capacity, bag_count, effective_tier, roll_gem_drop
from game.hud import render_hud
from game.input import Action, InputState
from game.objects.registry import (
    BAG_CAPACITIES,
    BAG_COSTS,
    BAG_UNLOCK_AT,
    GEM_CATALOG,
    TOOL_UPGRADE_UNLOCK_AT,
)
from game.scenes.lapidary import _build_lapidary_items, update_lapidary
from game.scenes.shop import _build_shop_items, update_shop
from game.tools import use_tool
from tests.test_gameplay import make_state

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))
USE = InputState(pressed=frozenset({Action.USE}))


def _drops(biome, tier, n=3000, seed=1):
    rng = random.Random(seed)
    return [roll_gem_drop(biome, tier, rng) for _ in range(n)]


# ── Tool tiers ────────────────────────────────────────────────────────────────


def test_effective_tier_grows_with_upgrades():
    assert effective_tier("shovel", 1) == 1
    assert effective_tier("shovel", 3) == 2
    assert effective_tier("pickaxe", 1) == 2
    assert effective_tier("pickaxe", 5) == 4


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_low_tiers_never_find_gems_above_their_tier(tier):
    found = {g for g in _drops("cave", tier) if g}
    assert found
    assert all(GEM_CATALOG[g].min_tier <= tier for g in found)


def test_top_gems_need_a_high_tier():
    assert "diamond" not in _drops("cave", 2, n=20000)
    assert "diamond" in _drops("cave", 4, n=20000)


def test_higher_tiers_dig_up_something_more_often():
    rate = {t: sum(g is not None for g in _drops("hillside", t)) for t in (1, 2, 4)}
    assert rate[1] < rate[2] < rate[4]


# ── Bag ───────────────────────────────────────────────────────────────────────


def test_full_bag_stops_digging_without_using_up_the_spot():
    state = make_state({(5, 5): "mineable_grass"})
    state.inventory["gems"] = {"quartz": bag_capacity(state)}
    use_tool(USE, state)
    assert state.depleted_tiles == set()
    assert "bag is full" in state.hud_message


def test_full_bag_stops_picking_up_visible_gems():
    state = make_state({(5, 5): "mineable_grass"})
    state.world_gems = {(5, 5): "quartz"}
    state.inventory["loot"] = {"snake_skin": bag_capacity(state)}
    use_tool(USE, state)
    assert state.world_gems == {(5, 5): "quartz"}


def _row(state, action):
    items = _build_shop_items(state)
    return next(i for i, it in enumerate(items) if it["action"] == action), items


def test_bigger_bag_can_be_bought_and_raises_capacity():
    state = make_state(active_scene="shop", shop_tab=1, player_gold=1000)
    state.shop_cursor, _ = _row(state, "upgrade_gear")
    update_shop(CONFIRM, state)
    assert state.bag_level == 1
    assert bag_capacity(state) == BAG_CAPACITIES[1]
    assert state.player_gold == 1000 - BAG_COSTS[1]


def test_bag_sizes_unlock_with_lifetime_earnings():
    locked_level = next(i for i, need in enumerate(BAG_UNLOCK_AT) if need > 0)
    state = make_state(active_scene="shop", shop_tab=1, player_gold=10_000)
    state.bag_level = locked_level - 1
    state.shop_cursor, items = _row(state, "upgrade_gear")
    assert not items[state.shop_cursor]["enabled"]
    assert f"${BAG_UNLOCK_AT[locked_level]}" in items[state.shop_cursor]["label"]
    update_shop(CONFIRM, state)
    assert state.bag_level == locked_level - 1

    state.lifetime_earnings = BAG_UNLOCK_AT[locked_level]
    update_shop(CONFIRM, state)
    assert state.bag_level == locked_level


def test_high_tool_levels_unlock_with_lifetime_earnings():
    level, need = min(TOOL_UPGRADE_UNLOCK_AT.items())
    state = make_state(active_scene="shop", shop_tab=1, player_gold=10_000)
    state.inventory["tools"]["shovel"]["level"] = level - 1
    items = _build_shop_items(state)
    row = next(i for i, it in enumerate(items) if it["key"] == "shovel")
    assert not items[row]["enabled"] and f"${need}" in items[row]["label"]
    state.shop_cursor = row
    update_shop(CONFIRM, state)
    assert state.inventory["tools"]["shovel"]["level"] == level - 1
    state.lifetime_earnings = need
    update_shop(CONFIRM, state)
    assert state.inventory["tools"]["shovel"]["level"] == level


def test_top_lapidary_levels_unlock_with_lifetime_earnings():
    state = make_state(active_scene="lapidary", player_gold=10_000, lapidary_level=3)
    items = _build_lapidary_items(state)
    state.lapidary_cursor = next(
        i for i, it in enumerate(items) if it["action"] == "upgrade_lapidary"
    )
    assert "unlocks" in items[state.lapidary_cursor]["label"]
    update_lapidary(CONFIRM, state)
    assert state.lapidary_level == 3
    state.lifetime_earnings = 2500
    update_lapidary(CONFIRM, state)
    assert state.lapidary_level == 4


def test_hud_shows_bag_fill(stub_renderer):
    state = make_state()
    state.inventory["gems"] = {"quartz": 3}
    state.inventory["loot"] = {"snake_skin": 1}
    render_hud(stub_renderer, state)
    text = "".join(stub_renderer.get_cell(x, 23)[0] for x in range(80))
    assert f"Bag:{bag_count(state)}/{bag_capacity(state)}" in text
