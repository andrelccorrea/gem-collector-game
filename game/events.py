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
# Frontends that never take events (terminal, balance bot) keep only the latest ones.
MAX_PENDING = 32


class Event(NamedTuple):
    """``text`` shown at world tile (x, y), next to sprite ``icon`` (None = no icon)
    tinted ``color`` (None = the icon's own colors); ``text_color`` colors the text."""

    x: int
    y: int
    text: str
    text_color: tuple
    icon: str | None = None
    color: tuple | None = None


def emit(state, text: str, text_color: tuple, icon=None, color=None, at=None) -> None:
    """Record an event at tile ``at`` (default: the player's tile)."""
    x, y = at if at is not None else (state.player_x, state.player_y)
    state.events.append(Event(x, y, text, text_color, icon, color))
    del state.events[:-MAX_PENDING]


def emit_gem(state, gem_name: str) -> None:
    """A gem (or geode) went into the bag."""
    gem = GEM_CATALOG.get(gem_name)
    color = gem.color[0] if gem is not None else None
    emit(state, f"+{gem_name.replace('_', ' ').title()}", GAIN_COLOR, "gem", color)


def take_events(state) -> list:
    """The events since the last call (oldest first)."""
    events, state.events = state.events, []
    return events
