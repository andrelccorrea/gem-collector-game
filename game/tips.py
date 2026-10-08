"""First-time tips: each game mechanic is explained once, the first time it matters.

Tips are taught one at a time (never over another message, and at least TIP_GAP game
seconds apart). The simulation only records shown tips in ``state.tips_seen``; the game
scene keeps them in the profile so a tip never repeats across runs.
"""

from game.constants import TYPE_LAKE, TYPE_STREAM
from game.gems import bag_has_room
from game.geography import in_town
from game.input import Action, hint_label
from game.lantern import LOW_FUEL_SHARE, fuel_share
from game.player import set_hud_message
from game.tools import MINEABLE_TYPES

TIP_SECONDS = 6.0  # how long a tip stays in the message row
TIP_GAP = 8.0  # minimum game time between two tips
ENEMY_TIP_RANGE = 4  # tiles


def _tile(state) -> dict:
    return state.world_tiles.meta.get((state.player_x, state.player_y), {})


def _near_enemy(state) -> bool:
    px, py = state.player_x, state.player_y
    return any(max(abs(e.x - px), abs(e.y - py)) <= ENEMY_TIP_RANGE for e in state.enemies)


# (id, when it applies, text) in priority order: urgent ones first.
TIPS = [
    (
        "enemy",
        _near_enemy,
        lambda: (
            f"Tip: {hint_label(Action.ATTACK, 'Attack')} hits an enemy next to you. Town is safe."
        ),
    ),
    (
        "low_hp",
        lambda s: s.player_hp <= s.player_max_hp // 2,
        lambda: (
            "Tip: hurt? Rest in town, or buy Bandages at the Shop and use them with "
            + hint_label(Action.USE_ITEM, "Item")
            + "."
        ),
    ),
    (
        "bag_full",
        lambda s: not bag_has_room(s),
        lambda: "Tip: your bag is full. Sell at the Shop (S) in town.",
    ),
    (
        "low_light",
        lambda s: fuel_share(s) < LOW_FUEL_SHARE,
        lambda: "Tip: your lantern is running low. It refills in town.",
    ),
    (
        "gem",
        lambda s: (s.player_x, s.player_y) in s.world_gems,
        lambda: f"Tip: a gem! {hint_label(Action.USE, 'Use')} picks it up with the right tool.",
    ),
    (
        "dig",
        lambda s: _tile(s).get("type") in MINEABLE_TYPES and not _tile(s).get("depleted"),
        lambda: f"Tip: marked ground hides gems. {hint_label(Action.USE, 'Use')} digs it.",
    ),
    (
        "pan",
        lambda s: _tile(s).get("type") in (TYPE_STREAM, TYPE_LAKE),
        lambda: "Tip: streams and lakes can be panned with a Gold Pan from the Shop.",
    ),
    (
        "start",
        lambda s: s.game_time > 2.0 and in_town(s.player_x, s.player_y),
        lambda: "Tip: dig for gems outside town and sell them here. Earn $10000 to win!",
    ),
]


def check_tips(state) -> None:
    """Show the first unseen tip that applies, if the message row is free."""
    if state.world_tiles is None or (state.hud_message and state.hud_message_timer > 0):
        return
    if state.game_time - state.last_tip_time < TIP_GAP:
        return
    for tip_id, applies, text in TIPS:
        if tip_id not in state.tips_seen and applies(state):
            state.tips_seen.add(tip_id)
            state.last_tip_time = state.game_time
            set_hud_message(state, text(), TIP_SECONDS)
            return
