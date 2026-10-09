"""Traveling merchant: on some game days a cart sets up beside a landmark.

It sells two offers drawn from a small list (one of each) and buys one kind of gem at
twice its value, a few a day. Which days, where and what all come from a stable hash of
the seed and the day (never the gameplay RNG), so a run's merchant is fixed. The cart is
gone when the day ends, so its deals are now or never.
"""

from game.constants import MAP_HEIGHT, MAP_WIDTH
from game.daylight import DAY_SECONDS
from game.decor import stable_random
from game.gems import get_gem_raw_value
from game.landmarks import landmarks
from game.objects.registry import GEM_CATALOG

VISIT_SHARE = 0.4  # share of game days with a merchant
WANTED_MULTIPLIER = 2
WANTED_PER_DAY = 5
# key -> (name, price, description)
OFFERS = {
    "geodes": ("Two geodes", 60, "Crack them at the Lapidary"),
    "elixir": ("Vigor elixir", 220, "+2 maximum HP for this run, and a full heal"),
    "oil_crate": ("Crate of lamp oil", 60, "Three Lamp Oils"),
    "bandage_pack": ("Pack of bandages", 55, "Three Bandages"),
    "charm_pair": ("Pair of recall charms", 50, "Two Recall Charms"),
}


def day(state) -> int:
    return int(state.game_time // DAY_SECONDS)


def today(state):
    """{"pos", "stock", "wants"} when the merchant is out today, else None."""
    if state.world_tiles is None:
        return None
    d = day(state)
    if stable_random(state.seed, d, 555) >= VISIT_SHARE:
        return None
    spots = sorted(landmarks(state))
    if not spots:
        return None
    lx, ly = spots[int(stable_random(state.seed, d, 556) * len(spots))]
    pos = None
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        x, y = lx + dx, ly + dy
        tile = state.world_tiles.meta.get((x, y))
        if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT and tile and tile["walkable"]:
            pos = (x, y)
            break
    if pos is None:
        return None
    keys = sorted(OFFERS)
    first = int(stable_random(state.seed, d, 557) * len(keys))
    second = (first + 1 + int(stable_random(state.seed, d, 558) * (len(keys) - 1))) % len(keys)
    easy = sorted(name for name, gem in GEM_CATALOG.items() if gem.min_tier <= 2)
    wants = easy[int(stable_random(state.seed, d, 559) * len(easy))]
    return {"pos": pos, "stock": [keys[first], keys[second]], "wants": wants}


def render_cart(renderer, state, view) -> None:
    from game.camera import OBJECT
    from game.daylight import phase, shade, tint_at

    visit = today(state)
    if visit is None or not view.contains(*visit["pos"]):
        return
    if state.world_tiles.meta.get(visit["pos"], {}).get("visibility") == "unseen":
        return
    light = tint_at(state, phase(state), *visit["pos"])
    sx, sy = visit["pos"][0] - view.x, visit["pos"][1] - view.y
    renderer.set_cell(sx, sy, "M", shade(((255, 210, 90), (60, 40, 0)), light))
    renderer.set_sprite(sx, sy, OBJECT, "merchant", light)


def here(state) -> bool:
    visit = today(state)
    return visit is not None and visit["pos"] == (state.player_x, state.player_y)


def bought_today(state, key: str) -> int:
    return sum(1 for d, k in state.merchant_log if d == day(state) and k == key)


def buy(state, key: str) -> str | None:
    """Buy one of today's offers; returns a refusal reason, or None when it worked."""
    visit = today(state)
    if visit is None or key not in visit["stock"]:
        return "Not for sale today."
    if bought_today(state, key):
        return "Sold out!"
    name, price, _ = OFFERS[key]
    if state.player_gold < price:
        return "Not enough gold!"
    state.player_gold -= price
    state.merchant_log.append([day(state), key])
    if key == "geodes":
        gems = state.inventory.setdefault("gems", {})
        gems["geode"] = gems.get("geode", 0) + 2
    elif key == "elixir":
        state.player_max_hp += 2
        state.player_hp = state.player_max_hp
    elif key in ("oil_crate", "bandage_pack"):
        supply = "lamp_oil" if key == "oil_crate" else "bandage"
        state.supplies[supply] = state.supplies.get(supply, 0) + 3
    elif key == "charm_pair":
        state.recall_charms += 2
    return None


def wanted_price(state) -> int:
    visit = today(state)
    return get_gem_raw_value(visit["wants"]) * WANTED_MULTIPLIER if visit else 0


def sell_wanted(state) -> int:
    """Sell one of the wanted gem; returns what it paid (0 if not possible)."""
    visit = today(state)
    gems = state.inventory.get("gems", {})
    if visit is None or gems.get(visit["wants"], 0) <= 0:
        return 0
    if bought_today(state, "sell") >= WANTED_PER_DAY:
        return 0
    gems[visit["wants"]] -= 1
    if gems[visit["wants"]] == 0:
        del gems[visit["wants"]]
    price = wanted_price(state)
    state.merchant_log.append([day(state), "sell"])
    state.player_gold += price
    state.lifetime_earnings += price
    return price
