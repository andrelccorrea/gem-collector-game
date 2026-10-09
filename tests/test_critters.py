from game import critters, daylight
from game.critters import Critter, update_critters
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.objects.registry import CRITTERS
from game.simulation import new_run, step_game
from tests.test_gameplay import make_state


def _meadow_state():
    state = make_state(x=10, y=10)
    state.seed = 1
    return state


def test_animals_spawn_out_of_sight_in_their_biome_and_time():
    state = new_run(12)
    state.player_x, state.player_y = 25, 30  # meadow, by day
    for _ in range(int(20 / STEP)):
        update_critters(state, STEP)
    assert state.critters
    for c in state.critters:
        kind = CRITTERS[c.name]
        assert kind["active"] in ("day", "any")
        assert critters._can_stand(state, c.x, c.y, kind["habitat"])


def test_night_brings_fireflies_and_no_day_animals():
    state = new_run(12)
    state.player_x, state.player_y = 25, 30
    state.game_time = 0.8 * daylight.DAY_SECONDS
    for _ in range(int(30 / STEP)):
        update_critters(state, STEP)
    names = {c.name for c in state.critters}
    assert "firefly" in names and not names & {"rabbit", "bird"}


def test_a_scared_herd_runs_away_faster_than_the_player_walks():
    state = new_run(12)
    state.enemies = []
    state.player_x, state.player_y = 25, 30  # open meadow
    spots = [
        (x, y)
        for x in range(27, 31)
        for y in range(29, 32)
        if critters._can_stand(state, x, y, "land")
    ]
    herd = [Critter("deer", *spots[0]), Critter("deer", *spots[-1])]
    state.critters = list(herd)
    start = [max(abs(c.x - 25), abs(c.y - 30)) for c in herd]
    for _ in range(int(1.0 / STEP)):
        update_critters(state, STEP)
    assert all(c.scared > 0 for c in herd)  # mates bolt together
    end = [max(abs(c.x - 25), abs(c.y - 30)) for c in herd]
    # The player covers about 6 tiles a second; scared deer get further than that.
    assert all(e - s >= 6 for s, e in zip(start, end, strict=True))


def test_animals_never_change_gameplay_rolls():
    a, b = new_run(7), new_run(7)
    b.critters = [Critter("deer", 1, 1)]  # even if they exist from the start
    for _ in range(300):
        step_game(EMPTY_INPUT, a, STEP)
        step_game(EMPTY_INPUT, b, STEP)
    assert a.rng.getstate() == b.rng.getstate()
    assert [(e.x, e.y) for e in a.enemies] == [(e.x, e.y) for e in b.enemies]


def test_far_animals_despawn():
    state = _meadow_state()
    state.critters = [Critter("rabbit", 19, 19)]
    state.player_x = state.player_y = 0
    critters.DESPAWN_DISTANCE, old = 5, critters.DESPAWN_DISTANCE
    try:
        update_critters(state, STEP)
    finally:
        critters.DESPAWN_DISTANCE = old
    assert state.critters == []


def test_rain_keeps_some_animals_in_and_brings_others_out():
    from game import weather

    state = new_run(12)
    for stretch in range(500):
        state.game_time = stretch * weather.SHOWER_SECONDS + 1
        if weather.is_raining(state) and daylight.phase(state)[0] == "day":
            break
    rng = critters.random.Random(3)
    meadow = [critters._species_for(state, 25, 30, rng) for _ in range(300)]
    river = [critters._species_for(state, 80, 60, rng) for _ in range(300)]
    assert "butterfly" not in meadow and "bird" not in meadow
    assert river.count("frog") + river.count("duck") > river.count("crab")


def test_rare_animals_are_rarer():
    from game import weather

    state = new_run(12)
    for stretch in range(500):
        state.game_time = stretch * weather.SHOWER_SECONDS + 1
        if not weather.is_raining(state) and daylight.phase(state)[0] == "day":
            break
    rng = critters.random.Random(4)
    picks = [critters._species_for(state, 25, 30, rng) for _ in range(2000)]
    assert 0 < picks.count("fox") < picks.count("deer")


def test_a_scared_hedgehog_curls_up_instead_of_running():
    state = new_run(12)
    state.enemies = []
    state.player_x, state.player_y = 25, 30
    spot = next((x, 30) for x in range(26, 30) if critters._can_stand(state, x, 30, "land"))
    hog = Critter("hedgehog", *spot)
    state.critters = [hog]
    for _ in range(int(1.0 / STEP)):
        update_critters(state, STEP)
    assert hog.scared > 0 and (hog.x, hog.y) == spot
