from clingine.renderer import StubRenderer
from game import goals, profile
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.scenes.game import GameScene
from game.scenes.world_map import render_map
from game.simulation import new_run


def test_goals_complete_one_at_a_time_and_pay_a_little():
    state = new_run(3)
    gold = state.player_gold
    assert goals.current(state) == goals.GOALS[0][0]
    state.lifetime_earnings = 50  # would meet goal 2, but goal 1 comes first
    assert not goals.check(state)
    state.stats["gems_found"] = 1
    assert goals.check(state) and state.goal == 1
    assert state.player_gold == gold + goals.GOALS[0][1]
    assert "Next: Sell a gem" in state.hud_message
    assert goals.check(state) and state.goal == 2  # selling is already done


def test_the_chain_is_kept_in_the_profile_and_announced():
    scene, state = GameScene(), new_run(3)
    scene.enter(state)
    assert state.hud_message == f"Goal: {goals.GOALS[0][0]}"
    state.stats["gems_found"] = 1
    scene.update(EMPTY_INPUT, state, STEP)
    assert profile.load_profile()["goal"] == 1
    later = new_run(4)
    GameScene().enter(later)
    assert later.goal == 1 and goals.current(later) == goals.GOALS[1][0]
    renderer = StubRenderer(79, 23)
    render_map(renderer, later)
    assert "Goal: Sell a gem" in "".join(renderer.get_cell(x, 0)[0] for x in range(79))


def test_the_chain_ends():
    state = new_run(3)
    state.goal = len(goals.GOALS)
    assert goals.current(state) is None and not goals.check(state)
