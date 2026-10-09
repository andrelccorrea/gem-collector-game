"""Deal of the day: each game day the shop sells one item for less.

The item is picked from the run's seed and the day number (no draw from the gameplay
RNG), so a run sees the same deals whatever happens in it. The shop shows the deal and
a countdown to the next one.
"""

from game.daylight import DAY_SECONDS
from game.decor import stable_random
from game.objects.registry import SUPPLIES, TOOL_CATALOG, TRINKETS

DISCOUNT = 0.25
GEAR = ("bag", "lantern", "armor", "dowsing rod", "boots")


def _candidates() -> list:
    tools = [name for name, tool in TOOL_CATALOG.items() if tool.cost > 0]
    return tools + list(GEAR) + list(SUPPLIES) + list(TRINKETS) + ["recall_charm", "dog"]


def deal_key(state) -> str:
    """The item on sale today (a tool, gear or supply key, or "recall_charm")."""
    day = int(state.game_time // DAY_SECONDS)
    options = _candidates()
    return options[int(stable_random(state.seed, day, 7331) * len(options))]


def price(state, key: str, base: int) -> int:
    return round(base * (1 - DISCOUNT)) if key == deal_key(state) else base


def seconds_left(state) -> float:
    return DAY_SECONDS - state.game_time % DAY_SECONDS


def banner(state) -> str:
    key = deal_key(state)
    name = SUPPLIES[key]["name"] if key in SUPPLIES else key.replace("_", " ").title()
    minutes, seconds = divmod(int(seconds_left(state)), 60)
    off = round(DISCOUNT * 100)
    return f"Deal of the day: {name} -{off}%  (new deal in {minutes}:{seconds:02d})"
