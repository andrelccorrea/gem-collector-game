import curses

import pytest

from clingine.colors import ColorPairs, terminal_palette
from clingine.renderer import CursesRenderer
from clingine.window import Window
from game.scenes.game import GameScene
from game.simulation import new_run


class FakeCurses:
    def __init__(self):
        self.pairs = {}

    def init_pair(self, number, fg, bg):
        self.pairs[number] = (fg, bg)

    def color_pair(self, number):
        return number << 8


def _pairs(n_colors=256, n_pairs=256):
    fake = FakeCurses()
    return ColorPairs(n_colors, n_pairs, fake.init_pair, fake.color_pair), fake


# ── Palette mapping ───────────────────────────────────────────────────────────


def test_256_color_palette_uses_only_theme_independent_colors():
    palette = terminal_palette(256)
    assert set(palette) == set(range(16, 256))
    assert palette[16] == (0, 0, 0) and palette[231] == (255, 255, 255)


@pytest.mark.parametrize("rgb,index", [((255, 0, 0), 196), ((0, 0, 0), 16), ((95, 135, 175), 67)])
def test_exact_cube_colors_map_to_their_index(rgb, index):
    pairs, _ = _pairs()
    assert pairs.nearest(rgb) == index


def test_grays_map_to_the_gray_ramp():
    pairs, _ = _pairs()
    assert pairs.nearest((128, 128, 128)) == 244  # 8 + 10 * 12 = 128


def test_eight_color_terminal_maps_to_ansi():
    pairs, _ = _pairs(n_colors=8)
    assert pairs.nearest((230, 20, 10)) == 1  # red
    assert pairs.nearest((10, 10, 10)) == 0  # black


def test_pairs_are_cached_and_allocated_once_per_terminal_pair():
    pairs, fake = _pairs()
    a = pairs.get_color_pair(((255, 0, 0), (0, 0, 0)))
    b = pairs.get_color_pair(((255, 0, 0), (0, 0, 0)))
    c = pairs.get_color_pair(((254, 1, 1), (1, 1, 1)))  # same nearest colors
    assert a == b == c
    assert len(fake.pairs) == 1


def test_running_out_of_pairs_falls_back_to_default_pair():
    pairs, fake = _pairs(n_pairs=3)
    attrs = [pairs.get_color_pair(((i * 40, 0, 0), (0, 0, 0))) for i in range(6)]
    assert len(fake.pairs) == 2
    assert attrs[-1] == 0


def test_colors_module_never_redefines_terminal_colors():
    import inspect

    import clingine.colors as colors_module
    import clingine.window as window_module

    for module in (colors_module, window_module):
        assert "init_color" not in inspect.getsource(module)


# ── Window flush ──────────────────────────────────────────────────────────────


class FakeScreen:
    def __init__(self):
        self.drawn = []
        self.size = (24, 80)
        self.fail_at = None

    def getmaxyx(self):
        return self.size

    def addstr(self, y, x, char, attr):
        if (x, y) == self.fail_at:
            raise curses.error
        self.drawn.append((x, y, char))

    def resize(self, height, width):
        pass

    def refresh(self):
        pass


def _window(width=80, height=24):
    window = Window.__new__(Window)  # skip the terminal resize in __init__
    window.width, window.height, window.char = width, height, " "
    window.color_pair = ((255, 255, 255), (0, 0, 0))
    fake = FakeCurses()
    window.color_pairs = ColorPairs(256, 256, fake.init_pair, fake.color_pair)
    window.screen = FakeScreen()
    window.reset()
    return window


def test_first_flush_draws_every_usable_cell_then_nothing():
    window = _window()
    window.update()
    assert len(window.screen.drawn) == 79 * 23
    window.screen.drawn.clear()
    window.update()
    assert window.screen.drawn == []


def test_idle_game_frame_redraws_nothing():
    window, state, scene = _window(), new_run(5), GameScene()
    renderer = CursesRenderer(window)
    scene.render(renderer, state)
    window.update()
    window.screen.drawn.clear()

    scene.render(renderer, state)
    window.update()
    assert window.screen.drawn == []


def test_clear_then_identical_redraw_reaches_the_terminal_as_no_change():
    from game.menu import render_menu
    from game.state import GameState

    window = _window()
    renderer = CursesRenderer(window)
    render_menu(renderer, GameState())  # clears the screen, then writes the menu
    window.update()
    window.screen.drawn.clear()

    render_menu(renderer, GameState())
    window.update()
    assert window.screen.drawn == []


def test_only_changed_cells_are_drawn():
    window = _window()
    window.update()
    window.screen.drawn.clear()
    renderer = CursesRenderer(window)
    renderer.set_cell(3, 4, "@", ((255, 255, 255), (0, 0, 0)))
    window.update()
    assert window.screen.drawn == [(3, 4, "@")]


def test_cells_without_color_use_the_window_default():
    window = _window()
    renderer = CursesRenderer(window)
    renderer.set_cell(1, 1, "x", None)
    window.update()
    assert window.screen_array[1][1][2] is None  # the cell itself is not rewritten
    assert window._drawn[1][1] == ("x", window.color_pair)


def test_terminal_resize_redraws_everything():
    window = _window()
    window.update()
    window.screen.drawn.clear()
    window.screen.size = (20, 60)  # shrinking wipes what the terminal showed
    window.update()
    window.screen.size = (24, 80)
    window.screen.drawn.clear()
    window.update()
    assert len(window.screen.drawn) == 79 * 23


def test_a_cell_that_failed_to_draw_is_retried():
    window = _window()
    window.screen.fail_at = (5, 5)
    window.update()
    assert (5, 5, " ") not in window.screen.drawn
    window.screen.fail_at = None
    window.screen.drawn.clear()
    window.update()
    assert window.screen.drawn == [(5, 5, " ")]


def test_pair_numbers_stay_within_what_an_attribute_can_hold():
    pairs, fake = _pairs(n_pairs=32767)
    for i in range(300):
        pairs.get_color_pair(((i % 256, i // 256 * 40, 0), (0, 0, 0)))
    assert max(fake.pairs) <= 255


def test_direct_color_terminal_uses_basic_ansi_colors():
    assert set(terminal_palette(16_777_216)) == set(range(8))
