from game.constants import FOG_RADIUS, MAP_HEIGHT, MAP_WIDTH


def update_fog(state) -> None:
    meta = state.world_tiles.meta

    for coord in state.visible_tiles:
        if coord in meta:
            meta[coord]["visibility"] = "explored"

    state.visible_tiles = set()

    px, py = state.player_x, state.player_y
    x_min = max(0, px - FOG_RADIUS)
    x_max = min(MAP_WIDTH - 1, px + FOG_RADIUS)
    y_min = max(0, py - FOG_RADIUS)
    y_max = min(MAP_HEIGHT - 1, py + FOG_RADIUS)

    for ty in range(y_min, y_max + 1):
        for tx in range(x_min, x_max + 1):
            if (tx, ty) in meta:
                meta[(tx, ty)]["visibility"] = "visible"
                state.visible_tiles.add((tx, ty))
