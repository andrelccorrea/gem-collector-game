import math

from game import persistence
from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
)
from game.input import Action, InputState
from game.ui import clear_screen, write_str

MENU_ITEMS = ["New Game", "Continue", "Leaderboard"]


def render_menu(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2

    title = "=== GEM COLLECTOR ==="
    write_str(renderer, mid_y - 5, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)

    subtitle = "A Terminal Prospecting Adventure"
    write_str(renderer, mid_y - 4, mid_x - len(subtitle) // 2, subtitle, COLOR_MENU_NORMAL)

    save_exists = persistence.has_save()
    for i, item in enumerate(MENU_ITEMS):
        row = mid_y - 1 + i * 2
        label = f"  {item}  "
        col = mid_x - len(label) // 2

        if i == 1 and not save_exists:
            cp = COLOR_MENU_DIMMED
        elif i == state.menu_cursor:
            cp = COLOR_MENU_SELECTED
        else:
            cp = COLOR_MENU_NORMAL

        write_str(renderer, row, col, label, cp)

    if state.menu_notice:
        notice = state.menu_notice[: math.floor(renderer.width) - 2]
        write_str(renderer, mid_y + 5, mid_x - len(notice) // 2, notice, COLOR_MENU_TITLE)

    hint = "Arrow Keys: Navigate  |  Enter: Select  |  Esc: Quit"
    write_str(renderer, mid_y + 7, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_menu(inp: InputState, state) -> None:
    save_exists = persistence.has_save()
    pressed = inp.pressed

    if Action.MOVE_UP in pressed and state.menu_cursor > 0:
        state.menu_cursor -= 1
        if state.menu_cursor == 1 and not save_exists:
            state.menu_cursor = 0
    elif Action.MOVE_DOWN in pressed and state.menu_cursor < len(MENU_ITEMS) - 1:
        state.menu_cursor += 1
        if state.menu_cursor == 1 and not save_exists:
            state.menu_cursor = 2
    elif Action.CONFIRM in pressed:
        state.menu_notice = ""
        _select_menu_item(state, save_exists)
    elif Action.CANCEL in pressed:
        state.quit_requested = True


def _replace_state(state, new_state) -> None:
    """Swap every field of ``state`` for those of ``new_state`` (nothing carries over)."""
    for key, val in vars(new_state).items():
        setattr(state, key, val)


def _select_menu_item(state, save_exists: bool) -> None:

    if state.menu_cursor == 0:  # New Game
        import random

        from game.simulation import new_run

        _replace_state(state, new_run(random.randint(1, 999999)))

    elif state.menu_cursor == 1 and save_exists:  # Continue
        try:
            loaded = persistence.load_game()
        except persistence.SaveLoadError as e:
            state.menu_notice = str(e)
            state.menu_cursor = 0
            loaded = None
        if loaded is not None:
            _replace_state(state, loaded)
            state.active_scene = "game"

    elif state.menu_cursor == 2:  # Leaderboard
        state.active_scene = "leaderboard"


def render_death_screen(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    msg = "  YOU DIED  "
    write_str(renderer, mid_y - 2, mid_x - len(msg) // 2, msg, COLOR_MENU_TITLE)
    sub = f"Lifetime Earnings: ${state.lifetime_earnings}"
    write_str(renderer, mid_y, mid_x - len(sub) // 2, sub, COLOR_MENU_NORMAL)
    hint = "Press Enter to return to menu"
    write_str(renderer, mid_y + 2, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_death_screen(inp: InputState, state) -> None:
    if Action.CONFIRM in inp.pressed:
        state.active_scene = "menu"
        state.menu_cursor = 0


def render_win_screen(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    title = "  HALL OF FAME!  "
    write_str(renderer, mid_y - 3, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)
    msg = f"You earned ${state.lifetime_earnings} as a prospector!"
    write_str(renderer, mid_y - 1, mid_x - len(msg) // 2, msg, COLOR_MENU_NORMAL)
    hint = "Press Enter to continue playing"
    write_str(renderer, mid_y + 1, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_win_screen(inp: InputState, state) -> None:
    if Action.CONFIRM in inp.pressed:
        persistence.save_leaderboard_entry(state.lifetime_earnings)
        state.active_scene = "game"


def render_leaderboard(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    title = "  HALL OF FAME - TOP PROSPECTORS  "
    write_str(renderer, 3, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)

    entries = persistence.load_leaderboard()
    if not entries:
        msg = "No entries yet. Earn $10,000 to make history!"
        write_str(renderer, 8, mid_x - len(msg) // 2, msg, COLOR_MENU_DIMMED)
    else:
        write_str(
            renderer, 6, mid_x - 20, f"{'Rank':<6}{'Earnings':>12}{'Date':>15}", COLOR_MENU_NORMAL
        )
        for i, entry in enumerate(entries[:10]):
            row = 7 + i
            line = f"  #{i + 1:<4}${entry.get('earnings', 0):>10}   {entry.get('date', 'N/A'):>12}"
            write_str(renderer, row, mid_x - 20, line, COLOR_MENU_NORMAL)

    hint = "Esc: Back to Menu"
    write_str(
        renderer, math.floor(renderer.height) - 3, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED
    )


def update_leaderboard(inp: InputState, state) -> None:
    if Action.CANCEL in inp.pressed:
        state.active_scene = "menu"
