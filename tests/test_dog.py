from game import dog
from game.enemies import Enemy
from game.input import Action
from game.loop import STEP
from game.persistence import load_game, save_game
from game.scenes.shop import _build_shop_items, update_shop
from game.simulation import new_run
from tests.test_gameplay import make_state, press


def _with_dog():
    state = make_state(x=5, y=5, has_dog=True)
    dog.update_dog(state, STEP)
    return state


def test_the_dog_appears_beside_the_player_and_follows():
    state = _with_dog()
    assert max(abs(state.dog["x"] - 5), abs(state.dog["y"] - 5)) == 1
    state.player_x = 12
    for _ in range(int(1.5 / STEP)):
        dog.update_dog(state, STEP)
    assert max(abs(state.dog["x"] - 12), abs(state.dog["y"] - 5)) <= dog.FOLLOW_DISTANCE


def test_a_lost_dog_turns_up_beside_the_player():
    state = _with_dog()
    state.player_x, state.player_y = 19, 19
    state.dog.update(x=0, y=0)
    state.player_x = state.player_y = 18
    state.dog.update(x=0, y=0)
    dog.update_dog(state, STEP)
    assert max(abs(state.dog["x"] - 18), abs(state.dog["y"] - 18)) == 1


def test_it_barks_at_enemies_but_not_all_the_time():
    state = _with_dog()
    state.enemies = [Enemy(state.dog["x"] + dog.BARK_RANGE, state.dog["y"], "snake")]
    dog.update_dog(state, STEP)
    assert [e.text for e in state.events] == ["Woof!"] and "dog barks" in state.hud_message
    state.game_time += dog.BARK_COOLDOWN / 2
    dog.update_dog(state, STEP)
    assert len(state.events) == 1
    state.game_time += dog.BARK_COOLDOWN
    dog.update_dog(state, STEP)
    assert len(state.events) == 2


def test_the_dog_is_bought_once_and_saved():
    state = new_run(3)
    state.active_scene, state.shop_tab, state.player_gold = "shop", 0, 1000
    items = _build_shop_items(state)
    state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "dog")
    update_shop(press(Action.CONFIRM), state)
    assert state.has_dog and state.player_gold < 1000
    gold = state.player_gold
    update_shop(press(Action.CONFIRM), state)
    assert state.player_gold == gold  # only one dog
    assert save_game(state) is None
    assert load_game().has_dog


def test_a_trained_dog_digs_up_gems_now_and_then():
    from game.objects.registry import DOG_TRAINING
    from game.simulation import new_run

    found = 0
    for seed in range(20):
        state = new_run(seed)
        state.has_dog, state.dog_training = True, 2
        state.player_x, state.player_y = 30, 30  # out in the meadow
        state.enemies = []
        dog.update_dog(state, STEP)
        state.game_time += DOG_TRAINING["interval"]
        dog.update_dog(state, STEP)
        found += sum(state.inventory["gems"].values())
    assert 3 <= found <= 19  # about 60% of tries (some rolls find nothing)


def test_an_untrained_dog_never_digs():
    state = _with_dog()
    state.game_time += 1000
    dog.update_dog(state, STEP)
    assert not state.inventory["gems"]


def test_training_is_bought_in_order_and_saved():
    state = new_run(3)
    state.active_scene, state.shop_tab, state.player_gold = "shop", 0, 2000
    state.has_dog = True
    for level in (1, 2):
        items = _build_shop_items(state)
        state.shop_cursor = next(i for i, it in enumerate(items) if it["key"] == "dog_training")
        update_shop(press(Action.CONFIRM), state)
        assert state.dog_training == level
    items = _build_shop_items(state)
    assert "(Best)" in next(it for it in items if it["key"] == "dog_training")["label"]
    assert save_game(state) is None
    assert load_game().dog_training == 2
