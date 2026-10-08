import math
from collections import deque

from game.constants import (
    BIOME_CAVE_MIN_X,
    BIOME_HILLSIDE_MAX_Y,
    BIOME_MEADOW_MAX_X,
    DIFFICULTY_TIERS,
    ENEMY_MAX_DISTANCE,
    ENEMY_PATH_RECALC_INTERVAL,
    ENEMY_SPAWN_INTERVAL,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_ENEMIES_BASE,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
    VIEWPORT_HEIGHT,
    VIEWPORT_WIDTH,
)
from game.objects.registry import ENEMY_CATALOG


class Enemy:
    def __init__(self, x: int, y: int, enemy_type: str):
        enemy_def = ENEMY_CATALOG.get(enemy_type)
        self.x = x
        self.y = y
        self.name = enemy_type
        self.hp = enemy_def.hp if enemy_def is not None else 5
        self.max_hp = self.hp
        self.attack = enemy_def.attack if enemy_def is not None else 1
        self.char = enemy_def.char if enemy_def is not None else "?"
        self.color = enemy_def.color if enemy_def is not None else ((255, 255, 255), (0, 0, 0))
        self.loot = enemy_def.loot if enemy_def is not None else ""
        self.loot_value = enemy_def.loot_value if enemy_def is not None else 0
        self.aggro_range = enemy_def.aggro_range if enemy_def is not None else 5
        self.speed = enemy_def.speed if enemy_def is not None else 1.5
        self.attack_cooldown_max = enemy_def.attack_cooldown if enemy_def is not None else 1.5
        self.attack_cooldown = self.attack_cooldown_max
        self.path: list = []
        self.path_timer: float = 0.0
        self.move_timer: float = 0.0
        self.fleeing: bool = False
        self.flash_timer: float = 0.0


def _get_difficulty(state) -> dict:
    """Return the current difficulty tier config based on lifetime_earnings."""
    tiers = sorted(DIFFICULTY_TIERS.keys())
    current = DIFFICULTY_TIERS[0]
    for threshold in tiers:
        if state.lifetime_earnings >= threshold:
            current = DIFFICULTY_TIERS[threshold]
    return current


def _get_max_enemies(state) -> int:
    return _get_difficulty(state).get("max_enemies", MAX_ENEMIES_BASE)


def _get_spawn_interval(state) -> float:
    return _get_difficulty(state).get("spawn_interval", ENEMY_SPAWN_INTERVAL)


def _get_biome_for_pos(x: int, y: int) -> str:
    if x <= BIOME_MEADOW_MAX_X:
        return "meadow"
    if x >= BIOME_CAVE_MIN_X:
        return "cave"
    if y <= BIOME_HILLSIDE_MAX_Y:
        return "hillside"
    return "river"


def _get_enemy_type_for_biome(biome: str, state) -> str | None:
    """Choose a random enemy type appropriate for the biome."""
    difficulty = _get_difficulty(state)
    cave_bat_enabled = difficulty.get("enable_cave_bat", False)

    eligible = []
    for name, enemy_def in ENEMY_CATALOG.items():
        if biome in enemy_def.biomes:
            if name == "cave_bat" and not cave_bat_enabled:
                continue
            eligible.append(name)

    return state.rng.choice(eligible) if eligible else None


def _is_in_town_area(x: int, y: int) -> bool:
    return abs(x - TOWN_CENTER_X) <= 8 and abs(y - TOWN_CENTER_Y) <= 6


def _is_on_screen(x: int, y: int, state) -> bool:
    sx = x - state.camera_x
    sy = y - state.camera_y
    return 0 <= sx < VIEWPORT_WIDTH and 0 <= sy < VIEWPORT_HEIGHT


def spawn_enemies(state, dt: float) -> None:
    """Try to spawn a new enemy off-screen if conditions are met."""
    state.spawn_timer += dt
    if state.spawn_timer < _get_spawn_interval(state):
        return
    state.spawn_timer = 0.0

    if len(state.enemies) >= _get_max_enemies(state):
        return

    if state.world_tiles is None:
        return

    # Try up to 20 random positions to find a valid spawn
    for _ in range(20):
        x = state.rng.randint(0, MAP_WIDTH - 1)
        y = state.rng.randint(0, MAP_HEIGHT - 1)

        # Must be off-screen
        if _is_on_screen(x, y, state):
            continue
        # Must not be in town
        if _is_in_town_area(x, y):
            continue
        # Must be walkable
        meta = state.world_tiles.meta.get((x, y), {})
        if not meta.get("walkable", False):
            continue
        # Must not already have an enemy there
        if any(e.x == x and e.y == y for e in state.enemies):
            continue

        biome = _get_biome_for_pos(x, y)
        enemy_type = _get_enemy_type_for_biome(biome, state)
        if enemy_type is None:
            continue

        # Apply difficulty modifiers
        difficulty = _get_difficulty(state)
        enemy = Enemy(x, y, enemy_type)
        if enemy_type == "bear" and "bear_hp" in difficulty:
            enemy.hp = difficulty["bear_hp"]
            enemy.max_hp = enemy.hp
        if enemy_type == "snake" and "snake_attack" in difficulty:
            enemy.attack = difficulty["snake_attack"]
        if enemy_type == "bear" and "bear_attack" in difficulty:
            enemy.attack = difficulty["bear_attack"]

        state.enemies.append(enemy)
        return


