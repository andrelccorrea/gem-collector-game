from game.constants import MAP_HEIGHT, MAP_WIDTH
from game.lantern import light_radius


def update_fog(state) -> None:
    meta = state.world_tiles.meta

    for coord in state.visible_tiles:
        if coord in meta:
            meta[coord]["visibility"] = "explored"

    state.visible_tiles = set()

    px, py = state.player_x, state.player_y
    radius = light_radius(state)
    x_min = max(0, px - radius)
    x_max = min(MAP_WIDTH - 1, px + radius)
    y_min = max(0, py - radius)
    y_max = min(MAP_HEIGHT - 1, py + radius)

    for ty in range(y_min, y_max + 1):
        for tx in range(x_min, x_max + 1):
            if (tx, ty) in meta:
                meta[(tx, ty)]["visibility"] = "visible"
                state.visible_tiles.add((tx, ty))
