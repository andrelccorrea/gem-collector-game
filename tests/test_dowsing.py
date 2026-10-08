from game import dowsing
from game.persistence import load_game, save_game
from game.simulation import new_run
from game.tile_info import describe_here
from tests.test_gameplay import make_state


def _rod_state(level=1):
    state = make_state(x=5, y=5, dowsing_level=level)
    state.world_gems = {}
    return state


def test_no_rod_no_hint():
    state = _rod_state(level=0)
    state.world_gems = {(6, 5): "quartz"}
    assert dowsing.hint(state) == ""


def test_hint_gives_warmth_direction_and_distance():
    state = _rod_state()
    state.world_gems = {(9, 1): "quartz", (7, 7): "ruby"}
    assert dowsing.hint(state) == "Rod: hot SE (2)"
    state.world_gems = {(5, 0): "quartz"}
    assert dowsing.hint(state) == "Rod: warm N (5)"
    state.world_gems = {(11, 5): "quartz"}
    assert dowsing.hint(state) == "Rod: cold E (6)"
    state.world_gems = {(12, 5): "quartz"}  # out of reach at level 1
    assert dowsing.hint(state) == ""


def test_the_rod_pings_only_when_the_trail_gets_warmer():
    state = _rod_state()
    state.world_gems = {(11, 5): "quartz"}
    dowsing.update_dowsing(state)
    assert [e.kind for e in state.events] == ["detect"]
    dowsing.update_dowsing(state)
    assert len(state.events) == 1  # same tier: quiet
    state.player_x = 9  # 2 away: hot
    dowsing.update_dowsing(state)
    assert len(state.events) == 2


def test_the_hint_is_in_the_tile_row_and_the_rod_is_saved():
    state = _rod_state()
    state.world_gems = {(7, 5): "quartz"}
    assert "Rod: hot E (2)" in describe_here(state)
    run = new_run(2)
    run.dowsing_level = 2
    assert save_game(run) is None
    assert load_game().dowsing_level == 2
