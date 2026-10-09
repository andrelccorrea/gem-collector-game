from game import profile
from game.input import Action
from game.objects.registry import DEFAULT_OUTFIT, OUTFITS
from game.scenes.game import GameScene
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from tests.test_gameplay import press
from tests.test_sprites import SpriteRecorder

CONFIRM = press(Action.CONFIRM)


def _outfits_tab(gold):
    state = new_run(3)
    state.active_scene, state.shop_tab, state.player_gold = "shop", 5, gold
    return state


def _select(state, name):
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == name)


def test_buying_an_outfit_wears_it_and_keeps_it_for_later_runs():
    state = _outfits_tab(1000)
    _select(state, "miner")
    update_shop(CONFIRM, state)
    assert state.outfit == "miner" and state.player_gold == 1000 - OUTFITS["miner"]["cost"]
    saved = profile.load_profile()
    assert saved["outfit"] == "miner" and "miner" in saved["outfits"]

    later = new_run(4)
    GameScene().enter(later)
    assert later.outfit == "miner"
    later.active_scene, later.shop_tab, later.player_gold = "shop", 5, 0
    _select(later, DEFAULT_OUTFIT)
    update_shop(CONFIRM, later)  # owned outfits are free to wear again
    assert later.outfit == DEFAULT_OUTFIT and later.player_gold == 0


def test_an_outfit_needs_the_gold():
    state = _outfits_tab(10)
    _select(state, "royal")
    update_shop(CONFIRM, state)
    assert state.outfit == DEFAULT_OUTFIT and state.hud_message == "Not enough gold!"


def test_the_player_is_drawn_in_the_outfit():
    state = new_run(3)
    state.enemies, state.outfit = [], "ranger"
    renderer = SpriteRecorder(80, 24)
    GameScene().render(renderer, state)
    assert renderer.entities["player"][2] == "player~ranger"
    px, py = renderer.entities["player"][:2]
    assert renderer.get_cell(px, py)[1][0] == tuple(OUTFITS["ranger"]["color"])
