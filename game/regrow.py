"""Worked-out ground recovers: a dug or panned tile can be worked again a game day later.

Without it a long run could exhaust every reachable spot before reaching the goal (a
balance-bot run did), leaving nothing to do. Tiles come back in the order they were
worked out, so ``state.depleted_at`` (tile -> game time) is checked from its oldest end.
"""

from game.constants import TILE_PROPS

REGROW_SECONDS = 360.0  # one game day


def update_regrowth(state) -> None:
    if state.world_tiles is None:
        return
    while state.depleted_at:
        pos, worked_at = next(iter(state.depleted_at.items()))
        if state.game_time - worked_at < REGROW_SECONDS:
            return
        del state.depleted_at[pos]
        state.depleted_tiles.discard(pos)
        state.tiles_version += 1
        tile = state.world_tiles.meta.get(pos)
        if tile is not None:
            tile["depleted"] = False
            tile["interactable"] = TILE_PROPS[tile["type"]][1]
