"""What happens when the player's HP reaches zero.

Normal runs: the player revives in town for a fee, and everything they carried stays
where they fell as a dropped bag they can walk back to and pick up. Dying again before
recovering it loses the old bag. Hardcore runs: death ends the run and erases its save.
"""

from game.gems import bag_capacity, bag_count
from game.lantern import lantern_capacity

# Share of the gold on hand charged to revive in town.
REVIVE_FEE_SHARE = 0.10


def revive_fee(state) -> int:
    return int(state.player_gold * REVIVE_FEE_SHARE)


def _carried(state) -> dict:
    return {
        "gems": dict(state.inventory["gems"]),
        "loot": dict(state.inventory["loot"]),
        "polished": {k: list(v) for k, v in state.polished_gem_values.items()},
    }


def drop_bag(state) -> None:
    """Leave everything carried at the player's position (replacing any older bag)."""
    if bag_count(state) == 0:
        return
    state.dropped_bag = {"x": state.player_x, "y": state.player_y, **_carried(state)}
    state.inventory["gems"] = {}
    state.inventory["loot"] = {}
    state.polished_gem_values = {}


def revive_in_town(state) -> None:
    """Normal-mode death: drop the bag, pay the fee, wake up healed in town."""
    drop_bag(state)
    state.player_gold -= revive_fee(state)
    state.player_hp = state.player_max_hp
    if state.world_tiles is not None and state.world_tiles.start_pos is not None:
        state.player_x, state.player_y = state.world_tiles.start_pos
    state.enemies = []
    state.lantern_fuel = lantern_capacity(state)
    state.move_cooldown = 0.0
    state.queued_move = None
    state.active_scene = "game"


def bag_here(state) -> bool:
    bag = state.dropped_bag
    return bag is not None and (bag["x"], bag["y"]) == (state.player_x, state.player_y)


def recover_bag(state) -> int:
    """Take back as much of the dropped bag as fits; returns how many items were taken."""
    bag = state.dropped_bag
    taken = 0
    for section in ("gems", "loot"):
        held = state.inventory[section]
        for key in list(bag[section]):
            while bag[section][key] > 0 and bag_count(state) < bag_capacity(state):
                bag[section][key] -= 1
                held[key] = held.get(key, 0) + 1
                if key in bag["polished"]:
                    prices = state.polished_gem_values.setdefault(key, [])
                    prices.append(bag["polished"][key].pop(0))
                    prices.sort(reverse=True)
                taken += 1
            if bag[section][key] == 0:
                del bag[section][key]
                bag["polished"].pop(key, None)
    if not bag["gems"] and not bag["loot"]:
        state.dropped_bag = None
    return taken
