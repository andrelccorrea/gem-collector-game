import pathlib
import re

import pytest

from game import camera
from game.constants import MAP_HEIGHT, MAP_WIDTH, VIEW_HEIGHT, VIEW_WIDTH
from game.gems import add_polished_gem
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
    for name in GEM_CATALOG:
        add_polished_gem(state, name, 100)
    items = _build_shop_items(state)
    assert len(items) > 13, "the list must be longer than one page for this test"

    for _ in range(len(items) - 1):
        update_shop(DOWN, state)
    assert items[state.shop_cursor]["action"] == "sell_all_gems"

    render_shop(stub_renderer, state)
    assert "Sell All Gems" in _screen_text(stub_renderer)


# ── Screen-size layout ────────────────────────────────────────────────────────


def test_game_view_fits_any_screen_size():
    from clingine.renderer import StubRenderer
    from game.simulation import new_run

    state = new_run(3)
    scene = GameScene()
    for width, height in [(80, 24), (40, 60), (120, 30), (20, 10)]:
        renderer = StubRenderer(width, height)
        scene.render(renderer, state)
        view = camera.render_view(state, renderer)
        assert (view.width, view.height) == (min(width, VIEW_WIDTH), min(height - 2, VIEW_HEIGHT))
        px, py = state.player_x - view.x, state.player_y - view.y
        assert renderer.get_cell(px, py)[0] == "@"
        hud_row = "".join(renderer.get_cell(x, height - 2)[0] for x in range(width))
        assert "HP:" in hud_row


@pytest.mark.parametrize("screen", [(80, 24), (40, 60), (30, 12), (300, 100)])
def test_drawn_view_always_lies_inside_the_simulation_view(screen):
    # Enemies spawn outside the simulation view; the drawn view must be inside it so a
    # spawn is never visible, whatever the screen size or player position.
    from clingine.renderer import StubRenderer

    renderer = StubRenderer(*screen)
    state = GameState()
    for px in range(0, MAP_WIDTH, 7):
        for py in range(0, MAP_HEIGHT, 3):
            state.player_x, state.player_y = px, py
            camera.update_camera(state)
            view = camera.render_view(state, renderer)
            assert state.camera_x <= view.x
            assert view.x + view.width <= state.camera_x + VIEW_WIDTH
            assert state.camera_y <= view.y
            assert view.y + view.height <= state.camera_y + VIEW_HEIGHT
            assert 0 <= view.x and view.x + view.width <= MAP_WIDTH
            assert 0 <= view.y and view.y + view.height <= MAP_HEIGHT


def test_camera_clamps_at_map_edges():
    state = GameState()
    state.player_x, state.player_y = MAP_WIDTH - 1, MAP_HEIGHT - 1
    camera.update_camera(state)
    assert (state.camera_x, state.camera_y) == (MAP_WIDTH - VIEW_WIDTH, MAP_HEIGHT - VIEW_HEIGHT)
    state.player_x, state.player_y = 0, 0
    camera.update_camera(state)
    assert (state.camera_x, state.camera_y) == (0, 0)


def test_enemies_spawn_outside_the_simulation_view():
    from game import enemies
    from game.simulation import new_run

    state = new_run(8)
    camera.update_camera(state)
    for _ in range(300):
        enemies.spawn_enemies(state, STEP * 10)
    assert state.enemies
    for e in state.enemies:
        inside_x = state.camera_x <= e.x < state.camera_x + VIEW_WIDTH
        inside_y = state.camera_y <= e.y < state.camera_y + VIEW_HEIGHT
        assert not (inside_x and inside_y), (e.x, e.y)
