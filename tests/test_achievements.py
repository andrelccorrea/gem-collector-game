from clingine.renderer import StubRenderer
from game import achievements, daylight, profile
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.menu import render_achievements
from game.scenes.game import GameScene
from game.simulation import new_run


def test_achievements_are_unique_and_rewards_follow_effort():
    ids = [a[0] for a in achievements.ACHIEVEMENTS]
    names = [a[1] for a in achievements.ACHIEVEMENTS]
    descs = [a[2] for a in achievements.ACHIEVEMENTS]
    assert len(set(ids)) == len(set(names)) == len(set(descs)) == len(ids)
    rewards = dict((a[0], a[3]) for a in achievements.ACHIEVEMENTS)
    assert rewards["first_find"] < rewards["prospector"] < rewards["tycoon"] < rewards["gem_legend"]


def test_each_condition_can_be_met():
    state = new_run(3)
    assert achievements.newly_unlocked(state, set()) == []  # nothing at the start
    state.inventory["gems"] = {"quartz": 1, "quartz_polished": 1}
    state.inventory["loot"] = {"bear_pelt": 1}
    state.supplies = {"bandage": 1, "lamp_oil": 1}
    state.lifetime_earnings, state.museum = 6000, ["a", "b", "c", "d", "e"]
    state.inventory["tools"] = {name: {"level": 1} for name in achievements.TOOL_CATALOG}
    state.armor_level = len(achievements.ARMOR["costs"]) - 1
    state.boots_level = len(achievements.BOOTS["costs"]) - 1
    state.has_won, state.hardcore = True, True
    state.player_x, state.player_y = 190, 40
    state.seen_species = set(achievements.CRITTERS) | {"bear"}
    state.friends = {"deer", "fox", "rabbit", "owl", "duck"}
    state.game_time = 0.8 * daylight.DAY_SECONDS
    assert set(achievements.newly_unlocked(state, set())) == set(achievements.BY_ID)


def test_unlocking_pays_reputation_once_and_is_announced():
    scene, state = GameScene(), new_run(3)
    scene.enter(state)
    before = profile.load_profile()["reputation"]
    state.lifetime_earnings = 1000
    scene.update(EMPTY_INPUT, state, STEP)
    saved = profile.load_profile()
    assert {"prospector", "first_find"} <= set(saved["achievements"])
    assert saved["reputation"] == before + 1 + 2
    assert "Achievement" in state.hud_message
    assert any(e.kind == "achievement" for e in state.events)
    scene.update(EMPTY_INPUT, state, STEP)
    GameScene().enter(state)
    assert profile.load_profile()["reputation"] == before + 3  # never paid twice


def test_the_menu_lists_achievements_and_progress():
    profile.unlock_achievements(["first_find"], {"first_find": 1})
    renderer = StubRenderer(79, 23)
    render_achievements(renderer, new_run(1))
    text = "\n".join("".join(renderer.get_cell(x, y)[0] for x in range(79)) for y in range(23))
    assert f"1/{len(achievements.ACHIEVEMENTS)}" in text
    assert "[x] First Glint" in text and "[ ] Gem Legend" in text
