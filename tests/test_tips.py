from game import profile
from game.enemies import Enemy
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.player import set_hud_message
from game.scenes.game import GameScene
from game.simulation import new_run
from game.tips import TIP_GAP, TIP_SECONDS, check_tips
from tests.test_gameplay import make_state


def test_a_tip_is_shown_once_when_it_applies():
    state = make_state({(5, 5): "mineable_grass"})
    check_tips(state)
    assert state.hud_message.startswith("Tip:") and "digs" in state.hud_message
    assert state.hud_message_timer == TIP_SECONDS and state.tips_seen == {"dig"}
    state.hud_message, state.game_time = "", TIP_GAP + 1
    check_tips(state)
    assert state.hud_message == ""  # never repeated


def test_tips_wait_for_the_message_row_and_for_each_other():
    state = make_state({(5, 5): "mineable_grass"})
    set_hud_message(state, "Found a Quartz!", 2.0)
    check_tips(state)
    assert state.tips_seen == set()  # a message is showing
    state.hud_message = ""
    check_tips(state)
    state.enemies = [Enemy(7, 5, "snake")]
    state.hud_message, state.game_time = "", state.last_tip_time + 1
    check_tips(state)
    assert state.tips_seen == {"dig"}  # too soon after the last tip
    state.game_time += TIP_GAP
    check_tips(state)
    assert "enemy" in state.tips_seen and "Attack" in state.hud_message


def test_urgent_tips_come_first():
    state = make_state({(5, 5): "mineable_grass"})
    state.enemies = [Enemy(6, 5, "snake")]
    check_tips(state)
    assert state.tips_seen == {"enemy"}


def test_seen_tips_are_kept_in_the_profile_across_runs():
    scene, state = GameScene(), new_run(3)
    scene.enter(state)
    for _ in range(int(3 / STEP)):
        scene.update(EMPTY_INPUT, state, STEP)
    assert "start" in state.tips_seen
    assert "start" in profile.load_profile()["tips"]

    later = new_run(4)
    GameScene().enter(later)
    assert "start" in later.tips_seen
