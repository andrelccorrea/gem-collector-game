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


def _polish_factors(gem_name: str, lapidary_level: int):
    """(gem, (min, max) gem multiplier, (min, max) machine bonus), or None if unknown."""
    gem = GEM_CATALOG.get(gem_name)
    if gem is None:
        return None
    upgrade = LAPIDARY_UPGRADES.get(lapidary_level, LAPIDARY_UPGRADES[1])
    bonus = (
        upgrade["mult_min"] / _LAPIDARY_BASE_MULT,
        upgrade["mult_max"] / _LAPIDARY_BASE_MULT,
    )
    return gem, (gem.polished_min_mult, gem.polished_max_mult), bonus


def polished_value_range(gem_name: str, lapidary_level: int) -> tuple[int, int]:
    """Lowest and highest price a cut can produce at this lapidary level."""
    factors = _polish_factors(gem_name, lapidary_level)
    if factors is None:
        return 0, 0
    gem, (gem_lo, gem_hi), (bonus_lo, bonus_hi) = factors
    return int(gem.value * gem_lo * bonus_lo), int(gem.value * gem_hi * bonus_hi)


def get_gem_polished_value(gem_name: str, lapidary_level: int, rng: random.Random) -> int:
    """Roll the sell price of one freshly cut gem at the given lapidary level."""
    factors = _polish_factors(gem_name, lapidary_level)
    if factors is None:
        return 0
    gem, (gem_lo, gem_hi), (bonus_lo, bonus_hi) = factors
    return int(gem.value * rng.uniform(gem_lo, gem_hi) * rng.uniform(bonus_lo, bonus_hi))


# Polished gems: inventory["gems"]["<name>_polished"] counts them and
# state.polished_gem_values["<name>_polished"] lists each one's price, highest first.


def add_polished_gem(state, gem_name: str, price: int) -> None:
    key = f"{gem_name}_polished"
    gems = state.inventory.setdefault("gems", {})
    gems[key] = gems.get(key, 0) + 1
    prices = state.polished_gem_values.setdefault(key, [])
    prices.append(price)
    prices.sort(reverse=True)


def polished_prices(state, key: str) -> list:
    """Prices of the held polished gems of this kind, highest first."""
    return state.polished_gem_values.get(key, [])


def take_polished_gem(state, key: str) -> int:
    """Remove the most valuable polished gem of this kind; returns its price."""
    gems = state.inventory["gems"]
    prices = state.polished_gem_values[key]
    price = prices.pop(0)
    gems[key] -= 1
    if gems[key] == 0:
        del gems[key]
        del state.polished_gem_values[key]
    return price


def total_gem_count(state) -> int:
    return sum(state.inventory.get("gems", {}).values())


def total_loot_count(state) -> int:
    return sum(state.inventory.get("loot", {}).values())
