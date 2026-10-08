import dataclasses

import pytest

from game.objects.base import EnemyDef, GemDef, ToolDef
from game.objects.registry import (
    GEM_CATALOG,
    TOOL_CATALOG,
    TOOL_MAX_LEVEL,
    TOOL_UPGRADE_COSTS,
    build_enemy_catalog,
    build_gem_catalog,
    build_tool_catalog,
    load_catalogs,
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
# Catalog file loading
# ---------------------------------------------------------------------------


def test_build_catalogs_from_empty_entries():
    assert build_gem_catalog([]) == {}
    assert build_tool_catalog([]) == {}
    assert build_enemy_catalog([]) == {}


def test_gem_catalog_singleton():
    assert isinstance(GEM_CATALOG, dict)


def test_tool_catalog_singleton():
    assert isinstance(TOOL_CATALOG, dict)


def test_catalog_file_entries_become_frozen_defs_in_file_order(tmp_path):
    path = tmp_path / "catalogs.toml"
    path.write_text(
        """
[[gems]]
name = "zircon"
value = 42
polished_min_mult = 2.0
polished_max_mult = 2.5
char = "o"
color = [[1, 2, 3], [0, 0, 0]]
biomes = ["cave"]
rarity_weight = 3

[[gems]]
name = "agate"
value = 7
polished_min_mult = 2.0
polished_max_mult = 2.2
char = "o"
color = [[9, 9, 9], [0, 0, 0]]
biomes = ["meadow", "river"]
rarity_weight = 9
"""
    )
    catalog = build_gem_catalog(load_catalogs(path)["gems"])
    assert list(catalog) == ["zircon", "agate"]
    assert catalog["zircon"] == make_gem_def(
        name="zircon",
        value=42,
        polished_max_mult=2.5,
        color=((1, 2, 3), (0, 0, 0)),
        biomes=("cave",),
        rarity_weight=3,
    )
    hash(catalog["agate"])  # tuples, not lists: entries stay hashable


def test_duplicate_names_are_rejected():
    entry = {f.name: getattr(make_gem_def(), f.name) for f in dataclasses.fields(GemDef)}
    with pytest.raises(ValueError, match="duplicate"):
        build_gem_catalog([entry, dict(entry)])


def test_unknown_or_missing_fields_are_rejected():
    entry = {f.name: getattr(make_gem_def(), f.name) for f in dataclasses.fields(GemDef)}
    with pytest.raises(TypeError):
        build_gem_catalog([{**entry, "sparkle": 1}])
    entry.pop("value")
    with pytest.raises(TypeError):
        build_gem_catalog([entry])


def test_tool_upgrades_come_from_the_catalog_file():
    data = load_catalogs()
    assert TOOL_MAX_LEVEL == data["tool_upgrades"]["max_level"]
    assert set(TOOL_UPGRADE_COSTS) == set(range(2, TOOL_MAX_LEVEL + 1))
