"""Save point: confirm and write the save slot."""

import math

from game.constants import (
    COLOR_MENU_NORMAL,
    COLOR_MENU_TITLE,
)
from game.input import Action, InputState
from game.player import set_hud_message
from game.ui import clear_screen, write_str


def render_save_point(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    write_str(renderer, mid_y - 2, mid_x - 8, "  SAVE POINT  ", COLOR_MENU_TITLE)
    write_str(
        renderer,
        mid_y,
        mid_x - 16,
        "Save your progress? [Enter] Yes  [Esc] Cancel",
        COLOR_MENU_NORMAL,
    )


def update_save_point(inp: InputState, state) -> None:
    """Handle save point input."""
    if Action.CANCEL in inp.pressed:
        state.active_scene = "game"
    elif Action.CONFIRM in inp.pressed:
        from game import persistence

        error = persistence.save_game(state)
        set_hud_message(state, error or "Game Saved!", 3.0)
        state.active_scene = "game"
