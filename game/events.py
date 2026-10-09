"""World events (finds, damage, healing) for frontends that animate them.

The simulation appends events to ``state.events``; a frontend takes them once per frame
(``take_events``) and shows them, e.g. as text floating up from the tile. Events never
feed back into the simulation and are not saved. The HUD message stays the text record.
"""

from typing import NamedTuple

from game.objects.registry import GEM_CATALOG

GAIN_COLOR = (255, 220, 90)
LOSS_COLOR = (255, 90, 90)
HEAL_COLOR = (110, 230, 110)
DULL_COLOR = (170, 170, 170)

# Event kinds: what happened, for frontends that react per kind (e.g. a sound each).
FIND, MISS, LOOT, FULL, HIT, HURT, HEAL = "find", "miss", "loot", "full", "hit", "hurt", "heal"
ACHIEVE = "achievement"
COIN, DENIED = "coin", "denied"  # a purchase or sale went through / was refused
# Frontends that never take events (terminal, balance bot) keep only the latest ones.
MAX_PENDING = 32


class Event(NamedTuple):
    """An event of ``kind`` at world tile (x, y): ``text`` next to sprite ``icon`` (None
    = no icon) tinted ``color`` (None = the icon's own colors), in ``text_color``."""

    x: int
    y: int
    kind: str
    text: str
    text_color: tuple
    icon: str | None = None
    color: tuple | None = None


def emit(state, kind: str, text: str, text_color: tuple, icon=None, color=None, at=None) -> None:
    """Record an event at tile ``at`` (default: the player's tile)."""
    x, y = at if at is not None else (state.player_x, state.player_y)
    state.events.append(Event(x, y, kind, text, text_color, icon, color))
    del state.events[:-MAX_PENDING]


def emit_gem(state, gem_name: str) -> None:
    """A gem (or geode) went into the bag."""
    gem = GEM_CATALOG.get(gem_name)
    color = gem.color[0] if gem is not None else None
    from game.gems import gem_sprite

    label = f"+{gem_name.replace('_', ' ').title()}"
    emit(state, FIND, label, GAIN_COLOR, gem_sprite(gem_name), color)


def take_events(state) -> list:
    """The events since the last call (oldest first)."""
    events, state.events = state.events, []
    return events
