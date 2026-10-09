from clingine.renderer import StubRenderer
from game import profile
from game.enemies import Enemy
from game.input import EMPTY_INPUT, Action
from game.loop import STEP
from game.menu import render_stats
from game.scenes.game import STATS_SYNC_SECONDS, GameScene
from game.simulation import new_run, step_game
from game.tools import use_tool
from tests.test_gameplay import make_state, press


def test_the_simulation_counts_what_happens():
    state = make_state({(5, 5): "mineable_grass"})
    state.world_gems = {}
    use_tool(press(Action.USE), state)
    assert state.stats["tiles_dug"] == 1
    state.world_gems = {(6, 5): "quartz"}
    state.world_tiles.meta[(6, 5)]["type"] = "mineable_grass"
    state.player_x = 6
    use_tool(press(Action.USE), state)
    assert state.stats["gems_found"] >= 1
    enemy = Enemy(7, 5, "snake")
    enemy.attack, enemy.attack_cooldown = 3, 0.0
    state.enemies = [enemy]
    from game.combat import enemy_attacks

    enemy_attacks(state, STEP)
    assert state.stats["damage_taken"] == 3


def test_totals_reach_the_profile_once_per_gain_and_across_runs():
    scene, state = GameScene(), new_run(4)
    scene.enter(state)
    state.stats = {"steps": 10}
    scene.update(EMPTY_INPUT, state, STATS_SYNC_SECONDS)  # long enough: syncs
    assert profile.load_profile()["stats"]["steps"] >= 10
    first = profile.load_profile()["stats"]["steps"]
    scene.sync_stats(state)
    assert profile.load_profile()["stats"]["steps"] == first  # nothing new, nothing added
    later = new_run(5)
    scene.enter(later)
    later.stats = {"steps": 3}
    scene.sync_stats(later)
    assert profile.load_profile()["stats"]["steps"] == first + 3


def test_walking_is_counted_and_the_screen_shows_totals():
    state = new_run(4)
    for _ in range(10):
        step_game(press(Action.MOVE_RIGHT), state, STEP * 5)
    assert state.stats.get("steps", 0) > 0
    profile.add_stats({"gems_found": 1234})
    renderer = StubRenderer(79, 23)
    render_stats(renderer, state)
    text = "\n".join("".join(renderer.get_cell(x, y)[0] for x in range(79)) for y in range(23))
    assert "Gems found" in text and "1,234" in text
