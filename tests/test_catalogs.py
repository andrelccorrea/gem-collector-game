"""Tests for Checkpoint 4: tool/enemy object definitions and catalog registry."""

import game.combat
import game.constants
import game.enemies
import game.tools
from game.objects.registry import (
    ENEMY_CATALOG,
    TOOL_CATALOG,
    build_enemy_catalog,
    build_tool_catalog,
)
from game.objects.tools.upgrades import TOOL_MAX_LEVEL, TOOL_UPGRADE_COSTS

# ---------------------------------------------------------------------------
# Tool catalog tests
# ---------------------------------------------------------------------------


def test_tool_catalog_has_3_tools():
    """build_tool_catalog() returns exactly 3 entries."""
    catalog = build_tool_catalog()
    assert len(catalog) == 3


def test_tool_catalog_has_expected_names():
    """TOOL_CATALOG contains keys 'shovel', 'pickaxe', 'gold_pan'."""
    assert "shovel" in TOOL_CATALOG
    assert "pickaxe" in TOOL_CATALOG
    assert "gold_pan" in TOOL_CATALOG


def test_tool_def_compatible_biomes_are_tuples():
    """Every tool's compatible_biomes is a tuple."""
    for name, tool_def in TOOL_CATALOG.items():
        assert isinstance(
            tool_def.compatible_biomes, tuple
        ), f"{name}.compatible_biomes should be a tuple, got {type(tool_def.compatible_biomes)}"


def test_tool_def_compatible_types_are_tuples():
    """Every tool's compatible_types is a tuple."""
    for name, tool_def in TOOL_CATALOG.items():
        assert isinstance(
            tool_def.compatible_types, tuple
        ), f"{name}.compatible_types should be a tuple, got {type(tool_def.compatible_types)}"


def test_tool_upgrade_costs_has_levels_2_to_5():
    """TOOL_UPGRADE_COSTS has keys 2, 3, 4, 5."""
    assert set(TOOL_UPGRADE_COSTS.keys()) == {2, 3, 4, 5}


def test_tool_max_level_is_5():
    """TOOL_MAX_LEVEL == 5."""
    assert TOOL_MAX_LEVEL == 5


def test_tool_catalog_not_in_constants():
    """game.constants has no attribute TOOL_CATALOG (it was removed in checkpoint 4)."""
    assert not hasattr(game.constants, "TOOL_CATALOG")


# ---------------------------------------------------------------------------
# Enemy catalog tests
# ---------------------------------------------------------------------------


def test_enemy_catalog_has_3_enemies():
    """build_enemy_catalog() returns exactly 3 entries."""
    catalog = build_enemy_catalog()
    assert len(catalog) == 3


def test_enemy_catalog_has_expected_names():
    """ENEMY_CATALOG contains keys 'snake', 'bear', 'cave_bat'."""
    assert "snake" in ENEMY_CATALOG
    assert "bear" in ENEMY_CATALOG
    assert "cave_bat" in ENEMY_CATALOG


def test_enemy_def_biomes_are_tuples():
    """Every enemy's biomes is a tuple."""
    for name, enemy_def in ENEMY_CATALOG.items():
        assert isinstance(
            enemy_def.biomes, tuple
        ), f"{name}.biomes should be a tuple, got {type(enemy_def.biomes)}"


def test_enemy_def_has_valid_hp_and_attack():
    """Every enemy has hp > 0 and attack > 0."""
    for name, enemy_def in ENEMY_CATALOG.items():
        assert enemy_def.hp > 0, f"{name}.hp must be > 0"
        assert enemy_def.attack > 0, f"{name}.attack must be > 0"


def test_enemy_def_has_valid_speed():
    """Every enemy has speed > 0."""
    for name, enemy_def in ENEMY_CATALOG.items():
        assert enemy_def.speed > 0, f"{name}.speed must be > 0"


def test_enemy_catalog_not_in_constants():
    """game.constants has no attribute ENEMY_CATALOG (it was removed in checkpoint 4)."""
    assert not hasattr(game.constants, "ENEMY_CATALOG")


def test_color_snake_not_in_constants():
    """game.constants has no attribute COLOR_SNAKE (it was removed in checkpoint 4)."""
    assert not hasattr(game.constants, "COLOR_SNAKE")


