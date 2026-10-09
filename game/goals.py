"""Starter goals: one at a time, each teaching a part of the game through play.

The chain is kept in the profile, so it runs once per player. Finishing a goal pays a
little gold (an early win) and announces the next one; the map shows the current goal.
"""

from game.events import COIN, GAIN_COLOR, emit
from game.player import set_hud_message

# (text, reward in gold, condition)
GOALS = [
    ("Dig up your first gem", 10, lambda s: s.stats.get("gems_found", 0) > 0),
    ("Sell a gem at the Shop (S)", 15, lambda s: s.lifetime_earnings > 0),
    ("Buy a new tool at the Shop", 20, lambda s: len(s.inventory.get("tools", {})) >= 2),
    ("Cut a gem at the Lapidary (L)", 25,
     lambda s: any(k.endswith("_polished") for k in s.inventory.get("gems", {}))),
    ("Stand still near an animal, then pet it", 20, lambda s: s.stats.get("pets", 0) > 0),
    ("Find a landmark out in the wild", 20, lambda s: bool(s.visited_landmarks)),
    ("Deliver a contract (Shop, Contracts tab)", 30, lambda s: bool(s.contracts_done)),
    ("Earn $1,000 in one run", 50, lambda s: s.lifetime_earnings >= 1000),
]  # fmt: skip


def current(state):
    """Text of the goal to work on, or None when the chain is done."""
    return GOALS[state.goal][0] if state.goal < len(GOALS) else None


def check(state) -> bool:
    """Complete the current goal if met (pays and announces the next); True if it did."""
    if state.goal >= len(GOALS):
        return False
    text, reward, met = GOALS[state.goal]
    if not met(state):
        return False
    state.goal += 1
    state.player_gold += reward
    following = current(state)
    after = f" Next: {following}." if following else " That's all the starter goals!"
    set_hud_message(state, f"Goal done: {text} (+${reward}).{after}", 5.0)
    emit(state, COIN, "", GAIN_COLOR)
    return True
