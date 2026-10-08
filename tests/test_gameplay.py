"""Behaviour tests for player, combat, tools, building entry and the shop."""

import pytest

from game.buildings import check_building_interaction
from game.combat import enemy_attacks, player_attack
from game.constants import (
    MAP_HEIGHT,
    MAP_WIDTH,
    PLAYER_ATTACK_COOLDOWN,
    WIN_LIFETIME_EARNINGS,
)
from game.enemies import Enemy
from game.gems import get_gem_raw_value
from game.input import EMPTY_INPUT, Action, InputState
from game.loop import STEP
from game.objects.registry import ENEMY_CATALOG, TOOL_CATALOG, TOOL_UPGRADE_COSTS
from game.player import update_player
from game.scenes.shop import _build_shop_items, update_shop
from game.state import GameState, gameplay_rng
from game.tilemap import TileMap
from game.tools import update_tools, use_tool
from game.world import _apply_tile


def press(*actions):
    return InputState(pressed=frozenset(actions))


def make_state(tiles=None, x=5, y=5, **overrides):
    """A 20x20 grass world (plus the given {(x, y): type} tiles) with the player at (x, y)."""
    world = TileMap(20, 20)
    for ty in range(20):
        for tx in range(20):
            _apply_tile(world, tx, ty, "grass")
    for (tx, ty), kind in (tiles or {}).items():
        _apply_tile(world, tx, ty, kind)
    state = GameState(world_tiles=world, world_gems={}, player_x=x, player_y=y, rng=gameplay_rng(1))
    state.equipped_tool = "shovel"
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


# ── Player ────────────────────────────────────────────────────────────────────


def test_player_cannot_walk_into_unwalkable_tiles():
    state = make_state({(6, 5): "tree"})
    update_player(press(Action.MOVE_RIGHT), state, STEP)
    assert (state.player_x, state.player_y) == (5, 5)


def test_player_is_clamped_to_the_map():
    state = GameState(player_x=MAP_WIDTH - 1, player_y=MAP_HEIGHT - 1)
    update_player(press(Action.MOVE_RIGHT), state, STEP)
    update_player(press(Action.MOVE_DOWN), state, STEP * 10)
    assert (state.player_x, state.player_y) == (MAP_WIDTH - 1, MAP_HEIGHT - 1)


def test_zero_hp_switches_to_the_death_screen():
    state = make_state(player_hp=0)
    update_player(EMPTY_INPUT, state, STEP)
    assert state.active_scene == "death"


def test_hud_message_expires():
    from game.player import set_hud_message

    state = make_state()
    set_hud_message(state, "hello", 0.5)
    for _ in range(20):
        update_player(EMPTY_INPUT, state, STEP)
    assert state.hud_message == ""


# ── Combat ────────────────────────────────────────────────────────────────────


def _snake(x, y):
    return Enemy(x, y, "snake")


def test_attack_hits_an_adjacent_enemy_with_tool_damage_and_level_bonus():
    state = make_state()
    state.inventory["tools"]["shovel"]["level"] = 3
    enemy = _snake(6, 6)  # diagonal counts as adjacent
    enemy.hp = enemy.max_hp = 100
    state.enemies = [enemy]
    player_attack(press(Action.ATTACK), state)
    assert enemy.hp == 100 - (TOOL_CATALOG["shovel"].melee_damage + 2)
    assert state.last_combat_time == state.game_time


def test_attack_without_an_adjacent_enemy_says_so():
    state = make_state()
    state.enemies = [_snake(8, 5)]
    player_attack(press(Action.ATTACK), state)
    assert state.hud_message == "No enemy in range!"
    assert state.enemies[0].hp == state.enemies[0].max_hp


def test_killing_an_enemy_gives_its_loot_and_gold():
    state = make_state()
    enemy = _snake(5, 4)
    enemy.hp = 1
    state.enemies = [enemy]
    player_attack(press(Action.ATTACK), state)
    snake = ENEMY_CATALOG["snake"]
    assert state.enemies == []
    assert state.inventory["loot"] == {snake.loot: 1}
    assert state.player_gold == 50 + snake.loot_value


def test_held_attack_key_is_rate_limited():
    state = make_state()
    enemy = _snake(5, 6)
    enemy.hp = enemy.max_hp = 100
    state.enemies = [enemy]
    hits = 0
    for _ in range(30):  # one second of key auto-repeat, one press per step
        before = enemy.hp
        player_attack(press(Action.ATTACK), state)
        hits += enemy.hp < before
        state.game_time += STEP
    assert hits == pytest.approx(1.0 / PLAYER_ATTACK_COOLDOWN, abs=1)


