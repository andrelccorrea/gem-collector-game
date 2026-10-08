"""Progress kept between runs: reputation earned by finishing runs, spent on perks.

Stored in profile.json next to the save (persistence.data_dir()), independent of any
single run. Perks apply to new normal and hardcore runs; daily runs ignore them so
everyone plays the same day on equal terms.
"""

import json
import os

from game import persistence
from game.objects.registry import PERKS, REPUTATION

PROFILE_NAME = "profile.json"


def _path() -> str:
    return os.path.join(persistence.data_dir(), PROFILE_NAME)


def new_profile() -> dict:
    return {"reputation": 0, "perks": {key: 0 for key in PERKS}, "runs_finished": 0}


def load_profile() -> dict:
    profile = new_profile()
    try:
        with open(_path()) as f:
            data = json.load(f)
        if isinstance(data, dict):
            profile["reputation"] = int(data.get("reputation", 0))
            profile["runs_finished"] = int(data.get("runs_finished", 0))
            for key in PERKS:
                profile["perks"][key] = int(data.get("perks", {}).get(key, 0))
    except (OSError, ValueError, TypeError, AttributeError):
        pass
    return profile


def save_profile(profile: dict) -> None:
    try:
        os.makedirs(persistence.data_dir(), exist_ok=True)
        with open(_path(), "w") as f:
            json.dump(profile, f, indent=2)
    except OSError:
        pass


def award_reputation(earnings: int, outcome: str) -> int:
    """Credit reputation for a finished run (outcome: win, hardcore_death, daily)."""
    gained = earnings // REPUTATION[f"{outcome}_divisor"]
    profile = load_profile()
    profile["reputation"] += gained
    profile["runs_finished"] += 1
    save_profile(profile)
    return gained


def next_perk_cost(profile: dict, key: str) -> int | None:
    """Reputation price of the next level of a perk, or None when it is maxed."""
    level = profile["perks"][key]
    costs = PERKS[key]["costs"]
    return costs[level] if level < len(costs) else None


def buy_perk(key: str) -> bool:
    profile = load_profile()
    cost = next_perk_cost(profile, key)
    if cost is None or profile["reputation"] < cost:
        return False
    profile["reputation"] -= cost
    profile["perks"][key] += 1
    save_profile(profile)
    return True


def apply_perks(state, profile: dict) -> None:
    """Give a fresh run the bonuses of the perks owned."""
    bonus = {key: PERKS[key]["per_level"] * level for key, level in profile["perks"].items()}
    state.player_gold += bonus["start_gold"]
    state.player_max_hp += bonus["max_hp"]
    state.player_hp = state.player_max_hp
    state.bag_bonus = bonus["bag_bonus"]
    state.lantern_bonus = bonus["lantern_bonus"]
    from game.lantern import lantern_capacity

    state.lantern_fuel = lantern_capacity(state)
