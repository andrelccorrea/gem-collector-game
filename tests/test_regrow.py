from game import regrow
from game.input import Action
from game.persistence import load_game, save_game
from game.simulation import new_run
from game.tools import use_tool
from tests.test_gameplay import make_state, press


def test_worked_ground_comes_back_a_day_later_in_order():
    state = make_state({(5, 5): "mineable_grass", (6, 5): "mineable_grass"})
    use_tool(press(Action.USE), state)
    state.game_time = 10.0
    state.player_x = 6
    use_tool(press(Action.USE), state)
    assert list(state.depleted_at) == [(5, 5), (6, 5)]
    state.game_time = regrow.REGROW_SECONDS + 5
    regrow.update_regrowth(state)
    assert (5, 5) not in state.depleted_tiles and (6, 5) in state.depleted_tiles
    tile = state.world_tiles.meta[(5, 5)]
    assert not tile["depleted"] and tile["interactable"]
    state.game_time += 10
    regrow.update_regrowth(state)
    assert state.depleted_at == {} and state.depleted_tiles == set()


def test_the_clock_and_regrowth_survive_a_load():
    state = new_run(3)
    state.game_time = 500.0
    state.depleted_tiles = {(10, 10)}
    state.depleted_at = {(10, 10): 450.0}
    assert save_game(state) is None
    loaded = load_game()
    assert loaded.game_time == 500.0 and loaded.depleted_at == {(10, 10): 450.0}


def test_the_bot_no_longer_stalls_when_the_ground_runs_out():
    from game.bot import simulate_run

    report = simulate_run(1, max_minutes=40)
    assert report.minutes_to_win is not None  # seed 1 used to stall at $9,417
