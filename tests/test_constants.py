from game.constants import FOG_RADIUS


def test_fog_radius_exists():
    assert FOG_RADIUS == 8


def test_fog_radius_is_int():
    assert isinstance(FOG_RADIUS, int)
