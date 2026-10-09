"""World map: the whole world shrunk to the screen, showing only what was explored.

Each screen cell stands for a block of tiles and takes the look of the block's most
telling explored tile; unexplored blocks stay blank. Markers show the player, the town,
landmarks already visited and a dropped bag. Game time is frozen while it is open.
"""

from game.constants import (
    COLOR_MENU_DIMMED,
    COLOR_MENU_TITLE,
    MAP_HEIGHT,
    MAP_WIDTH,
    PLAYER_CHAR,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
)
from game.input import Action, InputState
from game.input import hint as hint_of
from game.landmarks import landmarks
from game.theme import TILE_APPEARANCE, dim
from game.ui import clear_screen, write_str

# Which tile type speaks for a block (most telling first); anything else is plain ground.
_PRIORITY = ["shop", "lapidary", "save", "rich_ore", "ore", "stream", "lake", "deep",
             "shallow", "cave_wall", "tree", "rock"]  # fmt: skip
_MARK_PLAYER = ((255, 255, 255), (60, 60, 160))
_MARK = ((255, 220, 120), (0, 0, 0))


def _block_look(meta, x0, x1, y0, y1):
    best, rank = None, len(_PRIORITY) + 1
    for y in range(y0, y1):
        for x in range(x0, x1):
            tile = meta.get((x, y))
            if tile is None or tile["visibility"] == "unseen":
                continue
            r = _PRIORITY.index(tile["type"]) if tile["type"] in _PRIORITY else len(_PRIORITY)
            if r < rank:
                best, rank = tile["type"], r
    if best is None:
        return None
    char, colors = TILE_APPEARANCE[best]
    return (char if char.strip() else "·"), dim(colors) if best not in _PRIORITY[:3] else colors


_cache: dict = {}


def _terrain(state, meta, width: int, height: int) -> dict:
    """{(sx, sy): (char, colors)} for explored blocks; recomputed only when the explored
    area may have changed (the fog key moves with the player and the light)."""
    key = (id(state.world_tiles), state.fog_key, width, height)
    if _cache.get("key") != key:
        cells = {}
        for sy in range(1, height):
            y0 = (sy - 1) * MAP_HEIGHT // (height - 1)
            y1 = max(y0 + 1, sy * MAP_HEIGHT // (height - 1))
            for sx in range(width):
                x0 = sx * MAP_WIDTH // width
                x1 = max(x0 + 1, (sx + 1) * MAP_WIDTH // width)
                look = _block_look(meta, x0, x1, y0, y1)
                if look is not None:
                    cells[(sx, sy)] = look
        _cache.update(key=key, cells=cells)
    return _cache["cells"]


def render_map(renderer, state) -> None:
    clear_screen(renderer, ((0, 0, 0), (0, 0, 0)))
    width, height = renderer.width, renderer.height - 2
    title = "  WORLD MAP  "
    write_str(renderer, 0, (width - len(title)) // 2, title, COLOR_MENU_TITLE)
    if state.world_tiles is None:
        return
    meta = state.world_tiles.meta

    def cell(wx, wy):  # world tile -> screen cell
        return wx * width // MAP_WIDTH, 1 + wy * (height - 1) // MAP_HEIGHT

    for (sx, sy), look in _terrain(state, meta, width, height).items():
        renderer.set_cell(sx, sy, *look)

    for (lx, ly), _kind in landmarks(state).items():
        if (lx, ly) in state.visited_landmarks:
            renderer.set_cell(*cell(lx, ly), "*", _MARK)
    if state.dropped_bag is not None:
        renderer.set_cell(*cell(state.dropped_bag["x"], state.dropped_bag["y"]), "&", _MARK)
    renderer.set_cell(*cell(TOWN_CENTER_X, TOWN_CENTER_Y), "T", _MARK)
    renderer.set_cell(*cell(state.player_x, state.player_y), PLAYER_CHAR, _MARK_PLAYER)

    legend = (f"{PLAYER_CHAR} you   T town   * landmark visited   & your bag   "
              f"[{hint_of(Action.MAP)}/{hint_of(Action.CANCEL)}] Close")  # fmt: skip
    write_str(renderer, renderer.height - 1, max(0, (width - len(legend)) // 2), legend[:width],
              COLOR_MENU_DIMMED)  # fmt: skip


def update_map(inp: InputState, state) -> None:
    if Action.MAP in inp.pressed or Action.CANCEL in inp.pressed:
        state.active_scene = "game"
