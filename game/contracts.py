"""Contract board: each game day three orders for gems or loot, paid above market.

The board rotates once per game day and is the same for the whole run (picked from the
seed and the day with a stable hash, never the gameplay RNG). Rewards follow the items'
own value: REWARD_MULTIPLIER times what they are worth, plus a flat bonus, and they
skip market saturation. A contract is claimed at the board by handing the items over.
"""

from game.daylight import DAY_SECONDS
from game.decor import stable_random
from game.gems import get_gem_raw_value
from game.objects.registry import ENEMY_CATALOG, GEM_CATALOG

REWARD_MULTIPLIER = 1.5
BONUS = 15
EASY_TIER = 2  # the first two orders ask for gems found with a basic or tier-2 tool
LOOT_VALUES = {e.loot: e.loot_value for e in ENEMY_CATALOG.values() if e.loot}


def day(state) -> int:
    return int(state.game_time // DAY_SECONDS)


def _value(item: str) -> int:
    return LOOT_VALUES[item] if item in LOOT_VALUES else get_gem_raw_value(item)


def offers(state) -> list:
    """Today's three contracts: [{"item", "count", "reward", "loot"}]."""
    today = day(state)
    easy = sorted(name for name, gem in GEM_CATALOG.items() if gem.min_tier <= EASY_TIER)
    pools = [easy, sorted(LOOT_VALUES), sorted(GEM_CATALOG)]
    board = []
    for i, pool in enumerate(pools):
        item = pool[int(stable_random(state.seed, today, i, 31) * len(pool))]
        count = 2 + int(stable_random(state.seed, today, i, 32) * 3)  # 2 to 4
        reward = round(_value(item) * count * REWARD_MULTIPLIER) + BONUS
        board.append({"item": item, "count": count, "reward": reward, "loot": item in LOOT_VALUES})
    return board


def _held(state, offer) -> dict:
    return state.inventory.setdefault("loot" if offer["loot"] else "gems", {})


def can_deliver(state, index: int) -> bool:
    offer = offers(state)[index]
    done = (day(state), index) in state.contracts_done
    return not done and _held(state, offer).get(offer["item"], 0) >= offer["count"]


def deliver(state, index: int) -> int:
    """Hand the items over and get paid; returns the reward (0 if not possible)."""
    if not can_deliver(state, index):
        return 0
    offer = offers(state)[index]
    held = _held(state, offer)
    held[offer["item"]] -= offer["count"]
    if held[offer["item"]] == 0:
        del held[offer["item"]]
    state.contracts_done.add((day(state), index))
    state.stats["contracts"] = state.stats.get("contracts", 0) + 1
    state.player_gold += offer["reward"]
    state.lifetime_earnings += offer["reward"]
    return offer["reward"]
