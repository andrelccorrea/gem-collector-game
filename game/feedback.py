"""Shared buy/sell feedback for town screens: a message plus a cue the frontend can
sound (a refusal tone or a coin chime)."""

from game.events import COIN, DENIED, DULL_COLOR, GAIN_COLOR, emit
from game.player import set_hud_message


def refuse(state, message: str) -> None:
    set_hud_message(state, message, 1.5)
    emit(state, DENIED, "", DULL_COLOR)


def chime(state) -> None:
    """A purchase or sale went through."""
    emit(state, COIN, "", GAIN_COLOR)
