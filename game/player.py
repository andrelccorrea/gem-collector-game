import math
import time

from game.constants import (
    COLOR_PLAYER,
    HP_REGEN_INTERVAL,
    HP_REGEN_RATE,
    MAP_HEIGHT,
    MAP_WIDTH,
    MOVE_COOLDOWN,
    PLAYER_CHAR,
    PLAYER_START_GOLD,
    PLAYER_START_HP,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)


def init_player(state) -> None:
    """Initialize player to starting state."""
    if state.world_tiles is not None and state.world_tiles.start_pos is not None:
        state.player_x, state.player_y = state.world_tiles.start_pos
    else:
        state.player_x = TOWN_CENTER_X
        state.player_y = TOWN_CENTER_Y
    state.player_hp = PLAYER_START_HP
    state.player_max_hp = PLAYER_START_HP
    state.player_gold = PLAYER_START_GOLD
    state.equipped_tool = "shovel"
    state.inventory = {
        "gems": {},
        "tools": {"shovel": {"level": 1}},
        "loot": {},
    }
    state.move_cooldown = 0.0
    state.regen_timer = 0.0
    state.last_combat_time = 0.0


def update_player(window, state, dt: float) -> None:
    """Handle movement, HP regen, HUD message timer."""
    _handle_movement(window, state, dt)
    _handle_hp_regen(state, dt)
    _handle_hud_message(state, dt)
    _check_death(state)


def _handle_movement(window, state, dt: float) -> None:
    """Discrete tile movement with cooldown timer using keyboard.held."""
    state.move_cooldown = max(0.0, state.move_cooldown - dt)
    if state.move_cooldown > 0:
        return

    held = window.keyboard.held
    dx, dy = 0, 0
    if "left" in held or "a" in held:
        dx = -1
    elif "right" in held or "d" in held:
        dx = 1
    elif "up" in held or "w" in held:
        dy = -1
    elif "down" in held or "s" in held:
        dy = 1

    if dx == 0 and dy == 0:
        return

    new_x = state.player_x + dx
    new_y = state.player_y + dy

    # Clamp to map bounds
    new_x = max(0, min(new_x, MAP_WIDTH - 1))
    new_y = max(0, min(new_y, MAP_HEIGHT - 1))

    # Check walkability from surface meta
    if state.world_tiles is not None:
        meta = state.world_tiles.meta.get((new_x, new_y), {})
        if not meta.get("walkable", True):
            return  # blocked

    state.player_x = new_x
    state.player_y = new_y
    state.move_cooldown = MOVE_COOLDOWN


def _handle_hp_regen(state, dt: float) -> None:
    """Regen HP when in town and not recently in combat."""
    if state.player_hp >= state.player_max_hp:
        return

    # Check if in town
    if not _is_in_town(state):
        return

    # Check not in recent combat (5 second window)
    if time.time() - state.last_combat_time < 5.0:
        return

    state.regen_timer += dt
    if state.regen_timer >= HP_REGEN_INTERVAL:
        state.regen_timer = 0.0
        state.player_hp = min(state.player_max_hp, state.player_hp + HP_REGEN_RATE)


def _is_in_town(state) -> bool:
    return abs(state.player_x - TOWN_CENTER_X) <= 7 and abs(state.player_y - TOWN_CENTER_Y) <= 5


def _handle_hud_message(state, dt: float) -> None:
    """Count down HUD message timer."""
    if state.hud_message_timer > 0:
        state.hud_message_timer = max(0.0, state.hud_message_timer - dt)
        if state.hud_message_timer <= 0:
            state.hud_message = ""


def _check_death(state) -> None:
    if state.player_hp <= 0:
        state.player_hp = 0
        state.active_scene = "death"


def render_player(renderer, state) -> None:
    if state.world_tiles is None:
        return

    screen_x = state.player_x - state.camera_x
    screen_y = state.player_y - state.camera_y

    max_x = math.floor(renderer.width) - 1
    max_y = math.floor(renderer.height) - 1

    if 0 <= screen_x < min(VIEWPORT_WIDTH, max_x) and 0 <= screen_y < min(VIEWPORT_HEIGHT, max_y):
        renderer.set_cell(screen_x, screen_y, PLAYER_CHAR, COLOR_PLAYER)


def set_hud_message(state, msg: str, duration: float = 2.0) -> None:
    """Set a temporary HUD message."""
    state.hud_message = msg
    state.hud_message_timer = duration
