import dataclasses
import types
from types import ModuleType
from unittest.mock import patch

import pytest

from game.objects.base import EnemyDef, GemDef, ToolDef
from game.objects.registry import (
    GEM_CATALOG,
    TOOL_CATALOG,
    build_enemy_catalog,
    build_gem_catalog,
    build_tool_catalog,
)

# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

GEM_COLOR = ((255, 0, 0), (0, 0, 0))


def make_gem_def(**overrides):
    defaults = dict(
        name="test_gem",
        value=10,
        polished_min_mult=2.0,
        polished_max_mult=3.0,
        char="o",
        color=GEM_COLOR,
        biomes=("cave",),
        rarity_weight=5,
    )
    defaults.update(overrides)
    return GemDef(**defaults)


def make_tool_def(**overrides):
    defaults = dict(
        name="test_tool",
        cost=0,
        compatible_biomes=("meadow",),
        compatible_types=("grass",),
        melee_damage=3,
        base_yield=1,
        desc="test",
    )
    defaults.update(overrides)
    return ToolDef(**defaults)


def make_enemy_def(**overrides):
    defaults = dict(
        name="test_enemy",
        hp=10,
        attack=2,
        char="e",
        color=GEM_COLOR,
        biomes=("meadow",),
        loot="test_loot",
        loot_value=5,
        aggro_range=4,
        speed=1.5,
        attack_cooldown=2.0,
    )
    defaults.update(overrides)
    return EnemyDef(**defaults)


# ---------------------------------------------------------------------------
# Dataclass frozen tests
# ---------------------------------------------------------------------------


def test_gem_def_frozen():
    gem = make_gem_def()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        gem.value = 99  # type: ignore[misc]


def test_tool_def_frozen():
    tool = make_tool_def()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        tool.cost = 999  # type: ignore[misc]


def test_enemy_def_frozen():
    enemy = make_enemy_def()
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        enemy.hp = 999  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Dataclass field tests
# ---------------------------------------------------------------------------


def test_gem_def_fields():
    gem = make_gem_def()
    assert gem.name == "test_gem"
    assert gem.value == 10
    assert gem.polished_min_mult == 2.0
    assert gem.polished_max_mult == 3.0
    assert gem.char == "o"
    assert gem.color == GEM_COLOR
    assert gem.biomes == ("cave",)
    assert gem.rarity_weight == 5


def test_tool_def_fields():
    tool = make_tool_def()
    assert tool.name == "test_tool"
    assert tool.cost == 0
    assert tool.compatible_biomes == ("meadow",)
    assert tool.compatible_types == ("grass",)
    assert tool.melee_damage == 3
    assert tool.base_yield == 1
    assert tool.desc == "test"


def test_enemy_def_fields():
    enemy = make_enemy_def()
    assert enemy.name == "test_enemy"
    assert enemy.hp == 10
    assert enemy.attack == 2
    assert enemy.char == "e"
    assert enemy.color == GEM_COLOR
    assert enemy.biomes == ("meadow",)
    assert enemy.loot == "test_loot"
    assert enemy.loot_value == 5
    assert enemy.aggro_range == 4
    assert enemy.speed == 1.5
    assert enemy.attack_cooldown == 2.0


# ---------------------------------------------------------------------------
# Hashability and equality (frozen dataclasses are hashable by default)
# ---------------------------------------------------------------------------


def test_gem_def_hashable():
    gem1 = make_gem_def()
    gem2 = make_gem_def()
    assert hash(gem1) == hash(gem2)


def test_gem_def_equality():
    gem1 = make_gem_def()
    gem2 = make_gem_def()
    assert gem1 == gem2


# ---------------------------------------------------------------------------
# Registry builder tests — empty subpackages
# ---------------------------------------------------------------------------


def test_build_gem_catalog_empty():
    with patch("game.objects.registry.pkgutil.iter_modules", return_value=[]):
        catalog = build_gem_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) == 0


def test_build_tool_catalog_empty():
    with patch("game.objects.registry.pkgutil.iter_modules", return_value=[]):
        catalog = build_tool_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) == 0


def test_build_enemy_catalog_empty():
    with patch("game.objects.registry.pkgutil.iter_modules", return_value=[]):
        catalog = build_enemy_catalog()
    assert isinstance(catalog, dict)
    assert len(catalog) == 0


# ---------------------------------------------------------------------------
# Singleton tests
# ---------------------------------------------------------------------------


def test_gem_catalog_singleton():
    assert isinstance(GEM_CATALOG, dict)


def test_tool_catalog_singleton():
    assert isinstance(TOOL_CATALOG, dict)


# ---------------------------------------------------------------------------
# Dynamic discovery test (future-proofing)
# ---------------------------------------------------------------------------


def test_registry_discovers_new_gem():
    """Inject a fake gem module into sys.modules and patch pkgutil.iter_modules
    so build_gem_catalog() picks it up and registers the GemDef it contains."""
    fake_gem = make_gem_def(name="discovered_gem", value=42)

    fake_module: ModuleType = types.ModuleType("game.objects.gems.fake_gem")
    fake_module.discovered_gem = fake_gem  # type: ignore[attr-defined]

    fake_module_name = "game.objects.gems.fake_gem"

    # iter_modules yields (finder, name, ispkg) triples
    fake_iter_result = [(None, fake_module_name, False)]

    with patch("game.objects.registry.pkgutil.iter_modules", return_value=fake_iter_result):
        with patch("game.objects.registry.importlib.import_module", return_value=fake_module):
            catalog = build_gem_catalog()

    assert "discovered_gem" in catalog
    assert catalog["discovered_gem"] is fake_gem
