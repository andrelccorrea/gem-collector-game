"""Frontend-independent game simulation: run creation and the fixed-step update.

Nothing here draws or reads the wall clock, so the same seed and the same inputs
always reproduce the same run (replays, balance simulations, daily seeded runs).
"""

import uuid

from game import (
    buildings,
    camera,
    combat,
    enemies,
    fog,
    lantern,
    market,
    player,
    tips,
    tools,
    world,
)
from game.input import Action, InputState
from game.state import GameState, gameplay_rng


def new_run(seed: int) -> GameState:
    """Return a fresh GameState for a new run on the world generated from ``seed``."""
    # The run id only labels the run for one-time rewards; it never touches gameplay.
    state = GameState(seed=seed, rng=gameplay_rng(seed), run_id=uuid.uuid4().hex)
    state.world_tiles, state.world_gems = world.generate_world(seed)
    player.init_player(state)
    state.lantern_fuel = lantern.lantern_capacity(state)
    camera.update_camera(state)
    fog.update_fog(state)
    state.active_scene = "game"
    return state


def step_game(inp: InputState, state, dt: float) -> bool:
    """Advance the game by one fixed step. Returns False once the scene changed."""
    state.game_time += dt
    market.update_market(state, dt)

    # Enemy spawning and movement
    enemies.spawn_enemies(state, dt)
    enemies.update_enemies(state, dt)

    # Combat: enemy auto-attacks
    combat.enemy_attacks(state, dt)

    # Building interaction (USE on a building tile)
    buildings.check_building_interaction(inp, state)

    # Player movement, HP regen, death check
    player.update_player(inp, state, dt)

    # Player attack, tool cycling and use
    combat.player_attack(inp, state)
    tools.update_tools(inp, state)
    tools.use_tool(inp, state)

    lantern.update_lantern(state, dt)
    if state.world_tiles is not None:
        fog.update_fog(state)
        # Spawning reads the viewport, so keep it in sync with the simulation rather
        # than with rendering (which may run a different number of times).
        camera.update_camera(state)

    tips.check_tips(state)

    if Action.CANCEL in inp.pressed:
        state.active_scene = "menu"

    if state.daily:
        from game.daily import check_daily_end

        check_daily_end(state)

    return state.active_scene == "game"
