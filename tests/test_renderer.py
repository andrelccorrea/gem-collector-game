from clingine.renderer import CursesRenderer, Renderer, StubRenderer


def test_stub_renderer_set_get_cell():
    renderer = StubRenderer(80, 24)
    renderer.set_cell(5, 3, "X", ((255, 0, 0), (0, 0, 0)))
    assert renderer.get_cell(5, 3) == ("X", ((255, 0, 0), (0, 0, 0)))


def test_stub_renderer_default_cell():
    renderer = StubRenderer(80, 24)
    assert renderer.get_cell(0, 0) == (" ", None)


def test_stub_renderer_boundary_guard_x():
    # The last column (x == width-1 = 79) must be a no-op, matching CursesRenderer behaviour.
    renderer = StubRenderer(80, 24)
    renderer.set_cell(79, 0, "X", None)
    assert renderer.get_cell(79, 0) == (" ", None)


def test_stub_renderer_boundary_guard_y():
    # The last row (y == height-1 = 23) must be a no-op, matching CursesRenderer behaviour.
    renderer = StubRenderer(80, 24)
    renderer.set_cell(0, 23, "X", None)
    assert renderer.get_cell(0, 23) == (" ", None)


def test_stub_renderer_out_of_bounds():
    renderer = StubRenderer(80, 24)
    # Must not raise; entirely out-of-bounds coordinates are silently ignored.
    renderer.set_cell(100, 100, "X", None)


def test_stub_renderer_clear():
    renderer = StubRenderer(80, 24)
    renderer.set_cell(5, 5, "X", ((1, 2, 3), (0, 0, 0)))
    renderer.clear()
    assert renderer.get_cell(5, 5) == (" ", None)


def test_stub_renderer_clear_with_color():
    renderer = StubRenderer(80, 24)
    color = ((255, 255, 255), (0, 0, 0))
    renderer.clear(color)
    assert renderer.get_cell(0, 0) == (" ", color)


def test_stub_renderer_width_height():
    renderer = StubRenderer(80, 24)
    assert renderer.width == 80
    assert renderer.height == 24


def test_stub_renderer_is_renderer():
    assert isinstance(StubRenderer(80, 24), Renderer)


def test_curses_renderer_is_renderer():
    assert issubclass(CursesRenderer, Renderer)
