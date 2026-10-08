from clingine.renderer import StubRenderer
from game.gems import GEODE, get_gem_raw_value
from game.input import Action, InputState
from game.market import MUSEUM_BONUS, MUSEUM_MILESTONE, museum_bonus, sell_one
from game.objects.registry import GEM_CATALOG
from game.persistence import load_game, save_game
from game.scenes.shop import SHOP_TABS, _build_shop_items, render_shop, update_shop
from game.simulation import new_run
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))
MUSEUM_TAB = SHOP_TABS.index("Museum")


def _donate(state, gem):
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == gem)
    update_shop(CONFIRM, state)


def test_one_of_each_kind_can_be_donated():
    state = GameState(active_scene="shop", shop_tab=MUSEUM_TAB)
    state.inventory["gems"] = {"garnet": 2, "opal_polished": 1, GEODE: 1}
    keys = {it["key"] for it in _build_shop_items(state) if it["action"] == "donate"}
    assert keys == {"garnet"}  # no polished gems or geodes
    _donate(state, "garnet")
    assert state.museum == ["garnet"] and state.inventory["gems"]["garnet"] == 1
    assert not [it for it in _build_shop_items(state) if it["action"] == "donate"]


def test_every_milestone_raises_all_sale_prices():
    state = GameState()
    state.museum = list(GEM_CATALOG)[: MUSEUM_MILESTONE - 1]
    assert museum_bonus(state) == 1.0
    state.museum = list(GEM_CATALOG)[:MUSEUM_MILESTONE]
    assert museum_bonus(state) == 1.0 + MUSEUM_BONUS
    state.inventory["gems"] = {"ruby": 1}
    assert sell_one(state, "ruby") == int(get_gem_raw_value("ruby") * (1 + MUSEUM_BONUS))


def test_museum_tab_shows_progress_and_bonus():
    state = GameState(active_scene="shop", shop_tab=MUSEUM_TAB)
    state.museum = list(GEM_CATALOG)[: 2 * MUSEUM_MILESTONE]
    renderer = StubRenderer(80, 24)
    render_shop(renderer, state)
    screen = "\n".join("".join(renderer.get_cell(x, y)[0] for x in range(80)) for y in range(24))
    assert f"Donated {2 * MUSEUM_MILESTONE}/{len(GEM_CATALOG)}" in screen
    assert f"+{round(2 * MUSEUM_BONUS * 100)}%" in screen
    assert "[ Museum ]" in screen


def test_museum_is_saved():
    state = new_run(3)
    state.museum = ["ruby", "opal"]
    save_game(state)
    assert load_game().museum == ["ruby", "opal"]