def test_adjacent_enemy_attacks_on_its_cooldown_and_can_kill():
    state = make_state(player_hp=5)
    enemy = _snake(6, 5)
    enemy.attack, enemy.attack_cooldown_max, enemy.attack_cooldown = 2, 1.0, 0.0
    state.enemies = [enemy]
    enemy_attacks(state, STEP)
    assert state.player_hp == 3
    enemy_attacks(state, 0.5)  # still cooling down
    assert state.player_hp == 3
    enemy_attacks(state, 0.6)
    enemy_attacks(state, 1.1)
    assert state.player_hp == 0 and state.active_scene == "death"


def test_distant_enemies_do_not_attack():
    state = make_state()
    enemy = _snake(9, 9)
    enemy.attack_cooldown = 0.0
    state.enemies = [enemy]
    enemy_attacks(state, STEP)
    assert state.player_hp == 20


# ── Tools ─────────────────────────────────────────────────────────────────────


def test_cycle_tool_goes_through_owned_tools():
    state = make_state()
    state.inventory["tools"] = {"shovel": {"level": 1}, "pickaxe": {"level": 1}}
    update_tools(press(Action.CYCLE_TOOL), state)
    assert state.equipped_tool == "pickaxe"
    update_tools(press(Action.CYCLE_TOOL), state)
    assert state.equipped_tool == "shovel"


def test_digging_a_compatible_tile_depletes_it_once():
    state = make_state({(5, 5): "mineable_grass"})
    use_tool(press(Action.USE), state)
    assert (5, 5) in state.depleted_tiles
    gems_after_first = dict(state.inventory["gems"])
    use_tool(press(Action.USE), state)
    assert state.hud_message == "Already worked. Try elsewhere."
    assert state.inventory["gems"] == gems_after_first


def test_wrong_tool_does_not_dig():
    state = make_state({(5, 5): "mineable_rock"})
    use_tool(press(Action.USE), state)
    assert state.depleted_tiles == set()
    assert "won't work" in state.hud_message


def test_visible_gem_is_picked_up():
    state = make_state({(5, 5): "mineable_grass"})
    state.world_gems = {(5, 5): "quartz"}
    use_tool(press(Action.USE), state)
    assert state.world_gems == {}
    assert state.inventory["gems"] == {"quartz": 1}


def test_digging_finds_gems_some_of_the_time():
    found = 0
    for seed in range(60):
        state = make_state({(5, 5): "mineable_grass"})
        state.rng = gameplay_rng(seed)
        use_tool(press(Action.USE), state)
        found += sum(state.inventory["gems"].values())
    assert 0 < found < 60


# ── Buildings and shop ────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "kind,scene", [("shop", "shop"), ("lapidary", "lapidary"), ("save", "save_point")]
)
def test_using_a_building_tile_opens_its_screen(kind, scene):
    state = make_state({(5, 5): kind}, shop_cursor=4, shop_tab=2, lapidary_cursor=3)
    check_building_interaction(press(Action.USE), state)
    assert state.active_scene == scene
    if scene == "shop":
        assert (state.shop_cursor, state.shop_tab) == (0, 0)
    if scene == "lapidary":
        assert state.lapidary_cursor == 0


def _select(state, action, key=None):
    items = _build_shop_items(state)
    state.shop_cursor = next(
        i for i, item in enumerate(items) if item["action"] == action and item["key"] == key
    )
    update_shop(press(Action.CONFIRM), state)


def test_buying_a_tool_costs_gold_once():
    state = make_state(active_scene="shop", player_gold=500)
    _select(state, "buy_tool", "pickaxe")
    assert "pickaxe" in state.inventory["tools"]
    assert state.player_gold == 500 - TOOL_CATALOG["pickaxe"].cost


def test_cannot_buy_without_enough_gold():
    state = make_state(active_scene="shop", player_gold=1)
    _select(state, "buy_tool", "pickaxe")
    assert "pickaxe" not in state.inventory["tools"]
    assert state.hud_message == "Not enough gold!"


def test_upgrading_a_tool_raises_its_level():
    state = make_state(active_scene="shop", player_gold=500, shop_tab=1)
    _select(state, "upgrade_tool", "shovel")
    assert state.inventory["tools"]["shovel"]["level"] == 2
    assert state.player_gold == 500 - TOOL_UPGRADE_COSTS[2]


def test_selling_counts_toward_lifetime_earnings_and_can_win():
    state = make_state(active_scene="shop", shop_tab=2)
    state.lifetime_earnings = WIN_LIFETIME_EARNINGS - get_gem_raw_value("quartz")
    state.inventory["gems"] = {"quartz": 1}
    _select(state, "sell_gem", "quartz")
    assert state.lifetime_earnings == WIN_LIFETIME_EARNINGS  # reaching it exactly wins
    assert state.active_scene == "win" and state.has_won


def test_loot_sells_for_its_catalog_value():
    state = make_state(active_scene="shop", shop_tab=3)
    pelt = ENEMY_CATALOG["bear"].loot
    state.inventory["loot"] = {pelt: 2}
    _select(state, "sell_all_loot")
    assert state.player_gold == 50 + 2 * ENEMY_CATALOG["bear"].loot_value
    assert state.inventory["loot"] == {}
