import math
import os

from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_NORMAL,
    COLOR_MENU_SELECTED,
    COLOR_MENU_TITLE,
)
from game.input import Action, InputState

MENU_ITEMS = ["New Game", "Continue", "Leaderboard"]


def _write_str(renderer, y: int, x: int, text: str, color_pair: tuple) -> None:
    max_y = math.floor(renderer.height) - 1
    max_x = math.floor(renderer.width) - 1
    if y < 0 or y >= max_y:
        return
    for i, ch in enumerate(text):
        cx = x + i
        if cx < 0 or cx >= max_x:
            continue
        renderer.set_cell(cx, y, ch, color_pair)


def _clear_screen(renderer, color_pair=None) -> None:
    if color_pair is None:
        color_pair = ((0, 0, 0), (0, 0, 0))
    renderer.clear(color_pair)


def render_menu(renderer, state) -> None:
    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))

    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2

    title = "=== GEM COLLECTOR ==="
    _write_str(renderer, mid_y - 5, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)

    subtitle = "A Terminal Prospecting Adventure"
    _write_str(renderer, mid_y - 4, mid_x - len(subtitle) // 2, subtitle, COLOR_MENU_NORMAL)

    save_exists = os.path.exists("save.json")
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

        _write_str(renderer, row, col, label, cp)

    hint = "Arrow Keys: Navigate  |  Enter: Select  |  Esc: Quit"
    _write_str(renderer, mid_y + 7, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_menu(inp: InputState, state) -> None:
    save_exists = os.path.exists("save.json")
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
        _select_menu_item(state, save_exists)
    elif Action.CANCEL in pressed:
        state.quit_requested = True


def _select_menu_item(state, save_exists: bool) -> None:
    from game import persistence
    from game import world as world_module

    if state.menu_cursor == 0:  # New Game
        import random

        from game import fog as fog_module

        state.seed = random.randint(1, 999999)
        state.world_tiles, state.world_gems = world_module.generate_world(state.seed)
        if state.world_tiles.start_pos is not None:
            state.player_x, state.player_y = state.world_tiles.start_pos
        else:
            from game.constants import TOWN_CENTER_X, TOWN_CENTER_Y

            state.player_x = TOWN_CENTER_X
            state.player_y = TOWN_CENTER_Y
        state.player_hp = state.player_max_hp
        state.player_gold = 50
        state.lifetime_earnings = 0
        state.equipped_tool = "shovel"
        state.inventory = {
            "gems": {},
            "tools": {"shovel": {"level": 1}},
            "loot": {},
        }
        state.depleted_tiles = set()
        state.visible_tiles = set()
        state.has_won = False
        fog_module.update_fog(state)
        state.active_scene = "game"

    elif state.menu_cursor == 1 and save_exists:  # Continue
        loaded = persistence.load_game()
        if loaded is not None:
            # Copy loaded state fields into current state
            for key, val in vars(loaded).items():
                setattr(state, key, val)
            state.active_scene = "game"

    elif state.menu_cursor == 2:  # Leaderboard
        state.active_scene = "leaderboard"


def render_death_screen(renderer, state) -> None:
    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    msg = "  YOU DIED  "
    _write_str(renderer, mid_y - 2, mid_x - len(msg) // 2, msg, COLOR_MENU_TITLE)
    sub = f"Lifetime Earnings: ${state.lifetime_earnings}"
    _write_str(renderer, mid_y, mid_x - len(sub) // 2, sub, COLOR_MENU_NORMAL)
    hint = "Press Enter to return to menu"
    _write_str(renderer, mid_y + 2, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_death_screen(inp: InputState, state) -> None:
    if Action.CONFIRM in inp.pressed:
        state.active_scene = "menu"
        state.menu_cursor = 0


def render_win_screen(renderer, state) -> None:
    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    mid_y = math.floor(renderer.height) // 2
    title = "  HALL OF FAME!  "
    _write_str(renderer, mid_y - 3, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)
    msg = f"You earned ${state.lifetime_earnings} as a prospector!"
    _write_str(renderer, mid_y - 1, mid_x - len(msg) // 2, msg, COLOR_MENU_NORMAL)
    hint = "Press Enter to continue playing"
    _write_str(renderer, mid_y + 1, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED)


def update_win_screen(inp: InputState, state) -> None:
    if Action.CONFIRM in inp.pressed:
        from game import persistence

        persistence.save_leaderboard_entry(state.lifetime_earnings)
        state.active_scene = "game"


def render_leaderboard(renderer, state) -> None:
    from game import persistence

    _clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    mid_x = math.floor(renderer.width) // 2
    title = "  HALL OF FAME - TOP PROSPECTORS  "
    _write_str(renderer, 3, mid_x - len(title) // 2, title, COLOR_MENU_TITLE)

    entries = persistence.load_leaderboard()
    if not entries:
        msg = "No entries yet. Earn $10,000 to make history!"
        _write_str(renderer, 8, mid_x - len(msg) // 2, msg, COLOR_MENU_DIMMED)
    else:
        _write_str(
            renderer, 6, mid_x - 20, f"{'Rank':<6}{'Earnings':>12}{'Date':>15}", COLOR_MENU_NORMAL
        )
        for i, entry in enumerate(entries[:10]):
            row = 7 + i
            line = f"  #{i + 1:<4}${entry.get('earnings', 0):>10}   {entry.get('date', 'N/A'):>12}"
            _write_str(renderer, row, mid_x - 20, line, COLOR_MENU_NORMAL)

    hint = "Esc: Back to Menu"
    _write_str(
        renderer, math.floor(renderer.height) - 3, mid_x - len(hint) // 2, hint, COLOR_MENU_DIMMED
    )


def update_leaderboard(inp: InputState, state) -> None:
    if Action.CANCEL in inp.pressed:
        state.active_scene = "menu"
