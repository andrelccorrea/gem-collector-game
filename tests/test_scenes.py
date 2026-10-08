import pathlib
import re

from game.input import EMPTY_INPUT, Action, InputState
from game.loop import STEP
from game.objects.registry import GEM_CATALOG
from game.scenes import FunctionScene, Scene, SceneManager, build_scenes
from game.scenes.game import GameScene
from game.scenes.shop import _build_shop_items, render_shop, update_shop
from game.state import GameState
from game.ui import list_page

DOWN = InputState(pressed=frozenset({Action.MOVE_DOWN}))


def _screen_text(renderer):
    return "\n".join(
        "".join(renderer.get_cell(x, y)[0] for x in range(renderer.width))
        for y in range(renderer.height)
    )


class Recorder(Scene):
    def __init__(self, switch_to=None):
        self.calls = []
        self.switch_to = switch_to

    def enter(self, state):
        self.calls.append("enter")

    def update(self, inp, state, frame_dt):
        self.calls.append("update")
        if self.switch_to:
            state.active_scene = self.switch_to

    def render(self, renderer, state):
        self.calls.append("render")


# ── SceneManager ──────────────────────────────────────────────────────────────


def test_manager_enters_once_then_updates_and_renders(stub_renderer):
    a = Recorder()
    manager = SceneManager({"a": a})
    state = GameState(active_scene="a")
    manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    assert a.calls == ["enter", "update", "render", "update", "render"]


def test_manager_skips_render_when_scene_switches_and_enters_the_new_one(stub_renderer):
    a, b = Recorder(switch_to="b"), Recorder()
    manager = SceneManager({"a": a, "b": b})
    state = GameState(active_scene="a")
    manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    assert a.calls == ["enter", "update"]
    assert b.calls == ["enter", "update", "render"]


def test_function_scene_delegates(stub_renderer):
    seen = []
    scene = FunctionScene(lambda inp, s: seen.append("u"), lambda r, s: seen.append("r"))
    scene.update(EMPTY_INPUT, GameState(), STEP)
    scene.render(stub_renderer, GameState())
    assert seen == ["u", "r"]


def test_every_scene_name_used_in_code_is_registered():
    names = set()
    game_dir = pathlib.Path(__file__).resolve().parents[1] / "game"
    for path in game_dir.rglob("*.py"):
        names |= set(re.findall(r'active_scene = "([a-z_]+)"', path.read_text()))
    assert names, "expected scene assignments in game/"
    assert names <= set(build_scenes())


def test_returning_to_the_game_does_not_simulate_time_spent_elsewhere(stub_renderer):
    from game.simulation import new_run

    state = new_run(2)
    shop = Recorder()
    manager = SceneManager({"game": GameScene(), "shop": shop})
    for _ in range(5):  # play a few frames so the start-up discard is used up
        manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    played = state.game_time
    assert played > 0

    state.active_scene = "shop"
    manager.frame(EMPTY_INPUT, state, STEP, stub_renderer)
    state.active_scene = "game"
    manager.frame(EMPTY_INPUT, state, 30.0, stub_renderer)  # frame spanning the shop visit
    assert state.game_time == played


# ── Paged lists ───────────────────────────────────────────────────────────────


def test_list_page_contains_cursor():
    assert list(list_page(0, 30, 13)) == list(range(0, 13))
    assert list(list_page(13, 30, 13)) == list(range(13, 26))
    assert list(list_page(29, 30, 13)) == list(range(26, 30))


def test_sell_all_is_reachable_and_drawn_with_many_gem_types(stub_renderer):
    state = GameState(active_scene="shop")
    state.shop_tab = 2  # Sell Gems
    state.inventory["gems"] = {name: 1 for name in GEM_CATALOG}
    state.inventory["gems"].update({f"{name}_polished": 1 for name in GEM_CATALOG})
    items = _build_shop_items(state)
    assert len(items) > 13, "the list must be longer than one page for this test"

    for _ in range(len(items) - 1):
        update_shop(DOWN, state)
    assert items[state.shop_cursor]["action"] == "sell_all_gems"

    render_shop(stub_renderer, state)
    assert "Sell All Gems" in _screen_text(stub_renderer)
