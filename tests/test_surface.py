from clingine.surface import Surface


def test_surface_has_meta_attribute():
    s = Surface(10, 10)
    assert s.meta == {}


def test_surface_meta_is_independent_per_instance():
    s1 = Surface(10, 10)
    s2 = Surface(10, 10)
    s1.meta[(0, 0)] = {"type": "grass"}
    assert s2.meta == {}


def test_surface_has_start_pos_attribute():
    s = Surface(10, 10)
    assert s.start_pos is None


def test_surface_start_pos_can_be_set():
    s = Surface(10, 10)
    s.start_pos = (5, 3)
    assert s.start_pos == (5, 3)
