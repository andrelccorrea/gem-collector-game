from collections import deque

from game.camera import OBJECT, on_screen
from game.constants import (
    DIFFICULTY_TIERS,
    ENEMY_MAX_DISTANCE,
    ENEMY_PATH_RECALC_INTERVAL,
    ENEMY_SPAWN_INTERVAL,
    MAP_HEIGHT,
    MAP_WIDTH,
    MAX_ENEMIES_BASE,
)
from game.geography import biome_at, in_town
from game.objects.registry import ENEMY_CATALOG

# Enemies keep this many tiles away from the town rectangle.
ENEMY_TOWN_MARGIN = 2
# Spawns stay this far inside the despawn distance, so walking a few steps away from
# a fresh spawn does not remove it at once.
ENEMY_SPAWN_DISTANCE = ENEMY_MAX_DISTANCE - 10
HIT_TINT = (255, 90, 90)  # sprite tint while an enemy flashes from a hit


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


def _is_on_screen(x: int, y: int, state) -> bool:
    return on_screen(state, x, y)


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

    # Try up to 20 random positions in a ring around the player: outside the view, but
    # well within the despawn distance (Manhattan).
    px, py = state.player_x, state.player_y
    for _ in range(20):
        dx = state.rng.randint(-ENEMY_SPAWN_DISTANCE, ENEMY_SPAWN_DISTANCE)
        reach = ENEMY_SPAWN_DISTANCE - abs(dx)
        x, y = px + dx, py + state.rng.randint(-reach, reach)

        if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
            continue
        # Must be off-screen
        if _is_on_screen(x, y, state):
            continue
        # Must not be in or right next to town
        if in_town(x, y, ENEMY_TOWN_MARGIN):
            continue
        # Must be walkable
        meta = state.world_tiles.meta.get((x, y), {})
        if not meta.get("walkable", False):
            continue
        # Must not already have an enemy there
        if any(e.x == x and e.y == y for e in state.enemies):
            continue

        biome = biome_at(x, y)
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

        # Spread path recalculations so enemies don't all search on the same step.
        enemy.path_timer = state.rng.uniform(0.0, ENEMY_PATH_RECALC_INTERVAL)
        state.enemies.append(enemy)
        return


def find_path_bfs(
    surface,
    start_x: int,
    start_y: int,
    target_x: int,
    target_y: int,
    max_steps: int = 50,
    blocked=None,
) -> list:
    """Shortest walkable path from start to target as a list of (x, y), start excluded.

    The search explores at most ``max_steps`` tiles away. If the target cannot be
    reached within that (or at all), the path leads to the explored tile closest to
    the target instead, so the walker still moves sensibly and never through walls.
    ``blocked(x, y)`` marks extra tiles to avoid (e.g. the town for enemies).
    """
    start, target = (start_x, start_y), (target_x, target_y)
    if start == target:
        return []

    def distance(p):
        return abs(p[0] - target_x) + abs(p[1] - target_y)

    parent = {start: None}
    depth = {start: 0}
    best = start
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if depth[current] >= max_steps:
            continue
        cx, cy = current
        for nxt in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if nxt in parent or not (0 <= nxt[0] < MAP_WIDTH and 0 <= nxt[1] < MAP_HEIGHT):
                continue
            if not surface.meta.get(nxt, {}).get("walkable", False):
                continue
            if blocked is not None and blocked(*nxt):
                continue
            parent[nxt] = current
            depth[nxt] = depth[current] + 1
            if nxt == target:
                return _walk_back(parent, nxt)
            if distance(nxt) < distance(best):
                best = nxt
            queue.append(nxt)

    return _walk_back(parent, best)


def _walk_back(parent: dict, end) -> list:
    """Path from the search start to ``end`` (start excluded) via parent pointers."""
    path = []
    while parent[end] is not None:
        path.append(end)
        end = parent[end]
    path.reverse()
    return path


def _enemy_blocked(x: int, y: int) -> bool:
    return in_town(x, y, ENEMY_TOWN_MARGIN)


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
                enemy.path = find_path_bfs(
                    state.world_tiles, enemy.x, enemy.y, px, py, blocked=_enemy_blocked
                )
            elif enemy.fleeing:
                # Flee: path away from player (find a tile farther away)
                flee_x = max(0, min(MAP_WIDTH - 1, enemy.x + (enemy.x - px)))
                flee_y = max(0, min(MAP_HEIGHT - 1, enemy.y + (enemy.y - py)))
                enemy.path = find_path_bfs(
                    state.world_tiles, enemy.x, enemy.y, flee_x, flee_y, 20, _enemy_blocked
                )
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
                        if meta.get("walkable", True) and not _enemy_blocked(nx, ny):
                            enemy.x = nx
                            enemy.y = ny
                    enemy.path.pop(0)

    for e in to_remove:
        state.enemies.remove(e)


def render_enemies(renderer, state, view) -> None:
    for enemy in state.enemies:
        tile_vis = state.world_tiles.meta.get((enemy.x, enemy.y), {}).get("visibility", "visible")
        if tile_vis != "visible":
            continue

        if not view.contains(enemy.x, enemy.y):
            continue
        screen_x, screen_y = enemy.x - view.x, enemy.y - view.y

        color = enemy.color
        if enemy.flash_timer > 0:
            color = ((255, 255, 255), (200, 0, 0))

        renderer.set_cell(screen_x, screen_y, enemy.char, color)
        tint = HIT_TINT if enemy.flash_timer > 0 else None
        renderer.set_sprite(screen_x, screen_y, OBJECT, enemy.name, tint)
