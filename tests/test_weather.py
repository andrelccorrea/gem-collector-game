from clingine.renderer import StubRenderer
from game import camera, daylight, weather
from game.hud import render_hud
from game.scenes.game import GameScene
from game.simulation import new_run


def _rainy(state, raining=True):
    for stretch in range(500):
        state.game_time = stretch * weather.SHOWER_SECONDS + 1
        if weather.is_raining(state) == raining:
            return state
    raise AssertionError("no such weather in 500 stretches")


def test_showers_come_and_go_at_about_the_set_share():
    state = new_run(5)
    rainy = 0
    for stretch in range(400):
        state.game_time = stretch * weather.SHOWER_SECONDS
        rainy += weather.is_raining(state)
    assert 0.2 < rainy / 400 < 0.4


def test_rain_greys_the_light_but_caves_stay_dry():
    state = _rainy(new_run(5))
    state.game_time %= daylight.DAY_SECONDS * 100  # any time works; keep the shower
    _rainy(state)
    name, tint = daylight.phase(state)
    expected = daylight.mix(dict((n, t) for _, n, t in daylight.PHASES)[name], weather.OVERCAST)
    assert tint == expected
    state.player_x = 170  # caves
    assert not weather.rain_here(state)


def test_terminal_drops_fall_and_the_hud_says_rain():
    state = _rainy(new_run(5))
    state.enemies = []
    renderer = StubRenderer(80, 24)
    GameScene().render(renderer, state)
    view = camera.render_view(state, renderer)
    drops = {(x, y) for y in range(view.height) for x in range(view.width)
             if renderer.get_cell(x, y)[0] == "'"}  # fmt: skip
    assert 0 < len(drops) < view.width * view.height * 0.1
    state.game_time += 0.5
    GameScene().render(renderer, state)
    later = {(x, y) for y in range(view.height) for x in range(view.width)
             if renderer.get_cell(x, y)[0] == "'"}  # fmt: skip
    assert later != drops
    hud = StubRenderer(79, 23)
    render_hud(hud, state)
    assert "rain" in "".join(hud.get_cell(x, 20)[0] for x in range(79)).lower()
