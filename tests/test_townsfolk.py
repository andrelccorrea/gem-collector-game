from game import daylight, townsfolk
from game.constants import TYPE_TOWN
from game.geography import in_town
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.simulation import new_run, step_game


def _town(seed=4):
    state = new_run(seed)
    state.enemies, state.game_time = [], 10.0
    townsfolk.update_townsfolk(state, STEP)
    return state


def test_villagers_wander_the_town_square_by_day():
    state = _town()
    start = [(v["x"], v["y"]) for v in state.townsfolk]
    assert len(start) == len(townsfolk.VILLAGERS)
    for _ in range(int(30 / STEP)):
        townsfolk.update_townsfolk(state, STEP)
    for v in state.townsfolk:
        assert in_town(v["x"], v["y"])
        assert state.world_tiles.meta[(v["x"], v["y"])]["type"] == TYPE_TOWN
    assert [(v["x"], v["y"]) for v in state.townsfolk] != start


def test_they_go_home_at_night():
    state = _town()
    state.game_time = 0.8 * daylight.DAY_SECONDS
    townsfolk.update_townsfolk(state, STEP)
    assert all((v["x"], v["y"]) == v["home"] for v in state.townsfolk)


def test_a_villager_greets_with_a_hint_but_not_all_the_time():
    state = _town()
    v = state.townsfolk[0]
    state.player_x, state.player_y = v["x"] + 1, v["y"]
    v["timer"] = 99  # stand still
    townsfolk.update_townsfolk(state, STEP)
    name = townsfolk.VILLAGERS[v["id"]][0]
    assert state.hud_message.startswith(f"{name}:")
    first = state.hud_message
    state.hud_message = ""
    townsfolk.update_townsfolk(state, STEP)
    assert state.hud_message == ""  # cooldown
    v["greet"] = 0
    townsfolk.update_townsfolk(state, STEP)
    assert state.hud_message and state.hud_message != first  # the next line


def test_villagers_never_touch_gameplay_rolls(monkeypatch):
    with_folk = new_run(7)
    for _ in range(300):
        step_game(EMPTY_INPUT, with_folk, STEP)
    monkeypatch.setattr(townsfolk, "update_townsfolk", lambda state, dt: None)
    without = new_run(7)
    for _ in range(300):
        step_game(EMPTY_INPUT, without, STEP)
    assert with_folk.townsfolk and not without.townsfolk
    assert with_folk.rng.getstate() == without.rng.getstate()
