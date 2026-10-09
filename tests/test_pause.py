from game.input import Action
from game.loop import STEP
from game.menu import _menu_ids, _select_menu_item, update_menu
from game.persistence import autosave_allowed
from game.scenes.pause import PAUSE_ITEMS, update_pause
from game.simulation import new_run, step_game
from tests.test_gameplay import press


def _paused():
    state = new_run(4)
    step_game(press(Action.CANCEL), state, STEP)
    return state


def test_back_pauses_instead_of_leaving_the_run():
    state = _paused()
    assert state.active_scene == "pause" and autosave_allowed(state)
    update_pause(press(Action.CANCEL), state)
    assert state.active_scene == "game"


def test_the_main_menu_keeps_the_run_open_and_resumes_it():
    state = _paused()
    state.player_gold, state.pause_cursor = 777, [k for k, _ in PAUSE_ITEMS].index("menu")
    update_pause(press(Action.CONFIRM), state)
    assert state.active_scene == "menu" and state.run_open
    update_menu(press(Action.CONFIRM), state)  # the cursor sits on Resume Run
    assert state.active_scene == "game" and state.player_gold == 777


def test_abandoning_an_open_run_needs_a_second_choice():
    state = _paused()
    state.run_open, state.active_scene, state.player_gold = True, "menu", 777
    state.menu_cursor = _menu_ids().index("new")
    _select_menu_item(state, save_exists=False)
    assert state.player_gold == 777 and "abandons" in state.menu_notice
    _select_menu_item(state, save_exists=False)
    assert state.active_scene == "game" and not state.run_open and state.player_gold != 777


def test_without_an_open_run_resume_is_skipped():
    state = new_run(4)
    state.active_scene, state.menu_cursor = "menu", 0
    update_menu(press(Action.MOVE_DOWN), state)
    assert _menu_ids()[state.menu_cursor] != "resume"
