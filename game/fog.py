"""Fog of war: tiles in the lantern's light and in line of sight are visible; tiles
seen before stay "explored"."""

from game.constants import MAP_HEIGHT, MAP_WIDTH, OPAQUE_TILE_TYPES
from game.lantern import light_radius


def _line(x0: int, y0: int, x1: int, y1: int):
    """Tiles strictly between (x0, y0) and (x1, y1) on a Bresenham line."""
    if (x0, y0) == (x1, y1):
        return
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x1 > x0 else -1), (1 if y1 > y0 else -1)
    err = dx + dy
    x, y = x0, y0
    while True:
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
        if (x, y) == (x1, y1):
            return
        yield x, y


def _in_sight(meta, px: int, py: int, tx: int, ty: int) -> bool:
    """No opaque tile (trees, rock, cave walls) between the player and the target."""
    for pos in _line(px, py, tx, ty):
        if meta.get(pos, {}).get("type") in OPAQUE_TILE_TYPES:
            return False
    return True


def update_fog(state) -> None:
    px, py = state.player_x, state.player_y
    radius = light_radius(state)
    # Visibility only changes when the player moves or the light changes.
    key = (px, py, radius)
    if key == state.fog_key:
        return
    state.fog_key = key

    meta = state.world_tiles.meta
    for coord in state.visible_tiles:
        if coord in meta:
            meta[coord]["visibility"] = "explored"
    state.visible_tiles = set()

    x_min = max(0, px - radius)
    x_max = min(MAP_WIDTH - 1, px + radius)
    y_min = max(0, py - radius)
    y_max = min(MAP_HEIGHT - 1, py + radius)
    for ty in range(y_min, y_max + 1):
        for tx in range(x_min, x_max + 1):
            if (tx, ty) in meta and _in_sight(meta, px, py, tx, ty):
                meta[(tx, ty)]["visibility"] = "visible"
                state.visible_tiles.add((tx, ty))
