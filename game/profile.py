"""Progress kept between runs: reputation earned by finishing runs, spent on perks.

Stored in profile.json next to the save (persistence.data_dir()), independent of any
single run. Perks apply to new normal and hardcore runs; daily runs ignore them so
everyone plays the same day on equal terms.
"""

import json
import os

from game import persistence
from game.objects.registry import DEFAULT_OUTFIT, OUTFITS, PERKS, REPUTATION

PROFILE_NAME = "profile.json"


def _path() -> str:
    return os.path.join(persistence.data_dir(), PROFILE_NAME)


# How many rewarded run ids to remember (enough to cover any save a player could reload).
REWARDED_RUNS_KEPT = 200


def new_profile() -> dict:
    return {
        "reputation": 0,
        "perks": {key: 0 for key in PERKS},
        "runs_finished": 0,
        "rewarded_runs": [],
        "tips": [],
        "achievements": [],
        "outfits": [DEFAULT_OUTFIT],
        "outfit": DEFAULT_OUTFIT,
        "bestiary": {},
        "stats": {},
        "friends": [],
        "goal": 0,
    }


def load_profile() -> dict:
    """The saved profile; a fresh one if none exists. A damaged file is moved aside to
    profile.json.bak (so it can be recovered by hand) rather than silently replaced."""
    profile = new_profile()
    path = _path()
    if not os.path.isfile(path):
        return profile
    try:
        with open(path) as f:
            data = json.load(f)
        profile["reputation"] = int(data["reputation"])
        profile["runs_finished"] = int(data.get("runs_finished", 0))
        profile["rewarded_runs"] = [str(r) for r in data.get("rewarded_runs", [])]
        profile["tips"] = [str(t) for t in data.get("tips", [])]
        profile["achievements"] = [str(a) for a in data.get("achievements", [])]
        owned = [str(o) for o in data.get("outfits", []) if o in OUTFITS]
        profile["outfits"] = sorted(set(owned) | {DEFAULT_OUTFIT})
        profile["bestiary"] = {str(k): str(v) for k, v in data.get("bestiary", {}).items()}
        profile["stats"] = {str(k): int(v) for k, v in data.get("stats", {}).items()}
        profile["friends"] = [str(f) for f in data.get("friends", [])]
        profile["goal"] = int(data.get("goal", 0))
        worn = data.get("outfit", DEFAULT_OUTFIT)
        profile["outfit"] = worn if worn in profile["outfits"] else DEFAULT_OUTFIT
        for key in PERKS:
            profile["perks"][key] = int(data.get("perks", {}).get(key, 0))
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        try:
            os.replace(path, path + ".bak")
        except OSError:
            pass
        return new_profile()
    return profile


def save_profile(profile: dict) -> None:
    """Write atomically (tmp file + rename): a kill mid-write never truncates it."""
    path = _path()
    tmp = path + ".tmp"
    try:
        os.makedirs(persistence.data_dir(), exist_ok=True)
        with open(tmp, "w") as f:
            json.dump(profile, f, indent=2)
        os.replace(tmp, path)
    except OSError:
        pass


def award_reputation(earnings: int, outcome: str, run_id: str) -> int:
    """Credit reputation for a finished run (outcome: win, hardcore_death, daily).

    Each run pays out once: reloading a save from before the ending pays nothing more.
    """
    profile = load_profile()
    if run_id and run_id in profile["rewarded_runs"]:
        return 0
    gained = earnings // REPUTATION[f"{outcome}_divisor"]
    profile["reputation"] += gained
    profile["runs_finished"] += 1
    if run_id:
        profile["rewarded_runs"] = (profile["rewarded_runs"] + [run_id])[-REWARDED_RUNS_KEPT:]
    save_profile(profile)
    return gained


def reputation_preview(earnings: int, outcome: str, run_id: str) -> int:
    """What award_reputation would pay right now (0 if this run was already rewarded)."""
    if run_id and run_id in load_profile()["rewarded_runs"]:
        return 0
    return earnings // REPUTATION[f"{outcome}_divisor"]


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


def remember_tips(tips) -> None:
    """Add these first-time tips to the ones the profile has already shown."""
    profile = load_profile()
    known = set(profile["tips"])
    if not set(tips) <= known:
        profile["tips"] = sorted(known | set(tips))
        save_profile(profile)


def add_stats(deltas: dict) -> None:
    """Add a run's new counts to the lifetime totals."""
    if not any(deltas.values()):
        return
    profile = load_profile()
    for key, amount in deltas.items():
        profile["stats"][key] = profile["stats"].get(key, 0) + amount
    save_profile(profile)


def record_goal(index: int) -> None:
    profile = load_profile()
    profile["goal"] = max(profile["goal"], index)
    save_profile(profile)


def record_friends(names) -> None:
    """Add species the player befriended."""
    profile = load_profile()
    profile["friends"] = sorted(set(profile["friends"]) | set(names))
    save_profile(profile)


def record_sightings(names, where: str) -> None:
    """Add first sightings to the bestiary, with where and when they happened."""
    profile = load_profile()
    for name in names:
        profile["bestiary"].setdefault(name, where)
    save_profile(profile)


def wear_outfit(name: str) -> None:
    """Own (if new) and wear an outfit."""
    profile = load_profile()
    if name not in profile["outfits"]:
        profile["outfits"] = sorted(set(profile["outfits"]) | {name})
    profile["outfit"] = name
    save_profile(profile)


def unlock_achievements(ids, rewards: dict) -> int:
    """Record achievements (each pays its reputation reward once); returns reputation won."""
    profile = load_profile()
    new = [i for i in ids if i not in profile["achievements"]]
    if not new:
        return 0
    gained = sum(rewards[i] for i in new)
    profile["achievements"] += new
    profile["reputation"] += gained
    save_profile(profile)
    return gained


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
