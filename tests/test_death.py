import pytest

from clingine.renderer import StubRenderer
from game import camera
from game.death import REVIVE_FEE_SHARE, recover_bag, revive_in_town
from game.gems import add_polished_gem, bag_capacity, polished_prices
from game.input import Action, InputState
from game.menu import MENU_ITEMS, _select_menu_item, update_death_screen, update_menu
from game.persistence import has_save, load_game, save_game
from game.simulation import new_run
from game.state import GameState
from game.tools import use_tool

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))
USE = InputState(pressed=frozenset({Action.USE}))
DOWN = InputState(pressed=frozenset({Action.MOVE_DOWN}))


def _menu_index(item_id):
    return [i for i, _ in MENU_ITEMS].index(item_id)


@pytest.fixture
def fallen():
    state = new_run(6)
    state.player_x, state.player_y = 60, 20
    state.player_gold, state.player_hp = 400, 0
    state.inventory["gems"] = {"garnet": 3}
    state.inventory["loot"] = {"bear_pelt": 1}
    add_polished_gem(state, "opal", 210)
    state.active_scene = "death"
    return state


def test_normal_death_drops_the_bag_and_revives_in_town_for_a_fee(fallen):
    update_death_screen(CONFIRM, fallen)
    assert fallen.active_scene == "game"
    assert (fallen.player_x, fallen.player_y) == fallen.world_tiles.start_pos
    assert fallen.player_hp == fallen.player_max_hp
    assert fallen.player_gold == 400 - int(400 * REVIVE_FEE_SHARE)
    assert fallen.inventory["gems"] == {} and fallen.inventory["loot"] == {}
    bag = fallen.dropped_bag
    assert (bag["x"], bag["y"]) == (60, 20)
    assert bag["gems"] == {"garnet": 3, "opal_polished": 1}
    assert bag["polished"] == {"opal_polished": [210]}


def test_walking_back_recovers_everything_with_prices(fallen):
    revive_in_town(fallen)
    fallen.player_x, fallen.player_y = 60, 20
    use_tool(USE, fallen)
    assert fallen.dropped_bag is None
    assert fallen.inventory["gems"] == {"garnet": 3, "opal_polished": 1}
    assert fallen.inventory["loot"] == {"bear_pelt": 1}
    assert polished_prices(fallen, "opal_polished") == [210]
    assert "Recovered 5" in fallen.hud_message


def test_recovery_stops_at_bag_capacity_and_keeps_the_rest(fallen):
    revive_in_town(fallen)
    fallen.player_x, fallen.player_y = 60, 20
    fallen.inventory["gems"] = {"quartz": bag_capacity(fallen) - 2}
    assert recover_bag(fallen) == 2
    left = sum(fallen.dropped_bag["gems"].values()) + sum(fallen.dropped_bag["loot"].values())
    assert left == 3


def test_dying_again_loses_the_older_bag(fallen):
    revive_in_town(fallen)
    fallen.player_x, fallen.player_y = 70, 25
    fallen.inventory["gems"] = {"quartz": 1}
    revive_in_town(fallen)
    assert fallen.dropped_bag["gems"] == {"quartz": 1}
    assert (fallen.dropped_bag["x"], fallen.dropped_bag["y"]) == (70, 25)


def test_dying_with_an_empty_bag_leaves_nothing_behind():
    state = new_run(6)
    revive_in_town(state)
    assert state.dropped_bag is None


def test_hardcore_death_ends_the_run_and_erases_its_save(fallen):
    fallen.hardcore = True
    save_game(fallen)
    update_death_screen(CONFIRM, fallen)
    assert fallen.active_scene == "menu"
    assert not has_save()


def test_hardcore_is_chosen_from_the_menu(monkeypatch):
    import random

    monkeypatch.setattr(random, "randint", lambda a, b: 77)
    state = GameState(menu_cursor=_menu_index("new_hardcore"))
    _select_menu_item(state, save_exists=False)
    assert state.hardcore and state.active_scene == "game"
    state = GameState(menu_cursor=_menu_index("new"))
    _select_menu_item(state, save_exists=False)
    assert not state.hardcore


def test_menu_cursor_skips_continue_without_a_save():
    state = GameState(menu_cursor=_menu_index("continue") - 1)
    update_menu(DOWN, state)
    assert state.menu_cursor == _menu_index("continue") + 1


def test_dropped_bag_and_mode_are_saved(fallen):
    fallen.hardcore = True
    revive_in_town(fallen)
    save_game(fallen)
    loaded = load_game()
    assert loaded.hardcore
    assert loaded.dropped_bag == fallen.dropped_bag


def test_dropped_bag_is_drawn_where_it_lies(fallen):
    revive_in_town(fallen)
    fallen.player_x, fallen.player_y = 62, 20
    camera.update_camera(fallen)
    fallen.world_tiles.meta[(60, 20)]["visibility"] = "visible"
    renderer = StubRenderer(80, 24)
    view = camera.render_view(fallen, renderer)
    camera.render_viewport(renderer, fallen, view)
    assert renderer.get_cell(60 - view.x, 20 - view.y)[0] == camera.DROPPED_BAG_CHAR
