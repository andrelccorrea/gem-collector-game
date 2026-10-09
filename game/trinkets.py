"""Trinkets: one slot, a few charms that each change how a run is played.

Bought at the shop and kept for the run; only the one worn works. Data (name, price,
description, numbers) lives in catalogs.toml [trinkets.*].
"""

from game.objects.registry import TRINKETS


def wearing(state, key: str) -> bool:
    return state.trinket == key


def sale_saturation(state) -> float:
    """How much one sale pushes its kind's price down (the Merchant's Scale softens it)."""
    return TRINKETS["scale"]["saturation"] if wearing(state, "scale") else 1.0


def lucky_retry(state) -> bool:
    """With the Lucky Clover, whether a dig that found nothing gets another try."""
    return wearing(state, "clover") and state.rng.random() < TRINKETS["clover"]["chance"]
