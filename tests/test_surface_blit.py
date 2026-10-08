from clingine.renderer import StubRenderer
from clingine.surface import Surface


def test_blit_writes_tile_to_renderer():
    surface = Surface(10, 10)
    color = ((0, 255, 0), (0, 0, 0))
    surface.set_tile(0, 0, "G", color)
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    assert stub.get_cell(0, 0) == ("G", color)


def test_blit_applies_camera_offset():
    surface = Surface(20, 20)
    color = ((128, 0, 255), (0, 0, 0))
    surface.set_tile(5, 5, "X", color)
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=5, cam_y=5, vp_width=10, vp_height=10, dest_y=0)
    # Tile at surface (5,5) with cam offset (5,5) maps to screen (0,0)
    assert stub.get_cell(0, 0) == ("X", color)


def test_blit_respects_dest_y():
    surface = Surface(10, 10)
    color = ((255, 0, 128), (0, 0, 0))
    surface.set_tile(0, 0, "D", color)
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=2)
    # Tile should appear at row 2, not row 0
    assert stub.get_cell(0, 2) == ("D", color)
    assert stub.get_cell(0, 0) == (" ", None)


def test_blit_skips_unchanged_cells():
    """Second blit of an unchanged surface must not touch already-matching cells."""

    class CountingRenderer(StubRenderer):
        def __init__(self, width, height):
            super().__init__(width, height)
            self.set_cell_calls = 0

        def set_cell(self, x, y, char, color_pair):
            self.set_cell_calls += 1
            super().set_cell(x, y, char, color_pair)

    surface = Surface(5, 5)
    surface.set_tile(0, 0, "A", ((10, 20, 30), (0, 0, 0)))
    stub = CountingRenderer(80, 24)

    surface.blit(stub, cam_x=0, cam_y=0, vp_width=5, vp_height=5, dest_y=0)
    calls_after_first = stub.set_cell_calls

    # Second blit — nothing changed, so set_cell count must not increase.
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=5, vp_height=5, dest_y=0)
    assert stub.set_cell_calls == calls_after_first


def test_blit_no_screen_array_access():
    """Blitting to StubRenderer must not raise AttributeError or import curses."""
    surface = Surface(5, 5)
    surface.set_tile(2, 2, "#", ((50, 100, 150), (0, 0, 0)))
    stub = StubRenderer(80, 24)
    # If surface.blit tried to access window.screen_array this would raise AttributeError.
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=5, vp_height=5, dest_y=0)
    assert stub.get_cell(2, 2) == ("#", ((50, 100, 150), (0, 0, 0)))


# ---------------------------------------------------------------------------
# Fog-of-war visibility rendering tests
# ---------------------------------------------------------------------------


def test_blit_unseen_tile_renders_blank():
    """A tile with visibility='unseen' must be rendered as a blank/black cell."""
    surface = Surface(10, 10)
    color = ((0, 255, 0), (0, 0, 0))
    surface.set_tile(0, 0, "G", color)
    surface.meta[(0, 0)] = {"visibility": "unseen"}
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    assert stub.get_cell(0, 0) == (" ", None)


def test_blit_explored_tile_renders_dimmed():
    """A tile with visibility='explored' must render with all RGB components halved."""
    surface = Surface(10, 10)
    orig_fg = (100, 200, 60)
    orig_bg = (10, 20, 30)
    surface.set_tile(0, 0, "G", (orig_fg, orig_bg))
    surface.meta[(0, 0)] = {"visibility": "explored"}
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    char, cp = stub.get_cell(0, 0)
    assert char == "G"
    expected_fg = (orig_fg[0] // 2, orig_fg[1] // 2, orig_fg[2] // 2)
    expected_bg = (orig_bg[0] // 2, orig_bg[1] // 2, orig_bg[2] // 2)
    assert cp == (expected_fg, expected_bg)


def test_blit_visible_tile_renders_normally():
    """A tile with visibility='visible' must render with its original char and color."""
    surface = Surface(10, 10)
    color = ((200, 150, 50), (10, 10, 10))
    surface.set_tile(1, 1, "V", color)
    surface.meta[(1, 1)] = {"visibility": "visible"}
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    assert stub.get_cell(1, 1) == ("V", color)


def test_blit_no_meta_defaults_to_visible():
    """A surface with no meta entries must render tiles normally (default = visible)."""
    surface = Surface(10, 10)
    color = ((255, 100, 0), (0, 0, 0))
    surface.set_tile(3, 3, "N", color)
    # meta is empty — no visibility key anywhere
    assert surface.meta == {}
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    assert stub.get_cell(3, 3) == ("N", color)


def test_blit_explored_tile_with_none_color_renders_char():
    """An explored tile with no color pair should still render the char unchanged."""
    surface = Surface(10, 10)
    surface.set_tile(2, 2, "E", None)
    surface.meta[(2, 2)] = {"visibility": "explored"}
    stub = StubRenderer(80, 24)
    surface.blit(stub, cam_x=0, cam_y=0, vp_width=10, vp_height=10, dest_y=0)
    char, cp = stub.get_cell(2, 2)
    assert char == "E"
    # No color to dim, so color_pair stays None
    assert cp is None
