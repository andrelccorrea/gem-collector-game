from game.constants import RECALL_CHARM_COST
from game.hud import render_hud
from game.input import Action, InputState, map_keys
from game.loop import STEP
from game.persistence import load_game, save_game
from game.player import update_player
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run

RECALL = InputState(pressed=frozenset({Action.RECALL}))
CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def test_r_key_is_recall():
    assert map_keys({"r"}).pressed == {Action.RECALL}


def test_charm_is_bought_at_the_shop():
    state = new_run(2)
    state.active_scene, state.shop_tab, state.player_gold = "shop", 0, 100
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["action"] == "buy_charm")
    update_shop(CONFIRM, state)
    assert state.recall_charms == 1
    assert state.player_gold == 100 - RECALL_CHARM_COST


def test_recall_teleports_to_town_and_uses_a_charm():
    state = new_run(2)
    state.player_x, state.player_y, state.recall_charms = 150, 60, 2
    update_player(RECALL, state, STEP)
    assert (state.player_x, state.player_y) == state.world_tiles.start_pos
    assert state.recall_charms == 1


def test_recall_without_a_charm_or_in_town_does_nothing():
    state = new_run(2)
    state.player_x, state.player_y = 150, 60
    update_player(RECALL, state, STEP)
    assert (state.player_x, state.player_y) == (150, 60)
    assert "No Recall Charm" in state.hud_message

    state.recall_charms = 1
    state.player_x, state.player_y = state.world_tiles.start_pos
    update_player(RECALL, state, STEP)
    assert state.recall_charms == 1


def test_charms_are_saved():
    state = new_run(2)
    state.recall_charms = 3
    save_game(state)
    assert load_game().recall_charms == 3


def test_hud_mentions_recall_and_still_fits(stub_renderer):
    state = new_run(2)
    state.bag_level, state.lifetime_earnings = 3, 12_345
    state.inventory["gems"] = {"quartz": 59}
    renderer = stub_renderer.__class__(79, 23)  # an 80x24 terminal's usable area
    render_hud(renderer, state)
    row = "".join(renderer.get_cell(x, 22)[0] for x in range(79))
    assert "[R]Recall" in row and "Earned:$12345" in row