# ---------------------------------------------------------------------------
# Individual tool definitions
# ---------------------------------------------------------------------------


def test_shovel_compatible_biomes():
    """Shovel is compatible with the meadow biome."""
    shovel = TOOL_CATALOG["shovel"]
    assert "meadow" in shovel.compatible_biomes


def test_shovel_compatible_types_include_mineable_grass():
    """Shovel compatible_types includes 'mineable_grass' (post-prospecting redesign)."""
    shovel = TOOL_CATALOG["shovel"]
    assert "mineable_grass" in shovel.compatible_types


def test_pickaxe_compatible_biomes():
    """Pickaxe is compatible with hillside and cave biomes."""
    pickaxe = TOOL_CATALOG["pickaxe"]
    assert "hillside" in pickaxe.compatible_biomes
    assert "cave" in pickaxe.compatible_biomes


def test_gold_pan_compatible_biomes():
    """Gold pan is compatible with the river biome."""
    gold_pan = TOOL_CATALOG["gold_pan"]
    assert "river" in gold_pan.compatible_biomes


def test_tool_melee_damage_positive():
    """All tools have melee_damage > 0."""
    for name, tool_def in TOOL_CATALOG.items():
        assert tool_def.melee_damage > 0, f"{name}.melee_damage must be > 0"


# ---------------------------------------------------------------------------
# Individual enemy definitions
# ---------------------------------------------------------------------------


def test_snake_biomes_include_meadow_and_river():
    """Snake is found in meadow and river biomes."""
    snake = ENEMY_CATALOG["snake"]
    assert "meadow" in snake.biomes
    assert "river" in snake.biomes


def test_bear_biomes_include_meadow_and_hillside():
    """Bear is found in meadow and hillside biomes."""
    bear = ENEMY_CATALOG["bear"]
    assert "meadow" in bear.biomes
    assert "hillside" in bear.biomes


def test_cave_bat_biome_is_cave_only():
    """Cave bat is found only in the cave biome."""
    cave_bat = ENEMY_CATALOG["cave_bat"]
    assert cave_bat.biomes == ("cave",)


def test_enemy_loot_values_are_positive():
    """All enemies have loot_value > 0."""
    for name, enemy_def in ENEMY_CATALOG.items():
        assert enemy_def.loot_value > 0, f"{name}.loot_value must be > 0"


def test_enemy_aggro_range_positive():
    """All enemies have aggro_range > 0."""
    for name, enemy_def in ENEMY_CATALOG.items():
        assert enemy_def.aggro_range > 0, f"{name}.aggro_range must be > 0"


# ---------------------------------------------------------------------------
# Integration tests: modified modules import without error
# ---------------------------------------------------------------------------


def test_tools_py_uses_registry():
    """game.tools imports TOOL_CATALOG from the registry (not constants)."""
    # If the import failed the module-level import at the top of this file would
    # have already raised an ImportError.  Verify the module-level constant is
    # the same object as the registry singleton.
    assert game.tools.TOOL_CATALOG is TOOL_CATALOG


def test_combat_py_uses_registry():
    """game.combat imports TOOL_CATALOG from the registry (not constants)."""
    assert game.combat.TOOL_CATALOG is TOOL_CATALOG


def test_enemies_py_uses_registry():
    """game.enemies imports ENEMY_CATALOG from the registry (not constants)."""
    assert game.enemies.ENEMY_CATALOG is ENEMY_CATALOG


# ---------------------------------------------------------------------------
# TOOL_UPGRADE_COSTS value sanity
# ---------------------------------------------------------------------------


def test_upgrade_costs_increase_with_level():
    """Each successive upgrade level costs more than the previous."""
    levels = sorted(TOOL_UPGRADE_COSTS.keys())
    for i in range(len(levels) - 1):
        assert (
            TOOL_UPGRADE_COSTS[levels[i]] < TOOL_UPGRADE_COSTS[levels[i + 1]]
        ), f"Upgrade cost for level {levels[i]} should be less than level {levels[i + 1]}"


def test_upgrade_costs_are_positive():
    """All upgrade costs are positive integers."""
    for level, cost in TOOL_UPGRADE_COSTS.items():
        assert cost > 0, f"Upgrade cost for level {level} must be > 0"
