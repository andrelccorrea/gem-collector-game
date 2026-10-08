import random

from game.gems import (
    GEODE,
    GEODE_CRACK_FEE,
    GEODE_VALUE,
    crack_geode,
    get_gem_raw_value,
    roll_gem_drop,
)
from game.input import Action, InputState
from game.objects.registry import GEM_CATALOG
from game.scenes.lapidary import _build_lapidary_items, update_lapidary
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))


def _drops(biome, n=4000):
    rng = random.Random(9)
    return [roll_gem_drop(biome, 1, rng) for _ in range(n)]


def test_geodes_come_from_rocky_ground_only():
    assert GEODE in _drops("hillside") and GEODE in _drops("cave")
    assert GEODE not in _drops("meadow") and GEODE not in _drops("river")


def test_geodes_are_nearly_worthless_uncracked():
    assert get_gem_raw_value(GEODE) == GEODE_VALUE


def test_cracking_always_reveals_a_cave_gem_above_the_digging_tier():
    rng = random.Random(4)
    found = [crack_geode(1, rng) for _ in range(500)]
    assert all("cave" in GEM_CATALOG[g].biomes for g in found)
    assert any(GEM_CATALOG[g].min_tier == 3 for g in found)  # tier 1 + bonus reaches tier 3


def test_lapidary_cracks_a_geode_for_a_fee():
    state = GameState(player_gold=100)
    state.inventory["gems"] = {GEODE: 2}
    items = _build_lapidary_items(state)
    state.lapidary_cursor = next(i for i, it in enumerate(items) if it["action"] == "crack_geode")
    update_lapidary(CONFIRM, state)
    assert state.player_gold == 100 - GEODE_CRACK_FEE
    assert state.inventory["gems"][GEODE] == 1
    revealed = [g for g in state.inventory["gems"] if g != GEODE]
    assert len(revealed) == 1 and revealed[0] in GEM_CATALOG
    assert "geode held" in state.hud_message
