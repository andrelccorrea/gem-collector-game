from clingine.util import draw_endpoints, draw_line


def test_draw_line_writes_chars(stub_renderer):
    draw_line(stub_renderer, x1=0, x2=4, y=5, char="-", color_pair=None)
    for x in range(0, 5):
        assert stub_renderer.get_cell(x, 5)[0] == "-", f"Expected '-' at ({x}, 5)"


def test_draw_endpoints_writes_only_endpoints(stub_renderer):
    draw_endpoints(stub_renderer, x1=0, x2=9, y=3, char="+", color_pair=None)
    assert stub_renderer.get_cell(0, 3)[0] == "+"
    assert stub_renderer.get_cell(9, 3)[0] == "+"
    # Middle cells must remain at default space character
    for x in range(1, 9):
        assert stub_renderer.get_cell(x, 3)[0] == " ", f"Middle cell ({x}, 3) should be default"


def test_draw_line_respects_renderer_bounds(stub_renderer):
    # x2 exceeds renderer width — must not raise; draw_line clamps internally.
    draw_line(stub_renderer, x1=0, x2=200, y=5, char="*", color_pair=None)
    # Verify at least the first cell was written (within bounds)
    assert stub_renderer.get_cell(0, 5)[0] == "*"
