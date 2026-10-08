"""Armor, boots and the drill: shop rows and their effect in play."""

import pytest

from game.combat import enemy_attacks
from game.constants import MOVE_COOLDOWN
from game.enemies import Enemy
from game.gems import effective_tier
from game.input import Action
from game.loop import STEP
from game.objects.registry import ARMOR, BOOTS, TOOL_CATALOG
from game.player import update_player
from game.scenes.shop import _build_shop_items, update_shop
from game.tools import use_tool
from tests.test_gameplay import make_state, press

CONFIRM = press(Action.CONFIRM)


@pytest.mark.parametrize("level,attack,taken", [(0, 5, 5), (2, 5, 3), (3, 2, 1)])
def test_armor_blocks_damage_but_a_hit_always_hurts(level, attack, taken):
    state = make_state(player_hp=20, armor_level=level)
    enemy = Enemy(6, 5, "snake")
    enemy.attack, enemy.attack_cooldown = attack, 0.0
    state.enemies = [enemy]
    enemy_attacks(state, STEP)
    assert state.player_hp == 20 - taken
    assert state.events[-1].text == f"-{taken}"


def _steps_in(state, seconds):
    start = state.player_x
    for _ in range(int(seconds / STEP)):
        update_player(press(Action.MOVE_RIGHT), state, STEP)
    return state.player_x - start


def test_boots_make_the_player_faster():
    slow = _steps_in(make_state(x=0, y=0), 1.0)
    fast = _steps_in(make_state(x=0, y=0, boots_level=len(BOOTS["step_multipliers"]) - 1), 1.0)
    assert slow == pytest.approx(1 / MOVE_COOLDOWN, abs=1)
    assert fast > slow


@pytest.mark.parametrize("gear,attr", [("armor", "armor_level"), ("boots", "boots_level")])
def test_gear_is_bought_level_by_level_and_unlocks_with_earnings(gear, attr):
    table = ARMOR if gear == "armor" else BOOTS
    state = make_state(active_scene="shop", shop_tab=1, player_gold=10_000)
    for level in range(1, len(table["costs"])):
        state.lifetime_earnings = max(0, table["unlock_at"][level] - 1)
        items = _build_shop_items(state)
        state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == gear)
        if table["unlock_at"][level] > 0:
            assert not items[state.shop_cursor]["enabled"]
            state.lifetime_earnings += 1
        gold = state.player_gold
        update_shop(CONFIRM, state)
        assert getattr(state, attr) == level
        assert state.player_gold == gold - table["costs"][level]
    items = _build_shop_items(state)
    assert "(Best)" in next(it for it in items if it["key"] == gear)["label"]


def test_the_drill_digs_any_ground_at_the_top_tier():
    drill = TOOL_CATALOG["drill"]
    assert effective_tier("drill", 1) == drill.tier == 3
    for kind in ("mineable_grass", "mineable_dirt", "mineable_rock"):
        state = make_state({(5, 5): kind})
        state.inventory["tools"]["drill"] = {"level": 1}
        state.equipped_tool = "drill"
        use_tool(press(Action.USE), state)
        assert state.world_tiles.meta[(5, 5)]["depleted"], kind


def test_the_selected_item_is_described():
    from clingine.renderer import StubRenderer
    from game.scenes.shop import render_shop

    renderer = StubRenderer(79, 23)
    state = make_state(active_scene="shop", shop_tab=1)
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "boots")
    render_shop(renderer, state)
    row = "".join(renderer.get_cell(x, 20)[0] for x in range(79))
    assert "Walk faster" in row


def test_purchases_chime_and_refusals_are_marked():
    state = make_state(active_scene="shop", shop_tab=0, player_gold=1000)
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "bandage")
    update_shop(CONFIRM, state)
    assert state.events[-1].kind == "coin"
    state.player_gold = 0
    update_shop(CONFIRM, state)
    assert state.events[-1].kind == "denied" and state.hud_message == "Not enough gold!"
