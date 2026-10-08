"""World-side building logic: entering buildings and the shared win check."""

from game.constants import (
    TYPE_LAPIDARY,
    TYPE_SAVE,
    TYPE_SHOP,
    WIN_LIFETIME_EARNINGS,
)
from game.input import Action, InputState


def check_building_interaction(inp: InputState, state) -> None:
    """Check if player is on a building tile and Space was pressed."""
    if Action.USE not in inp.pressed:
        return
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((state.player_x, state.player_y), {})
    tile_type = meta.get("type", "")

    if tile_type == TYPE_SHOP:
        state.active_scene = "shop"
        state.shop_cursor = 0
        state.shop_tab = 0
    elif tile_type == TYPE_LAPIDARY:
        state.active_scene = "lapidary"
        state.lapidary_cursor = 0
    elif tile_type == TYPE_SAVE:
        state.active_scene = "save_point"


def check_win(state) -> None:
    """Trigger win scene if lifetime earnings threshold is reached."""
    if state.lifetime_earnings >= WIN_LIFETIME_EARNINGS and not state.has_won:
        state.has_won = True
        state.active_scene = "win"
