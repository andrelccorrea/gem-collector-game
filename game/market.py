"""Selling at the shop, with prices that react to how much of an item was just sold.

Every sale of an item kind (a gem, a polished gem kind, or a loot kind) raises that
kind's saturation by one, and each point of saturation lowers its next price. The
market recovers with game time, so spreading sales out (or selling a variety of
items) pays better than dumping one kind at once.
"""

from game.gems import get_gem_raw_value, polished_prices, take_polished_gem
from game.objects.registry import ENEMY_CATALOG

# Each unit of saturation lowers the price: multiplier = 1 / (1 + PRICE_DROP * saturation)
PRICE_DROP_PER_SALE = 0.10
# Game seconds for one unit of saturation to wear off.
RECOVERY_SECONDS_PER_SALE = 30.0

_LOOT_VALUES = {e.loot: e.loot_value for e in ENEMY_CATALOG.values() if e.loot}


def update_market(state, dt: float) -> None:
    """Let saturation wear off as game time passes."""
    if not state.market:
        return
    recovered = dt / RECOVERY_SECONDS_PER_SALE
    for key in list(state.market):
        state.market[key] -= recovered
        if state.market[key] <= 0:
            del state.market[key]


def price_multiplier(saturation: float) -> float:
    return 1.0 / (1.0 + PRICE_DROP_PER_SALE * saturation)


def _is_loot(key: str) -> bool:
    return key in _LOOT_VALUES


def _base_price(state, key: str) -> int:
    """Full-price value of the next unit of ``key`` that would be sold."""
    if _is_loot(key):
        return _LOOT_VALUES[key]
    if key.endswith("_polished"):
        return polished_prices(state, key)[0]
    return get_gem_raw_value(key)


def unit_price(state, key: str, extra_saturation: float = 0.0) -> int:
    """What the shop pays right now for one unit of ``key``."""
    saturation = state.market.get(key, 0.0) + extra_saturation
    return max(1, int(_base_price(state, key) * price_multiplier(saturation)))


def discount_percent(state, key: str) -> int:
    return round((1.0 - price_multiplier(state.market.get(key, 0.0))) * 100)


def _held(state, key: str) -> dict:
    return state.inventory["loot"] if _is_loot(key) else state.inventory["gems"]


def sell_one(state, key: str) -> int:
    """Sell one unit of ``key``; returns the gold received (0 if none is held)."""
    held = _held(state, key)
    if held.get(key, 0) <= 0:
        return 0
    price = unit_price(state, key)
    if key.endswith("_polished"):
        take_polished_gem(state, key)
    else:
        held[key] -= 1
        if held[key] == 0:
            del held[key]
    state.market[key] = state.market.get(key, 0.0) + 1.0
    state.player_gold += price
    state.lifetime_earnings += price
    return price


def sell_all(state, loot: bool) -> int:
    """Sell every gem (or every piece of loot), one unit at a time. Returns the total."""
    held = state.inventory["loot" if loot else "gems"]
    total = 0
    for key in list(held):
        while held.get(key, 0) > 0:
            total += sell_one(state, key)
    return total


def preview_sell_all(state, keys: list) -> int:
    """Total that ``sell_all`` would pay for these kinds, without selling anything."""
    total = 0
    for key in keys:
        count = _held(state, key).get(key, 0)
        if key.endswith("_polished"):
            prices = polished_prices(state, key)
            saturation = state.market.get(key, 0.0)
            total += sum(
                max(1, int(p * price_multiplier(saturation + i))) for i, p in enumerate(prices)
            )
        else:
            total += sum(unit_price(state, key, extra_saturation=i) for i in range(count))
    return total
