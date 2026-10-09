import random

from game.constants import LAPIDARY_UPGRADES
from game.objects.registry import BAG_CAPACITIES, GEM_CATALOG, TOOL_CATALOG

# Geodes: rough stones dug up in rocky ground. Nearly worthless as they are, but the
# lapidary cracks them open for a fee to reveal a gem from a better pool than digging.
GEODE = "geode"
GEODE_VALUE = 3
GEODE_WEIGHT = 6
GEODE_BIOMES = frozenset({"hillside", "cave"})
GEODE_CRACK_FEE = 10
GEODE_TIER_BONUS = 2  # cracking draws from the cave pool at tier = digging tier + bonus

# Weight of "found nothing" for a tier-1 tool, and how much each extra tier removes
NO_DROP_WEIGHT = 65
NO_DROP_REDUCTION_PER_TIER = 8

# Lapidary base multiplier (level 1) — used to normalise upgrade bonuses
_LAPIDARY_BASE_MULT = LAPIDARY_UPGRADES[1]["mult_min"]


def effective_tier(tool_name: str | None, level: int = 1) -> int:
    """Digging quality of a tool: its tier, plus one for every two upgrade levels."""
    tool = TOOL_CATALOG.get(tool_name)
    return (tool.tier if tool is not None else 1) + (level - 1) // 2


def roll_gem_drop(biome: str, tier: int, rng: random.Random) -> str | None:
    """Roll for a gem drop in a biome with a tool of the given effective tier.

    Rarer gems need a higher tier (``GemDef.min_tier``), and each tier above the
    first makes empty digs less likely. Returns the gem name or None.
    """
    eligible = {
        name: gem
        for name, gem in GEM_CATALOG.items()
        if biome in gem.biomes and gem.min_tier <= tier
    }

    if not eligible:
        return None

    names = [""] + list(eligible.keys())
    no_drop = max(NO_DROP_WEIGHT - NO_DROP_REDUCTION_PER_TIER * (tier - 1), 0)
    weights = [no_drop] + [eligible[n].rarity_weight for n in eligible]
    if biome in GEODE_BIOMES:
        names.append(GEODE)
        weights.append(GEODE_WEIGHT)

    result = rng.choices(names, weights=weights, k=1)[0]
    return result if result else None


def bag_capacity(state) -> int:
    return BAG_CAPACITIES[state.bag_level] + state.bag_bonus


def bag_count(state) -> int:
    """Items carried: every gem (raw and polished) and every piece of loot."""
    return sum(state.inventory.get("gems", {}).values()) + sum(
        state.inventory.get("loot", {}).values()
    )


def bag_has_room(state) -> bool:
    return bag_count(state) < bag_capacity(state)


def add_gem_to_inventory(state, gem_name: str) -> None:
    """Add one gem of the given type to inventory."""
    gems = state.inventory.setdefault("gems", {})
    gems[gem_name] = gems.get(gem_name, 0) + 1
    state.stats["gems_found"] = state.stats.get("gems_found", 0) + 1


def add_loot_to_inventory(state, loot_name: str) -> None:
    """Add one loot item to inventory."""
    loot = state.inventory.setdefault("loot", {})
    loot[loot_name] = loot.get(loot_name, 0) + 1


def get_gem_raw_value(gem_name: str) -> int:
    """Return the base (raw) sell value for a gem."""
    if gem_name == GEODE:
        return GEODE_VALUE
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


def roll_cut_value(
    gem_name: str, lapidary_level: int, band: tuple[float, float], rng: random.Random
) -> int:
    """Price of a cut whose quality landed in ``band``: a (low, high) share of the
    gem's polished price range at this lapidary level."""
    low, high = polished_value_range(gem_name, lapidary_level)
    return int(low + (high - low) * rng.uniform(*band))


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


def crack_geode(tier: int, rng: random.Random) -> str:
    """The gem inside a geode: always something, from the cave pool at a boosted tier."""
    eligible = [
        gem
        for gem in GEM_CATALOG.values()
        if "cave" in gem.biomes and gem.min_tier <= tier + GEODE_TIER_BONUS
    ]
    return rng.choices([g.name for g in eligible], [g.rarity_weight for g in eligible])[0]
