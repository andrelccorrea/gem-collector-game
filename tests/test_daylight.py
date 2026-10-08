import pytest

from clingine.renderer import StubRenderer
from game import camera, daylight
from game.hud import render_hud
from game.scenes.game import GameScene
from game.simulation import new_run


def _at(share):
    state = new_run(2)
    state.enemies = []
    state.game_time = share * daylight.DAY_SECONDS
    return state


@pytest.mark.parametrize(
    "share,name", [(0.0, "day"), (0.6, "dusk"), (0.8, "night"), (0.95, "dawn"), (1.2, "day")]
)
def test_the_day_cycles_through_its_phases(share, name):
    assert daylight.phase(_at(share))[0] == name


def _cells(state):
    renderer = StubRenderer(80, 24)
    GameScene().render(renderer, state)
    return renderer, camera.render_view(state, renderer)


def test_night_darkens_the_world_but_the_lantern_keeps_a_glow():
    day, night = _at(0.0), _at(0.8)
    day_r, view = _cells(day)
    night_r, _ = _cells(night)
    px, py = day.player_x - view.x, day.player_y - view.y
    far = (px + 6, py)  # lit by the lantern, outside its glow
    near = (px + 1, py)
    day_far, night_far = day_r.get_cell(*far)[1], night_r.get_cell(*far)[1]
    assert sum(night_far[1]) < sum(day_far[1]) or sum(night_far[0]) < sum(day_far[0])
    glow = daylight.shade(day_r.get_cell(*near)[1], daylight.LANTERN_GLOW)
    assert night_r.get_cell(*near)[1] == glow


def test_the_glow_fades_in_rings():
    state = _at(0.8)
    now = daylight.phase(state)
    x, y = state.player_x, state.player_y
    rings = [daylight.tint_at(state, now, x + dx, y) for dx in (0, 4, 10)]
    assert rings == [daylight.GLOW_RINGS[0][2], daylight.GLOW_RINGS[1][2], now[1]]


def test_mix_and_shade():
    assert daylight.mix(None, (10, 20, 30)) == (10, 20, 30)
    assert daylight.mix((255, 255, 255), (10, 20, 30)) == (10, 20, 30)
    assert daylight.shade(None, (1, 2, 3)) is None
    assert daylight.shade(((200, 100, 0), (0, 0, 0)), None) == ((200, 100, 0), (0, 0, 0))


def test_hud_names_the_time_of_day_except_by_day():
    renderer = StubRenderer(79, 23)
    render_hud(renderer, _at(0.8))
    assert "Night" in "".join(renderer.get_cell(x, 20)[0] for x in range(79))
    render_hud(renderer, _at(0.1))
    assert "Day" not in "".join(renderer.get_cell(x, 20)[0] for x in range(79))
