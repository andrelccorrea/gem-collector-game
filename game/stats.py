"""Lifetime statistics: counters kept by the simulation, totals kept in the profile.

The run's counters live in ``state.stats`` (not saved); the game scene adds what grew
since the last time to the profile's totals now and then, so totals survive any run.
"""

STATS = {  # key -> label, in display order
    "gems_found": "Gems found",
    "tiles_dug": "Tiles dug or panned",
    "creatures_defeated": "Creatures defeated",
    "steps": "Steps walked",
    "damage_taken": "Damage taken",
    "contracts": "Contracts delivered",
    "landmarks": "Landmarks visited",
}


def bump(state, key: str, amount: int = 1) -> None:
    state.stats[key] = state.stats.get(key, 0) + amount
