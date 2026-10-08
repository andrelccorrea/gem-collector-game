import math

from game import death, persistence
from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
)
from game.input import Action, InputState
from game.ui import clear_screen, write_str

# (id, label); "continue" is only selectable when a save exists
MENU_ITEMS = [
    ("new", "New Game"),
    ("new_hardcore", "New Game (Hardcore)"),
    ("daily", "Daily Run"),
    ("continue", "Continue"),
    ("leaderboard", "Leaderboard"),
]


def _menu_ids() -> list:
    return [item_id for item_id, _ in MENU_ITEMS]


def _enabled(item_id: str, save_exists: bool) -> bool:
    return item_id != "continue" or save_exists


def render_menu(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2

    title = "=== GEM COLLECTOR ==="
    write_str(renderer, mid_y - 5, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)

    subtitle = "A Terminal Prospecting Adventure"
    write_str(renderer, mid_y - 4, mid_x - len(subtitle) // 2, subtitle, COLOR_MENU_NORMAL)

    save_exists = persistence.has_save()
    for i, (item_id, item) in enumerate(MENU_ITEMS):
        row = mid_y - 2 + i
        label = f"  {item}  "
        col = mid_x - len(label) // 2

        if not _enabled(item_id, save_exists):
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

    step = (Action.MOVE_DOWN in pressed) - (Action.MOVE_UP in pressed)
    if step:
        # Move to the next selectable entry in that direction, if any.
        ids = _menu_ids()
        i = state.menu_cursor + step
        while 0 <= i < len(ids) and not _enabled(ids[i], save_exists):
            i += step
        if 0 <= i < len(ids):
            state.menu_cursor = i
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
    choice = _menu_ids()[state.menu_cursor]

    if choice in ("new", "new_hardcore"):
        import random

        from game.simulation import new_run

        run = new_run(random.randint(1, 999999))
        run.hardcore = choice == "new_hardcore"
        _replace_state(state, run)

    elif choice == "daily":
        from datetime import date

        from game.daily import start_daily

        _replace_state(state, start_daily(date.today()))

    elif choice == "continue" and save_exists:
        try:
            loaded = persistence.load_game()
        except persistence.SaveLoadError as e:
            state.menu_notice = str(e)
            state.menu_cursor = 0
            loaded = None
        if loaded is not None:
            _replace_state(state, loaded)
            state.active_scene = "game"

    elif choice == "leaderboard":
        state.active_scene = "leaderboard"


def render_death_screen(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    msg = "  YOU DIED  " if state.hardcore else "  YOU FAINTED  "
    write_str(renderer, mid_y - 3, mid_x - len(msg) // 2, msg, COLOR_MENU_TITLE)
    sub = f"Lifetime Earnings: ${state.lifetime_earnings}"
    write_str(renderer, mid_y - 1, mid_x - len(sub) // 2, sub, COLOR_MENU_NORMAL)
    if state.hardcore:
        lines = ["Hardcore run over: its save is gone.", "Press Enter to return to menu"]
    else:
        lines = [
            "Your bag stays where you fell (marked & on the map).",
            f"Press Enter to revive in town for ${death.revive_fee(state)}",
        ]
    for i, line in enumerate(lines):
        write_str(renderer, mid_y + 1 + i, mid_x - len(line) // 2, line, COLOR_MENU_DIMMED)


def update_death_screen(inp: InputState, state) -> None:
    if Action.CONFIRM not in inp.pressed:
        return
    if state.hardcore:
        persistence.delete_save()
        state.active_scene = "menu"
        state.menu_cursor = 0
    else:
        death.revive_in_town(state)


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


def render_daily_end(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    title = f"  DAILY RUN {state.daily} - TIME'S UP  "
    write_str(renderer, 3, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)
    result = f"You earned ${state.lifetime_earnings}"
    write_str(renderer, 5, mid_x - len(result) // 2, result, COLOR_MENU_NORMAL)
    scores = persistence.load_daily(state.daily)
    if state.lifetime_earnings not in scores:
        scores = sorted(scores + [state.lifetime_earnings], reverse=True)
    write_str(renderer, 7, mid_x - 10, "Today's best:", COLOR_MENU_NORMAL)
    for i, score in enumerate(scores[:5]):
        mark = "  <- you" if score == state.lifetime_earnings else ""
        line = f"  #{i + 1}  ${score}{mark}"
        write_str(renderer, 8 + i, mid_x - 10, line, COLOR_MENU_NORMAL)
    hint = "Enter: Back to Menu"
    write_str(renderer, renderer.height - 2, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_daily_end(inp: InputState, state) -> None:
    if Action.CONFIRM in inp.pressed:
        persistence.save_daily_entry(state.daily, state.lifetime_earnings)
        state.active_scene = "menu"
        state.menu_cursor = 0


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

    from datetime import date

    today = date.today().isoformat()
    daily = persistence.load_daily(today)
    if daily:
        line = f"Today's daily best: ${daily[0]}  ({len(daily)} runs)"
        write_str(renderer, 18, mid_x - len(line) // 2, line, COLOR_MENU_TITLE)

    hint = "Esc: Back to Menu"
    write_str(renderer, renderer.height - 2, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_leaderboard(inp: InputState, state) -> None:
    if Action.CANCEL in inp.pressed:
        state.active_scene = "menu"
