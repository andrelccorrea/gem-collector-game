"""Tests for Checkpoint 3: per-gem GemDef files and rewired gems.py."""

import random

import game.constants
from game.gems import get_gem_polished_value, get_gem_raw_value, roll_gem_drop
from game.objects.registry import GEM_CATALOG, build_gem_catalog

# ---------------------------------------------------------------------------
# Catalog structure tests
# ---------------------------------------------------------------------------


def test_catalog_has_17_gems():
    """build_gem_catalog() returns exactly 17 entries."""
    catalog = build_gem_catalog()
    assert len(catalog) == 17


def test_a_gems_shape_tells_its_tier_not_just_its_color():
    """Glyph and sprite shape follow the tier, so rarity never rests on color alone."""
    from game.gems import gem_sprite

    shapes = {1: ("●", "gem_round"), 2: ("■", "gem_square"), 3: ("♦", "gem")}
    catalog = build_gem_catalog()
    for name, gem in catalog.items():
        assert (gem.char, gem_sprite(name)) == shapes[gem.min_tier], name
    assert gem_sprite("ruby_polished") == gem_sprite("ruby")


def test_all_gems_have_positive_value():
    """Every gem has value > 0."""
    catalog = build_gem_catalog()
    for name, gem in catalog.items():
        assert gem.value > 0, f"{name} has non-positive value={gem.value}"


def test_all_gems_have_valid_multipliers():
    """Every gem has polished_min_mult > 1.0 and polished_max_mult > polished_min_mult."""
    catalog = build_gem_catalog()
    for name, gem in catalog.items():
        assert gem.polished_min_mult > 1.0, (
            f"{name} polished_min_mult={gem.polished_min_mult} is not > 1.0"
        )
        assert gem.polished_max_mult > gem.polished_min_mult, (
            f"{name} polished_max_mult={gem.polished_max_mult} is not > "
            f"polished_min_mult={gem.polished_min_mult}"
        )


def test_gem_colors_are_unique():
    """All 17 gems have a distinct fg RGB color (first element of gem.color)."""
    catalog = build_gem_catalog()
    fg_colors = [gem.color[0] for gem in catalog.values()]
    unique_colors = set(fg_colors)
    assert len(unique_colors) == len(catalog), (
        f"Expected {len(catalog)} unique fg colors, found {len(unique_colors)}. "
        f"Duplicates: {[c for c in fg_colors if fg_colors.count(c) > 1]}"
    )


def test_every_biome_has_at_least_two_gems():
    """Each of the four biomes contains at least 2 gems."""
    catalog = build_gem_catalog()
    biomes_to_check = ["meadow", "hillside", "cave", "river"]
    for biome in biomes_to_check:
        gems_in_biome = [name for name, gem in catalog.items() if biome in gem.biomes]
        assert len(gems_in_biome) >= 2, (
            f"Biome '{biome}' has only {len(gems_in_biome)} gem(s): {gems_in_biome}"
        )


# ---------------------------------------------------------------------------
# Rarity and tier tests
# ---------------------------------------------------------------------------


def test_legendary_gems_are_cave_only():
    """paraiba_tourmaline and diamond have biomes==('cave',) and rarity_weight==1."""
    catalog = build_gem_catalog()
    for gem_name in ("paraiba_tourmaline", "diamond"):
        gem = catalog[gem_name]
        assert gem.biomes == ("cave",), f"{gem_name} biomes={gem.biomes}, expected ('cave',)"
        assert gem.rarity_weight == 1, f"{gem_name} rarity_weight={gem.rarity_weight}, expected 1"


def test_rarity_weight_ordering():
    """quartz has highest rarity_weight (50); paraiba_tourmaline and diamond have the lowest (1)."""
    catalog = build_gem_catalog()
    assert catalog["quartz"].rarity_weight == 50, (
        f"quartz rarity_weight={catalog['quartz'].rarity_weight}, expected 50"
    )
    assert catalog["paraiba_tourmaline"].rarity_weight == 1
    assert catalog["diamond"].rarity_weight == 1


# ---------------------------------------------------------------------------
# Roll drop tests
# ---------------------------------------------------------------------------


