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
