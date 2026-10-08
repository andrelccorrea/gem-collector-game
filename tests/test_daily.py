from datetime import date

from game.daily import DAILY_TIME_LIMIT, daily_seed, start_daily, time_left
from game.hud import render_hud
from game.input import EMPTY_INPUT, Action, InputState
from game.loop import STEP
from game.menu import MENU_ITEMS, _select_menu_item, render_daily_end, update_daily_end
from game.persistence import has_save, load_daily, save_daily_entry
from game.scenes import build_scenes
from game.scenes.save_point import update_save_point
from game.simulation import step_game
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))
DAY = date(2026, 10, 8)


def _text(renderer, row):
    return "".join(renderer.get_cell(x, row)[0] for x in range(renderer.width))


def test_everyone_gets_the_same_world_on_the_same_day():
    assert daily_seed(DAY) == 20261008
    a, b = start_daily(DAY), start_daily(DAY)
    assert a.seed == b.seed and a.world_gems == b.world_gems
    assert start_daily(date(2026, 10, 9)).seed != a.seed
    assert a.daily == "2026-10-08"


def test_the_run_ends_when_time_is_up():
    state = start_daily(DAY)
    state.game_time = DAILY_TIME_LIMIT - STEP / 2
    step_game(EMPTY_INPUT, state, STEP)
    assert state.active_scene == "daily_end"
    assert time_left(state) == 0.0


def test_normal_runs_have_no_time_limit():
    from game.simulation import new_run

    state = new_run(1)
    state.game_time = DAILY_TIME_LIMIT * 3
    step_game(EMPTY_INPUT, state, STEP)
    assert state.active_scene == "game"


def test_daily_runs_cannot_be_saved():
    state = start_daily(DAY)
    state.active_scene = "save_point"
    update_save_point(CONFIRM, state)
    assert not has_save()
    assert "can't be saved" in state.hud_message


def test_end_screen_records_the_score_and_shows_the_rank(stub_renderer):
    save_daily_entry("2026-10-08", 900)
    save_daily_entry("2026-10-08", 300)
    state = GameState(daily="2026-10-08", lifetime_earnings=500, active_scene="daily_end")
    render_daily_end(stub_renderer, state)
    screen = "\n".join(_text(stub_renderer, y) for y in range(stub_renderer.height))
    assert "$500  <- you" in screen and "#2" in screen
    update_daily_end(CONFIRM, state)
    assert load_daily("2026-10-08") == [900, 500, 300]
    assert state.active_scene == "menu"


def test_daily_scores_are_kept_per_day():
    save_daily_entry("2026-10-07", 100)
    save_daily_entry("2026-10-08", 200)
    assert load_daily("2026-10-07") == [100]
    assert load_daily("2026-10-08") == [200]


def test_hud_shows_time_left_in_daily_runs(stub_renderer):
    state = GameState(daily="2026-10-08", game_time=DAILY_TIME_LIMIT - 75)
    render_hud(stub_renderer, state)
    assert "Time:1:15" in _text(stub_renderer, 22)


def test_daily_run_is_in_the_menu_and_its_end_screen_is_registered(monkeypatch):
    import game.daily

    monkeypatch.setattr(game.daily, "start_daily", lambda day: start_daily(DAY))
    state = GameState(menu_cursor=[i for i, _ in MENU_ITEMS].index("daily"))
    _select_menu_item(state, save_exists=False)
    assert state.daily == "2026-10-08" and state.active_scene == "game"
    assert "daily_end" in build_scenes()