def test_roll_gem_drop_cave():
    """100 cave rolls only return gems that belong to the cave biome (or None)."""
    rng = random.Random(42)
    catalog = build_gem_catalog()
    cave_gem_names = {name for name, gem in catalog.items() if "cave" in gem.biomes} | {"geode"}
    for _ in range(100):
        result = roll_gem_drop("cave", 3, rng)
        if result is not None:
            assert result in cave_gem_names, (
                f"roll_gem_drop('cave', 3) returned '{result}', which is not in the cave biome"
            )


def test_roll_gem_drop_meadow():
    """100 meadow rolls only return gems that belong to the meadow biome (or None)."""
    rng = random.Random(7)
    catalog = build_gem_catalog()
    meadow_gem_names = {name for name, gem in catalog.items() if "meadow" in gem.biomes}
    for _ in range(100):
        result = roll_gem_drop("meadow", 1, rng)
        if result is not None:
            assert result in meadow_gem_names, (
                f"roll_gem_drop('meadow', 1) returned '{result}', which is not in the meadow biome"
            )


def test_roll_gem_drop_returns_none_sometimes():
    """200 cave rolls must include at least one None (no-drop weight applies)."""
    rng = random.Random(99)
    results = [roll_gem_drop("cave", 3, rng) for _ in range(200)]
    none_count = results.count(None)
    assert none_count > 0, "Expected at least one None in 200 cave rolls, but got zero Nones"


def test_roll_gem_drop_unknown_biome_returns_none():
    """An unknown biome has an empty eligible pool so roll_gem_drop returns None."""
    result = roll_gem_drop("nonexistent_biome", 1, random.Random(0))
    assert result is None


# ---------------------------------------------------------------------------
# Polished value tests
# ---------------------------------------------------------------------------


def test_get_gem_raw_value_quartz():
    """get_gem_raw_value('quartz') == 5."""
    assert get_gem_raw_value("quartz") == 5


def test_get_gem_polished_value_greater_than_raw():
    """get_gem_polished_value('ruby', lapidary_level=1) is always > get_gem_raw_value('ruby')."""
    raw = get_gem_raw_value("ruby")
    rng = random.Random(1)
    for _ in range(20):
        polished = get_gem_polished_value("ruby", 1, rng)
        assert polished > raw, f"Polished ruby value {polished} is not greater than raw value {raw}"


def test_get_gem_polished_value_lapidary_bonus():
    """Mean polished value at lapidary_level=3 >= mean at lapidary_level=1 over 50 samples each."""
    rng = random.Random(123)
    samples_l1 = [get_gem_polished_value("ruby", 1, rng) for _ in range(50)]
    samples_l3 = [get_gem_polished_value("ruby", 3, rng) for _ in range(50)]
    mean_l1 = sum(samples_l1) / len(samples_l1)
    mean_l3 = sum(samples_l3) / len(samples_l3)
    assert mean_l3 >= mean_l1, (
        f"Expected mean polished value at level 3 ({mean_l3:.1f}) >= level 1 ({mean_l1:.1f})"
    )


# ---------------------------------------------------------------------------
# Specific gem presence tests
# ---------------------------------------------------------------------------


ALL_17_GEM_NAMES = [
    "quartz",
    "citrine",
    "tourmaline",
    "amethyst",
    "garnet",
    "topaz",
    "turquoise",
    "aquamarine",
    "emerald",
    "alexandrite",
    "chrysoberyl",
    "ruby",
    "sapphire",
    "opal",
    "imperial_topaz",
    "paraiba_tourmaline",
    "diamond",
]


def test_specific_gems_exist():
    """All 17 gem names exist as keys in GEM_CATALOG."""
    for gem_name in ALL_17_GEM_NAMES:
        assert gem_name in GEM_CATALOG, f"'{gem_name}' not found in GEM_CATALOG"


def test_gem_catalog_not_in_constants():
    """game.constants no longer has a GEM_CATALOG attribute (the old catalog has been removed)."""
    assert not hasattr(game.constants, "GEM_CATALOG"), (
        "game.constants still has GEM_CATALOG — it should have been removed in Checkpoint 3"
    )