def find_path_bfs(
    surface, start_x: int, start_y: int, target_x: int, target_y: int, max_steps: int = 50
) -> list:
    """BFS pathfinding. Returns list of (x,y) from start to target, or empty list."""
    if start_x == target_x and start_y == target_y:
        return []

    queue = deque([(start_x, start_y, [])])
    visited = {(start_x, start_y)}

    while queue:
        cx, cy, path = queue.popleft()

        if len(path) >= max_steps:
            # Return greedy path toward target as fallback
            return _greedy_path(start_x, start_y, target_x, target_y, max_steps // 2)

        for nx, ny in [(cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)]:
            if not (0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT):
                continue
            if (nx, ny) in visited:
                continue
            meta = surface.meta.get((nx, ny), {})
            if not meta.get("walkable", True):
                continue

            new_path = path + [(nx, ny)]
            if nx == target_x and ny == target_y:
                return new_path

            visited.add((nx, ny))
            queue.append((nx, ny, new_path))

    return _greedy_path(start_x, start_y, target_x, target_y, max_steps // 2)


def _greedy_path(sx: int, sy: int, tx: int, ty: int, steps: int) -> list:
    """Greedy direct path (no obstacle avoidance) as fallback."""
    path = []
    cx, cy = sx, sy
    for _ in range(steps):
        if cx == tx and cy == ty:
            break
        if cx != tx:
            cx += 1 if tx > cx else -1
        elif cy != ty:
            cy += 1 if ty > cy else -1
        path.append((cx, cy))
    return path


def update_enemies(state, dt: float) -> None:
    """Update all enemies: pathfinding, movement, despawn."""
    if state.world_tiles is None:
        return

    px, py = state.player_x, state.player_y
    to_remove = []

    for enemy in state.enemies:
        # Despawn if too far from player
        dist = abs(enemy.x - px) + abs(enemy.y - py)
        if dist > ENEMY_MAX_DISTANCE:
            to_remove.append(enemy)
            continue

        # Flash timer countdown (visual hit feedback)
        if enemy.flash_timer > 0:
            enemy.flash_timer = max(0.0, enemy.flash_timer - dt)

        # Check aggro
        aggroed = dist <= enemy.aggro_range

        # Flee if HP is low (< 25% of max)
        enemy.fleeing = enemy.hp < enemy.max_hp * 0.25

        # Pathfinding: recalculate path periodically
        enemy.path_timer -= dt
        if enemy.path_timer <= 0:
            enemy.path_timer = ENEMY_PATH_RECALC_INTERVAL
            if aggroed and not enemy.fleeing:
                enemy.path = find_path_bfs(state.world_tiles, enemy.x, enemy.y, px, py)
            elif enemy.fleeing:
                # Flee: path away from player (find a tile farther away)
                flee_x = max(0, min(MAP_WIDTH - 1, enemy.x + (enemy.x - px)))
                flee_y = max(0, min(MAP_HEIGHT - 1, enemy.y + (enemy.y - py)))
                enemy.path = find_path_bfs(state.world_tiles, enemy.x, enemy.y, flee_x, flee_y, 20)
            else:
                enemy.path = []

        # Move along path
        if enemy.path:
            adjacent_to_player = abs(enemy.x - px) <= 1 and abs(enemy.y - py) <= 1
            if not adjacent_to_player or enemy.fleeing:
                enemy.move_timer += dt
                move_interval = 1.0 / enemy.speed
                if enemy.move_timer >= move_interval:
                    enemy.move_timer = 0.0
                    next_pos = enemy.path[0]
                    nx, ny = next_pos
                    # Check no other enemy is there
                    if not any(e is not enemy and e.x == nx and e.y == ny for e in state.enemies):
                        meta = state.world_tiles.meta.get((nx, ny), {})
                        if meta.get("walkable", True) and not _is_in_town_area(nx, ny):
                            enemy.x = nx
                            enemy.y = ny
                    enemy.path.pop(0)

    for e in to_remove:
        state.enemies.remove(e)


def render_enemies(renderer, state) -> None:
    max_x = math.floor(renderer.width) - 1
    max_y = math.floor(renderer.height) - 1

    for enemy in state.enemies:
        tile_vis = state.world_tiles.meta.get((enemy.x, enemy.y), {}).get("visibility", "visible")
        if tile_vis != "visible":
            continue

        screen_x = enemy.x - state.camera_x
        screen_y = enemy.y - state.camera_y

        if not (
            0 <= screen_x < min(VIEWPORT_WIDTH, max_x)
            and 0 <= screen_y < min(VIEWPORT_HEIGHT, max_y)
        ):
            continue

        color = enemy.color
        if enemy.flash_timer > 0:
            color = ((255, 255, 255), (200, 0, 0))

        renderer.set_cell(screen_x, screen_y, enemy.char, color)
