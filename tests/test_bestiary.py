from clingine.renderer import StubRenderer
from game import bestiary, profile
from game.critters import Critter
from game.input import EMPTY_INPUT
from game.loop import STEP
from game.menu import render_bestiary
from game.objects.registry import CRITTERS, ENEMY_CATALOG
from game.scenes.game import GameScene
from game.simulation import new_run


def test_every_creature_has_an_entry():
    assert set(bestiary.ENTRIES) == set(CRITTERS) | set(ENEMY_CATALOG)


def test_a_first_sighting_is_announced_and_remembered_with_its_context():
    scene, state = GameScene(), new_run(5)
    scene.enter(state)
    state.enemies = []
    near = (state.player_x + 1, state.player_y)
    state.critters = [Critter("fox", *near, move_timer=99)]
    state.world_tiles.meta[near]["visibility"] = "visible"
    scene.update(EMPTY_INPUT, state, STEP)
    assert "New in your bestiary: Fox" in state.hud_message
    saved = profile.load_profile()["bestiary"]
    assert saved["fox"] == bestiary.context(state) and saved["fox"].endswith("by day")
    state.hud_message = ""
    scene.update(EMPTY_INPUT, state, STEP)
    assert "bestiary" not in state.hud_message  # only the first time


def test_unseen_creatures_hide_in_the_bestiary_screen():
    profile.record_sightings(["deer"], "Meadow, by day")
    renderer = StubRenderer(79, 23)
    render_bestiary(renderer, new_run(1))
    text = "\n".join("".join(renderer.get_cell(x, y)[0] for x in range(79)) for y in range(23))
    assert f"1/{len(bestiary.ENTRIES)}" in text
    assert "Deer" in text and "(Meadow, by day)" in text and "???" in text
    assert "Fox" not in text
