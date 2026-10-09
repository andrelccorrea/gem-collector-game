from typing import NamedTuple

from game import daylight
from game.constants import (
    HUD_ROWS,
    MAP_HEIGHT,
    MAP_WIDTH,
    TYPE_DEEP,
    TYPE_LAKE,
    TYPE_SHALLOW,
    TYPE_STREAM,
    VIEW_HEIGHT,
    VIEW_WIDTH,
)
from game.daylight import mix, shade, tint_at
from game.decor import decoration
from game.landmarks import landmark_at
from game.objects.registry import GEM_CATALOG
from game.theme import UNSEEN_APPEARANCE, dim, tile_appearance

GROUND, OBJECT = "ground", "object"  # sprite layers (see Renderer.set_sprite)
EXPLORED_TINT = (128, 128, 128)

DROPPED_BAG_CHAR = "&"
DROPPED_BAG_COLOR = ((255, 120, 0), (40, 20, 0))


class View(NamedTuple):
    """A rectangle of the world: top-left tile (x, y) and size in tiles."""

    x: int
    y: int
    width: int
    height: int

    def contains(self, wx: int, wy: int) -> bool:
        return self.x <= wx < self.x + self.width and self.y <= wy < self.y + self.height


def _centered(center: int, size: int, limit: int) -> int:
    """Start of a span of ``size`` centered on ``center``, clamped to [0, limit)."""
    return max(0, min(center - size // 2, limit - size))


def update_camera(state) -> None:
    """Center the simulation view on the player, clamped to map bounds."""
    state.camera_x = _centered(state.player_x, VIEW_WIDTH, MAP_WIDTH)
    state.camera_y = _centered(state.player_y, VIEW_HEIGHT, MAP_HEIGHT)


def on_screen(state, x: int, y: int) -> bool:
    """Whether world tile (x, y) is inside the simulation view (where nothing spawns)."""
    return View(state.camera_x, state.camera_y, VIEW_WIDTH, VIEW_HEIGHT).contains(x, y)


def render_view(state, renderer) -> View:
    """The part of the world a frontend draws: the screen above the HUD, centered on the
    player and never larger than the simulation view (so it always lies inside it)."""
    width = max(1, min(renderer.width, VIEW_WIDTH))
    height = max(1, min(renderer.height - HUD_ROWS, VIEW_HEIGHT))
    return View(
        _centered(state.player_x, width, MAP_WIDTH),
        _centered(state.player_y, height, MAP_HEIGHT),
        width,
        height,
    )


_view_cache: dict = {}


def _view_cells(state, view: View) -> list:
    """[(sx, sy, char, color_pair, (sprite, tint) or None)] for the view's ground.

    Working out a tile's look (decoration, light, shore) is the costly part of a frame,
    so the result is kept until something it depends on changes: the view, the fog, the
    light (and, at night, where the player's glow is) or the tiles themselves.
    """
    now = daylight.phase(state)
    glow = (state.player_x, state.player_y) if now[0] == "night" else None
    key = (id(state.world_tiles), view, state.fog_key, now, glow, state.tiles_version)
    if _view_cache.get("key") == key:
        return _view_cache["cells"]
    meta = state.world_tiles.meta
    cells = []
    for sy in range(view.height):
        for sx in range(view.width):
            wx, wy = view.x + sx, view.y + sy
            tile = meta.get((wx, wy))
            if tile is None or tile.get("visibility") == "unseen":
                cells.append((sx, sy, *UNSEEN_APPEARANCE, None))
                continue
            deco = landmark_at(state, wx, wy) or decoration(state.seed, wx, wy, tile)
            light = tint_at(state, now, wx, wy)
            char, color_pair = tile_appearance(tile, deco)
            ground = _ground_sprite(tile, deco, light, meta, wx, wy)
            cells.append((sx, sy, char, shade(color_pair, light), ground))
    # The world itself is kept too, so its id can't be reused by another one meanwhile.
    _view_cache.update(key=key, cells=cells, world=state.world_tiles)
    return cells


def render_viewport(renderer, state, view: View) -> None:
    if state.world_tiles is None:
        return

    for sx, sy, char, color_pair, ground in _view_cells(state, view):
        if ground is not None:
            renderer.set_sprite(sx, sy, GROUND, *ground)
        # Only touch cells that changed, so the frontend redraws as little as possible.
        if renderer.get_cell(sx, sy) != (char, color_pair):
            renderer.set_cell(sx, sy, char, color_pair)

    _render_world_gems(renderer, state, view)
    _render_dropped_bag(renderer, state, view)


_WATER = {TYPE_STREAM, TYPE_LAKE, TYPE_SHALLOW, TYPE_DEEP}
_SIDES = ((0, -1, 1), (1, 0, 2), (0, 1, 4), (-1, 0, 8))  # (dx, dy, bit): N, E, S, W


# Grass overlaps onto lower ground around it (path, dirt, sand, the town square), so
# their boundary is a ragged edge of tufts rather than a straight grid line.
_GRASSY = {"grass", "mineable_grass", "tree"}
_UNDER_GRASS = {"path", "dirt", "bank", "town"}


def _side_mask(meta: dict, x: int, y: int, kinds: set) -> int:
    """Bits N=1, E=2, S=4, W=8 for the neighbours whose type is in ``kinds``."""
    mask = 0
    for dx, dy, bit in _SIDES:
        neighbour = meta.get((x + dx, y + dy))
        if neighbour is not None and neighbour["type"] in kinds:
            mask |= bit
    return mask


def shore_mask(meta: dict, x: int, y: int) -> int:
    """Which sides of a water tile touch land, as bits N=1, E=2, S=4, W=8 (4-bit
    autotiling); off the map counts as water, so map edges get no shore."""
    mask = 0
    for dx, dy, bit in _SIDES:
        neighbour = meta.get((x + dx, y + dy))
        if neighbour is not None and neighbour["type"] not in _WATER:
            mask |= bit
    return mask


def _ground_sprite(tile, deco, light, meta, wx, wy):
    """(sprite, tint) for a seen tile's ground."""
    sprite = deco or ("depleted" if tile.get("depleted") else tile["type"])
    if sprite in _WATER:
        mask = shore_mask(meta, wx, wy)
        if mask:
            sprite = f"{sprite}#{mask}"
    elif sprite in _UNDER_GRASS:
        mask = _side_mask(meta, wx, wy, _GRASSY)
        if mask:
            sprite = f"{sprite}+{mask}"
    fog = None if tile.get("visibility", "visible") == "visible" else EXPLORED_TINT
    return sprite, mix(fog, light)


def _render_dropped_bag(renderer, state, view: View) -> None:
    bag = state.dropped_bag
    if bag is None or not view.contains(bag["x"], bag["y"]):
        return
    visibility = state.world_tiles.meta.get((bag["x"], bag["y"]), {}).get("visibility", "visible")
    if visibility == "unseen":
        return
    light = tint_at(state, daylight.phase(state), bag["x"], bag["y"])
    color = DROPPED_BAG_COLOR if visibility == "visible" else dim(DROPPED_BAG_COLOR)
    renderer.set_cell(bag["x"] - view.x, bag["y"] - view.y, DROPPED_BAG_CHAR, shade(color, light))
    tint = None if visibility == "visible" else EXPLORED_TINT
    renderer.set_sprite(bag["x"] - view.x, bag["y"] - view.y, OBJECT, "bag", mix(tint, light))


def _render_world_gems(renderer, state, view: View) -> None:
    """Draw visible gems on top of the world tiles, respecting fog of war."""
    if not state.world_gems:
        return

    meta = state.world_tiles.meta
    now = daylight.phase(state)
    for (gx, gy), gem_name in state.world_gems.items():
        if not view.contains(gx, gy):
            continue
        sx, sy = gx - view.x, gy - view.y

        visibility = meta.get((gx, gy), {}).get("visibility", "visible")
        if visibility == "unseen":
            continue

        gem = GEM_CATALOG.get(gem_name)
        if gem is None:
            continue

        char, color_pair = gem.char, gem.color
        if visibility == "explored":
            color_pair = dim(color_pair)

        color_pair = shade(color_pair, tint_at(state, now, gx, gy))
        renderer.set_cell(sx, sy, char, color_pair)
        # One gem image, colored like the gem's glyph.
        renderer.set_sprite(sx, sy, OBJECT, "gem", color_pair[0])
