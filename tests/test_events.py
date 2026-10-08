from clingine.renderer import StubRenderer
from game.combat import HIT_COLOR, enemy_attacks, player_attack
from game.enemies import Enemy
from game.events import (
    DULL_COLOR,
    GAIN_COLOR,
    LOSS_COLOR,
    MAX_PENDING,
    Event,
    emit,
    take_events,
)
from game.hud import PULSE_FRAMES, HudPulse, render_hud
from game.input import Action
from game.loop import STEP
from game.objects.registry import GEM_CATALOG
from game.player import set_hud_message
from game.state import GameState, gameplay_rng
from game.tools import use_tool
from tests.test_gameplay import make_state, press


def test_picking_up_a_gem_floats_it_in_its_color():
    state = make_state({(5, 5): "mineable_grass"})
    state.world_gems = {(5, 5): "quartz"}
    use_tool(press(Action.USE), state)
    color = GEM_CATALOG["quartz"].color[0]
    assert take_events(state) == [Event(5, 5, "+Quartz", GAIN_COLOR, "gem", color)]
    assert state.events == []


def test_digging_reports_finds_and_misses():
    texts = set()
    for seed in range(40):
        state = make_state({(5, 5): "mineable_grass"})
        state.rng = gameplay_rng(seed)
        use_tool(press(Action.USE), state)
        (event,) = take_events(state)
        texts.add(event.text_color)
    assert texts == {GAIN_COLOR, DULL_COLOR}


def test_combat_floats_damage_on_the_target():
    state = make_state()
    enemy = Enemy(6, 5, "snake")
    enemy.hp = enemy.max_hp = 100
    enemy.attack, enemy.attack_cooldown = 2, 0.0
    state.enemies = [enemy]
    player_attack(press(Action.ATTACK), state)
    enemy_attacks(state, STEP)
    hit, hurt = take_events(state)
    assert (hit.x, hit.y, hit.text_color) == (6, 5, HIT_COLOR)
    assert hurt == Event(5, 5, "-2", LOSS_COLOR, "heart")


def test_pending_events_are_capped():
    state = GameState()
    for i in range(MAX_PENDING + 5):
        emit(state, str(i), GAIN_COLOR)
    events = take_events(state)
    assert len(events) == MAX_PENDING and events[-1].text == str(MAX_PENDING + 4)


def _gold_cells(renderer, state):
    row = renderer.height - 3
    text = "".join(renderer.get_cell(x, row)[0] for x in range(renderer.width))
    at = text.index("Gold:")
    return [renderer.get_cell(at + i, row)[1] for i in range(len(f"Gold:${state.player_gold}"))]


def test_changed_counter_blinks_then_settles():
    renderer, state, pulse = StubRenderer(79, 23), GameState(run_id="a"), HudPulse()
    render_hud(renderer, state, pulse)
    normal = _gold_cells(renderer, state)
    state.player_gold += 10
    seen = []
    for _ in range(PULSE_FRAMES + 2):
        render_hud(renderer, state, pulse)
        seen.append(_gold_cells(renderer, state))
    assert seen[0] != normal and len(set(seen[0])) == 1  # whole counter highlighted
    assert normal in seen[:PULSE_FRAMES]  # it blinks
    assert seen[-1] == normal


def test_a_new_run_does_not_blink():
    renderer, state, pulse = StubRenderer(79, 23), GameState(run_id="a"), HudPulse()
    render_hud(renderer, state, pulse)
    normal = _gold_cells(renderer, state)
    state.run_id, state.player_gold = "b", 999
    render_hud(renderer, state, pulse)
    assert _gold_cells(renderer, state)[0] == normal[0]


def test_message_row_keeps_the_bag_fill():
    renderer, state = StubRenderer(79, 23), GameState()
    set_hud_message(state, "Found a Quartz!", 2.0)
    render_hud(renderer, state)
    row = "".join(renderer.get_cell(x, 22)[0] for x in range(79))
    assert "Found a Quartz!" in row and row.rstrip().endswith("Bag:0/15")
