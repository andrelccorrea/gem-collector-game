import random

from game.constants import LAPIDARY_UPGRADES
from game.objects.registry import GEM_CATALOG

# No-drop weight: 65% chance of nothing
NO_DROP_WEIGHT = 65

# Lapidary base multiplier (level 1) — used to normalise upgrade bonuses
_LAPIDARY_BASE_MULT = LAPIDARY_UPGRADES[1]["mult_min"]


def roll_gem_drop(biome: str, tool_name: str, rng: random.Random) -> str | None:
    """Roll for a gem drop based on biome and tool. Returns gem name or None."""
    eligible = {name: gem for name, gem in GEM_CATALOG.items() if biome in gem.biomes}

    if not eligible:
        return None

    names = [""] + list(eligible.keys())
    weights = [NO_DROP_WEIGHT] + [eligible[n].rarity_weight for n in eligible]

    result = rng.choices(names, weights=weights, k=1)[0]
    return result if result else None


def add_gem_to_inventory(state, gem_name: str) -> None:
    """Add one gem of the given type to inventory."""
    gems = state.inventory.setdefault("gems", {})
    gems[gem_name] = gems.get(gem_name, 0) + 1


def add_loot_to_inventory(state, loot_name: str) -> None:
    """Add one loot item to inventory."""
    loot = state.inventory.setdefault("loot", {})
    loot[loot_name] = loot.get(loot_name, 0) + 1


def get_gem_raw_value(gem_name: str) -> int:
    """Return the base (raw) sell value for a gem."""
    gem = GEM_CATALOG.get(gem_name)
    return gem.value if gem is not None else 0


def get_gem_polished_value(gem_name: str, lapidary_level: int, rng: random.Random) -> int:
    """Return a randomised polished sell value for a gem at the given lapidary level."""
    gem = GEM_CATALOG.get(gem_name)
    if gem is None:
        return 0
    upgrade = LAPIDARY_UPGRADES.get(lapidary_level, LAPIDARY_UPGRADES[1])
    lapidary_bonus = upgrade["mult_min"] / _LAPIDARY_BASE_MULT
    gem_mult = rng.uniform(gem.polished_min_mult, gem.polished_max_mult)
    return int(gem.value * gem_mult * lapidary_bonus)


def total_gem_count(state) -> int:
    return sum(state.inventory.get("gems", {}).values())


def total_loot_count(state) -> int:
    return sum(state.inventory.get("loot", {}).values())
