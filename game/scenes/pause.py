"""Pause: what Back/Esc opens during play. Nothing is lost from here: the main menu keeps
the run open and offers to resume it."""

from game.constants import COLOR_MENU_DIMMED, COLOR_MENU_TITLE
from game.input import Action, InputState
from game.input import hint as hint_of
from game.ui import clear_screen, render_list, write_str

PAUSE_ITEMS = [("resume", "Resume"), ("map", "World Map"), ("menu", "Main Menu")]


def render_pause(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    title = "=== PAUSED ==="
    write_str(renderer, 5, (renderer.width - len(title)) // 2, title, COLOR_MENU_TITLE)
    items = [{"label": f"  {label}", "enabled": True} for _, label in PAUSE_ITEMS]
    render_list(renderer, items, state.pause_cursor, top=8, bottom=8 + len(items))
    note = "Your run stays open in the main menu."
    write_str(renderer, 13, (renderer.width - len(note)) // 2, note, COLOR_MENU_DIMMED)
    hint = f"[{hint_of(Action.CONFIRM)}] Choose  [{hint_of(Action.CANCEL)}] Resume"
    write_str(renderer, renderer.height - 1, (renderer.width - len(hint)) // 2, hint,
              COLOR_MENU_DIMMED)  # fmt: skip


def update_pause(inp: InputState, state) -> None:
    pressed = inp.pressed
    if Action.CANCEL in pressed:
        state.active_scene = "game"
        return
    if Action.MOVE_UP in pressed:
        state.pause_cursor = (state.pause_cursor - 1) % len(PAUSE_ITEMS)
    if Action.MOVE_DOWN in pressed:
        state.pause_cursor = (state.pause_cursor + 1) % len(PAUSE_ITEMS)
    if Action.CONFIRM not in pressed:
        return
    choice = PAUSE_ITEMS[state.pause_cursor][0]
    state.pause_cursor = 0
    if choice == "resume":
        state.active_scene = "game"
    elif choice == "map":
        state.active_scene = "map"
    else:
        state.run_open = True
        state.menu_cursor = 0  # "Resume Run" is the first item
        state.active_scene = "menu"
