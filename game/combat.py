import time

from game.input import Action, InputState
from game.objects.registry import TOOL_CATALOG
from game.player import set_hud_message


def player_attack(inp: InputState, state) -> None:
    """Handle F key: attack the closest adjacent enemy."""
    if Action.ATTACK not in inp.pressed:
        return

    px, py = state.player_x, state.player_y

    # Find all adjacent enemies (Chebyshev distance <= 1)
    adjacent = [e for e in state.enemies if max(abs(e.x - px), abs(e.y - py)) <= 1]

    if not adjacent:
        set_hud_message(state, "No enemy in range!", 1.0)
        return

    # Target the closest (Manhattan distance)
    target = min(adjacent, key=lambda e: abs(e.x - px) + abs(e.y - py))

    # Calculate damage
    damage = _player_damage(state)
    target.hp -= damage
    target.flash_timer = 0.2  # brief flash feedback

    state.last_combat_time = time.time()

    if target.hp <= 0:
        _kill_enemy(state, target)
    else:
        set_hud_message(
            state,
            f"Hit {target.name}! ({target.hp}/{target.max_hp} HP left)",
            1.5,
        )


def _player_damage(state) -> int:
    """Base tool damage + upgrade bonus."""
    tool = state.equipped_tool
    if tool is None:
        return 1  # bare hands

    tool_def = TOOL_CATALOG.get(tool)
    base = tool_def.melee_damage if tool_def is not None else 1
    level = state.inventory.get("tools", {}).get(tool, {}).get("level", 1)
    return base + (level - 1)


def _kill_enemy(state, enemy) -> None:
    """Remove enemy, add loot to inventory, notify player."""
    from game import gems as gems_module

    state.enemies.remove(enemy)

    # Add loot
    if enemy.loot:
        gems_module.add_loot_to_inventory(state, enemy.loot)

    # Award gold (loot value goes to gold directly on kill)
    state.player_gold += enemy.loot_value

    set_hud_message(
        state,
        f"Defeated {enemy.name}! +${enemy.loot_value} and got {enemy.loot or 'nothing'}.",
        3.0,
    )


def enemy_attacks(state, dt: float) -> None:
    """All adjacent enemies auto-attack the player on their cooldown timer."""
    if not state.enemies:
        return

    px, py = state.player_x, state.player_y

    for enemy in state.enemies:
        # Check adjacency
        if max(abs(enemy.x - px), abs(enemy.y - py)) > 1:
            continue

        # Tick attack cooldown
        enemy.attack_cooldown -= dt
        if enemy.attack_cooldown > 0:
            continue

        # Attack!
        enemy.attack_cooldown = enemy.attack_cooldown_max
        state.player_hp -= enemy.attack
        state.last_combat_time = time.time()

        if state.player_hp <= 0:
            state.player_hp = 0
            state.active_scene = "death"
            return

        set_hud_message(
            state,
            f"A {enemy.name} hit you for {enemy.attack} damage!"
            f" ({state.player_hp}/{state.player_max_hp} HP)",
            1.5,
        )
