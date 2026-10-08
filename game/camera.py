from game.constants import MAP_HEIGHT, MAP_WIDTH, VIEWPORT_HEIGHT, VIEWPORT_WIDTH
from game.objects.registry import GEM_CATALOG
from game.theme import UNSEEN_APPEARANCE, dim, tile_appearance


def update_camera(state) -> None:
    """Center camera on player, clamped to map bounds."""
    cam_x = state.player_x - VIEWPORT_WIDTH // 2
    cam_y = state.player_y - VIEWPORT_HEIGHT // 2
    state.camera_x = max(0, min(cam_x, MAP_WIDTH - VIEWPORT_WIDTH))
    state.camera_y = max(0, min(cam_y, MAP_HEIGHT - VIEWPORT_HEIGHT))


def render_viewport(renderer, state) -> None:
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta
    max_x = min(VIEWPORT_WIDTH, renderer.width - 1)
    max_y = min(VIEWPORT_HEIGHT, renderer.height - 1)
    for sy in range(max_y):
        for sx in range(max_x):
            tile = meta.get((state.camera_x + sx, state.camera_y + sy))
            char, color_pair = tile_appearance(tile) if tile is not None else UNSEEN_APPEARANCE
            # Only touch cells that changed, so the frontend redraws as little as possible.
            if renderer.get_cell(sx, sy) != (char, color_pair):
                renderer.set_cell(sx, sy, char, color_pair)

    _render_world_gems(renderer, state)


def _render_world_gems(renderer, state) -> None:
    """Draw visible gems on top of the world tiles, respecting fog of war."""
    if not state.world_gems:
        return

    meta = state.world_tiles.meta
    cam_x, cam_y = state.camera_x, state.camera_y

    for (gx, gy), gem_name in state.world_gems.items():
        sx, sy = gx - cam_x, gy - cam_y
        if not (0 <= sx < VIEWPORT_WIDTH and 0 <= sy < VIEWPORT_HEIGHT):
            continue

        visibility = meta.get((gx, gy), {}).get("visibility", "visible")
        if visibility == "unseen":
            continue

        gem = GEM_CATALOG.get(gem_name)
        if gem is None:
            continue

        char, color_pair = gem.char, gem.color
        if visibility == "explored":
            color_pair = dim(color_pair)

        renderer.set_cell(sx, sy, char, color_pair)
