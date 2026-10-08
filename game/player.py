from game import daylight
from game.camera import OBJECT
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
)
from game.daylight import shade, tint_at
from game.events import HEAL, HEAL_COLOR, emit
from game.geography import in_town
from game.input import Action, InputState
from game.objects.registry import BOOTS


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
    state.last_move = None
    state.queued_move = None
    state.regen_timer = 0.0
    state.last_combat_time = float("-inf")


def update_player(inp: InputState, state, dt: float) -> None:
    """Handle movement, recall, HP regen, HUD message timer."""
    # A successful recall ends this step's movement: no step away from the town spawn.
    if not (Action.RECALL in inp.pressed and _use_recall_charm(state)):
        _handle_movement(inp, state, dt)
    _handle_hp_regen(state, dt)
    _handle_hud_message(state, dt)
    _check_death(state)


_MOVE_DELTAS = {
    Action.MOVE_LEFT: (-1, 0),
    Action.MOVE_RIGHT: (1, 0),
    Action.MOVE_UP: (0, -1),
    Action.MOVE_DOWN: (0, 1),
}


def _requested_move(actions):
    return next((a for a in _MOVE_DELTAS if a in actions), None)


def _handle_movement(inp: InputState, state, dt: float) -> None:
    """Discrete tile movement, one step per move press (or while held), rate-limited."""
    state.move_cooldown = max(0.0, state.move_cooldown - dt)
    requested = _requested_move(inp.pressed) or _requested_move(inp.held)

    if state.move_cooldown > 0:
        # Keep a direction change pressed mid-step so quick turns are not lost; repeats
        # of the current direction are dropped so the player never overshoots on release.
        if requested is not None and requested != state.last_move:
            state.queued_move = requested
        return

    action = requested or state.queued_move
    state.queued_move = None
    if action is None:
        return
    dx, dy = _MOVE_DELTAS[action]

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
    state.last_move = action
    state.move_cooldown = MOVE_COOLDOWN * BOOTS["step_multipliers"][state.boots_level]


def _handle_hp_regen(state, dt: float) -> None:
    """Regen HP when in town and not recently in combat."""
    if state.player_hp >= state.player_max_hp:
        return

    # Check if in town
    if not in_town(state.player_x, state.player_y):
        return

    # Check not in recent combat (5 second window)
    if state.game_time - state.last_combat_time < 5.0:
        return

    state.regen_timer += dt
    if state.regen_timer >= HP_REGEN_INTERVAL:
        state.regen_timer = 0.0
        state.player_hp = min(state.player_max_hp, state.player_hp + HP_REGEN_RATE)
        emit(state, HEAL, f"+{HP_REGEN_RATE}", HEAL_COLOR, "heart")


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


def render_player(renderer, state, view) -> None:
    if state.world_tiles is None:
        return
    if view.contains(state.player_x, state.player_y):
        sx, sy = state.player_x - view.x, state.player_y - view.y
        light = tint_at(state, daylight.phase(state), state.player_x, state.player_y)
        renderer.set_cell(sx, sy, PLAYER_CHAR, shade(COLOR_PLAYER, light))
        renderer.set_sprite(sx, sy, OBJECT, "player", light)


def set_hud_message(state, msg: str, duration: float = 2.0) -> None:
    """Set a temporary HUD message."""
    state.hud_message = msg
    state.hud_message_timer = duration


def _use_recall_charm(state) -> bool:
    """Teleport to town if possible; returns whether the player was recalled."""
    if in_town(state.player_x, state.player_y):
        set_hud_message(state, "You are already in town.", 1.5)
    elif state.recall_charms <= 0:
        set_hud_message(state, "No Recall Charm. Buy one at the shop.", 1.5)
    elif state.world_tiles is not None and state.world_tiles.start_pos is not None:
        state.recall_charms -= 1
        state.player_x, state.player_y = state.world_tiles.start_pos
        state.queued_move = None
        set_hud_message(state, f"Recalled to town ({state.recall_charms} charms left).", 2.0)
        return True
    return False
