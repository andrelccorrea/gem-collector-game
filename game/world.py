import math
import random
from collections import deque

from clingine.surface import Surface
from game.bsp import BSPNode, connect_rooms, get_leaves, place_rooms, split
from game.constants import (
    LAPIDARY_X,
    LAPIDARY_Y,
    MAP_HEIGHT,
    MAP_WIDTH,
    SAVE_X,
    SAVE_Y,
    SHOP_X,
    SHOP_Y,
    TILE_DEFS,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
    TYPE_BANK,
    TYPE_CAVE_FLOOR,
    TYPE_CAVE_WALL,
    TYPE_DEEP,
    TYPE_DIRT,
    TYPE_GRASS,
    TYPE_LAKE,
    TYPE_LAPIDARY,
    TYPE_MINEABLE_DIRT,
    TYPE_MINEABLE_GRASS,
    TYPE_MINEABLE_ROCK,
    TYPE_ORE,
    TYPE_PATH,
    TYPE_RICH_ORE,
    TYPE_ROCK,
    TYPE_SAVE,
    TYPE_SHALLOW,
    TYPE_SHOP,
    TYPE_STREAM,
    TYPE_TOWN,
    TYPE_TREE,
)

# Town boundaries: 12-wide x 8-tall cluster centered at TOWN_CENTER
TOWN_LEFT = TOWN_CENTER_X - 6
TOWN_RIGHT = TOWN_CENTER_X + 5  # 12 tiles wide: [94..105]
TOWN_TOP = TOWN_CENTER_Y - 4
TOWN_BOTTOM = TOWN_CENTER_Y + 3  # 8 tiles tall: [36..43]

# River band: winding horizontal strip centred near y=58
RIVER_CENTER_Y = 58
RIVER_HALF_WIDTH = 2  # band spans ±2 rows around the centre line


def _is_town(x: int, y: int) -> bool:
    return TOWN_LEFT <= x <= TOWN_RIGHT and TOWN_TOP <= y <= TOWN_BOTTOM


def _biome_corridor_tile(x: int, y: int) -> str:
    """Return an appropriate walkable tile type for carving a corridor at (x, y)."""
    if x >= 120:
        return TYPE_CAVE_FLOOR
    if x >= 50 and y <= 39:
        return TYPE_DIRT
    return TYPE_PATH


def _apply_tile(surface: Surface, x: int, y: int, type_name: str) -> None:
    """Write one tile to the surface and meta dict."""
    char, color_pair, walkable, interactable = TILE_DEFS[type_name]
    surface.set_tile(x, y, char, color_pair)
    surface.meta[(x, y)] = {
        "type": type_name,
        "walkable": walkable,
        "interactable": interactable,
        "depleted": False,
        "visibility": "unseen",
    }


_WATER_TYPES = {TYPE_STREAM, TYPE_LAKE, TYPE_SHALLOW, TYPE_DEEP}


def _carve_stream(
    surface: Surface,
    rng: random.Random,
    x_start: int,
    y_start: int,
    x_end: int,
    y_end: int,
    bounds: tuple[int, int, int, int] | None = None,
) -> None:
    """Random walk from start to end carving stream tiles with directional bias.

    bounds: optional (x_min, y_min, x_max, y_max) to restrict carving — useful
    to keep the stream inside its region.
    """
    if bounds is None:
        bx_min, by_min, bx_max, by_max = 0, 0, MAP_WIDTH, MAP_HEIGHT
    else:
        bx_min, by_min, bx_max, by_max = bounds

    cx, cy = x_start, y_start
    max_steps = (abs(x_end - x_start) + abs(y_end - y_start)) * 4 + 50
    steps = 0

    while (cx, cy) != (x_end, y_end) and steps < max_steps:
        if bx_min <= cx < bx_max and by_min <= cy < by_max and not _is_town(cx, cy):
            _apply_tile(surface, cx, cy, TYPE_STREAM)
            # Occasional widening for organic feel
            if rng.random() < 0.25:
                wx, wy = cx + rng.choice([-1, 1]), cy
                if bx_min <= wx < bx_max and by_min <= wy < by_max and not _is_town(wx, wy):
                    _apply_tile(surface, wx, wy, TYPE_STREAM)

        # Bias movement toward target with random perturbation
        dx_target = x_end - cx
        dy_target = y_end - cy

        if abs(dx_target) > abs(dy_target):
            primary = (1 if dx_target > 0 else -1, 0)
        else:
            primary = (0, 1 if dy_target > 0 else -1)

        roll = rng.random()
        if roll < 0.65:
            dx, dy = primary
        elif roll < 0.85:
            # Perpendicular drift for meandering
            if primary[0] != 0:
                dx, dy = 0, rng.choice([-1, 1])
            else:
                dx, dy = rng.choice([-1, 1]), 0
        else:
            # Diagonal step
            dx = primary[0] if primary[0] != 0 else rng.choice([-1, 1])
            dy = primary[1] if primary[1] != 0 else rng.choice([-1, 1])

        cx += dx
        cy += dy
        steps += 1

    # Ensure end point is also water
    if bx_min <= x_end < bx_max and by_min <= y_end < by_max and not _is_town(x_end, y_end):
        _apply_tile(surface, x_end, y_end, TYPE_STREAM)


def _carve_lake(
    surface: Surface,
    rng: random.Random,
    cx: int,
    cy: int,
    radius: int,
    bounds: tuple[int, int, int, int] | None = None,
) -> None:
    """Carve an organic lake centered at (cx, cy). Uses radial distance with
    angular perturbation for irregular shape."""
    if bounds is None:
        bx_min, by_min, bx_max, by_max = 0, 0, MAP_WIDTH, MAP_HEIGHT
    else:
        bx_min, by_min, bx_max, by_max = bounds

    # Pre-roll perturbation for ~16 angular sectors so the lake outline is
    # consistent (no per-tile noise jitter).
    sectors = 16
    perturb = [rng.uniform(-1.0, 1.5) for _ in range(sectors)]

    span = radius + 2
    for dy in range(-span, span + 1):
        for dx in range(-span, span + 1):
            tx, ty = cx + dx, cy + dy
            if not (bx_min <= tx < bx_max and by_min <= ty < by_max):
                continue
            if _is_town(tx, ty):
                continue

            dist = (dx * dx + dy * dy) ** 0.5
            if dx == 0 and dy == 0:
                effective_radius = radius
            else:
                angle = math.atan2(dy, dx)
                idx = int((angle + math.pi) / (2 * math.pi) * sectors) % sectors
                effective_radius = radius + perturb[idx]

            if dist <= effective_radius:
                _apply_tile(surface, tx, ty, TYPE_LAKE)


def _scatter_mineable(
    surface: Surface,
    rng: random.Random,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
    base_type: str,
    mineable_type: str,
    density: float,
) -> None:
    """Convert a fraction of base_type tiles within bounds to mineable_type."""
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if _is_town(x, y):
                continue
            if surface.meta.get((x, y), {}).get("type") == base_type:
                if rng.random() < density:
                    _apply_tile(surface, x, y, mineable_type)


def _add_water_banks(
    surface: Surface,
    x_min: int,
    y_min: int,
    x_max: int,
    y_max: int,
) -> None:
    """Convert grass tiles adjacent to water into dirt banks."""
    changes: list[tuple[int, int]] = []
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if _is_town(x, y):
                continue
            if surface.meta.get((x, y), {}).get("type") != TYPE_GRASS:
                continue
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if surface.meta.get((nx, ny), {}).get("type") in _WATER_TYPES:
                    changes.append((x, y))
                    break

    for x, y in changes:
        _apply_tile(surface, x, y, TYPE_DIRT)


def _place_visible_gems(
    surface: Surface,
    rng: random.Random,
    eligible_types: tuple[str, ...],
    region_bounds: tuple[int, int, int, int],
    biome: str,
    density: float,
) -> dict[tuple[int, int], str]:
    """Roll visible gems on tiles of eligible types within bounds.

    Uses the same biome-filtered weighted choice as `gems.roll_gem_drop` but
    without the no-drop weight — every selected tile gets a gem.
    """
    from game.objects.registry import GEM_CATALOG

    eligible = {n: g for n, g in GEM_CATALOG.items() if biome in g.biomes}
    if not eligible:
        return {}

    names = list(eligible.keys())
    weights = [eligible[n].rarity_weight for n in names]

    placed: dict[tuple[int, int], str] = {}
    x_min, y_min, x_max, y_max = region_bounds
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if _is_town(x, y):
                continue
            if surface.meta.get((x, y), {}).get("type") not in eligible_types:
                continue
            if rng.random() >= density:
                continue
            gem_name = rng.choices(names, weights=weights, k=1)[0]
            placed[(x, y)] = gem_name
    return placed


def _generate_meadow(surface: Surface, rng: random.Random) -> None:
    """Meadow region (x=0..49, y=0..79): grass with scattered trees, optional
    ponds, and mineable patches."""
    x_min, y_min, x_max, y_max = 0, 0, 50, 80

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if not _is_town(x, y):
                _apply_tile(surface, x, y, TYPE_GRASS)

    # Scatter trees (~15%) — they act as walls but cluster naturally with density
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_GRASS, TYPE_TREE, 0.15)

    # Optional small pond (50% chance)
    if rng.random() < 0.5:
        cx = rng.randint(x_min + 6, x_max - 7)
        cy = rng.randint(y_min + 6, y_max - 7)
        _carve_lake(surface, rng, cx, cy, rng.randint(2, 3), bounds=(x_min, y_min, x_max, y_max))
        _add_water_banks(surface, x_min, y_min, x_max, y_max)

    # Mineable grass patches — sparse
    _scatter_mineable(
        surface, rng, x_min, y_min, x_max, y_max, TYPE_GRASS, TYPE_MINEABLE_GRASS, 0.03
    )
    # Mineable dirt patches on banks (if pond was placed)
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_DIRT, TYPE_MINEABLE_DIRT, 0.10)


def _generate_hillside(surface: Surface, rng: random.Random) -> None:
    """Hillside region (x=50..119, y=0..39): dirt with scattered rocks and
    mineable patches."""
    x_min, y_min, x_max, y_max = 50, 0, 120, 40

    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if not _is_town(x, y):
                _apply_tile(surface, x, y, TYPE_DIRT)

    # Scatter rocks (~18%) — impassable obstacles
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_DIRT, TYPE_ROCK, 0.18)

    # Optional pond (40% chance)
    if rng.random() < 0.4:
        cx = rng.randint(x_min + 6, x_max - 7)
        cy = rng.randint(y_min + 4, y_max - 5)
        _carve_lake(surface, rng, cx, cy, rng.randint(2, 3), bounds=(x_min, y_min, x_max, y_max))
        _add_water_banks(surface, x_min, y_min, x_max, y_max)

    # Mineable dirt and rock patches
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_DIRT, TYPE_MINEABLE_DIRT, 0.06)
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_ROCK, TYPE_MINEABLE_ROCK, 0.20)


def _retile_cave_resources(surface: Surface, rng: random.Random) -> None:
    """Add prospecting features to the cave: convert legacy ORE/RICH_ORE if
    present, scatter mineable patches on cave floor, and carve 1-2 small pools."""
    cave_min_x = 120
    cave_bounds = (cave_min_x, 0, MAP_WIDTH, MAP_HEIGHT)

    # Convert any legacy ore tiles to the new mineable variants
    for y in range(MAP_HEIGHT):
        for x in range(cave_min_x, MAP_WIDTH):
            t = surface.meta.get((x, y), {}).get("type")
            if t == TYPE_ORE:
                _apply_tile(surface, x, y, TYPE_MINEABLE_DIRT)
            elif t == TYPE_RICH_ORE:
                _apply_tile(surface, x, y, TYPE_MINEABLE_ROCK)

    # Scatter prospecting patches on cave floor
    _scatter_mineable(
        surface,
        rng,
        cave_min_x,
        0,
        MAP_WIDTH,
        MAP_HEIGHT,
        TYPE_CAVE_FLOOR,
        TYPE_MINEABLE_DIRT,
        0.05,
    )
    _scatter_mineable(
        surface,
        rng,
        cave_min_x,
        0,
        MAP_WIDTH,
        MAP_HEIGHT,
        TYPE_CAVE_FLOOR,
        TYPE_MINEABLE_ROCK,
        0.03,
    )

    # Carve 1-2 small underground pools for visible gem placement
    n_pools = rng.randint(1, 2)
    for _ in range(n_pools):
        cx = rng.randint(cave_min_x + 5, MAP_WIDTH - 6)
        cy = rng.randint(5, MAP_HEIGHT - 6)
        if surface.meta.get((cx, cy), {}).get("type") == TYPE_CAVE_FLOOR:
            _carve_lake(surface, rng, cx, cy, rng.randint(2, 3), bounds=cave_bounds)


def _generate_river_delta(
    surface: Surface,
    rng: random.Random,
) -> None:
    """River Delta region (x=50..119, y=40..79): grass base with winding streams,
    organic lakes, and mineable banks."""
    x_min, y_min, x_max, y_max = 50, 40, 120, 80
    bounds = (x_min, y_min, x_max, y_max)

    # 1. Fill region with grass (replaces the previous deep-water fill)
    for y in range(y_min, y_max):
        for x in range(x_min, x_max):
            if not _is_town(x, y):
                _apply_tile(surface, x, y, TYPE_GRASS)

    # 2. Carve 2-3 streams crossing the region
    n_streams = rng.randint(2, 3)
    for _ in range(n_streams):
        # Pick start and end on opposite edges for through-flowing streams
        edge_pair = rng.choice(["lr", "tb", "diag1", "diag2"])
        if edge_pair == "lr":
            sx, sy = x_min, rng.randint(y_min + 2, y_max - 3)
            ex, ey = x_max - 1, rng.randint(y_min + 2, y_max - 3)
        elif edge_pair == "tb":
            sx, sy = rng.randint(x_min + 2, x_max - 3), y_min
            ex, ey = rng.randint(x_min + 2, x_max - 3), y_max - 1
        elif edge_pair == "diag1":
            sx, sy = x_min, y_min
            ex, ey = x_max - 1, y_max - 1
        else:
            sx, sy = x_max - 1, y_min
            ex, ey = x_min, y_max - 1
        _carve_stream(surface, rng, sx, sy, ex, ey, bounds=bounds)

    # 3. Carve 2-4 lakes
    n_lakes = rng.randint(2, 4)
    for _ in range(n_lakes):
        cx = rng.randint(x_min + 5, x_max - 6)
        cy = rng.randint(y_min + 5, y_max - 6)
        radius = rng.randint(3, 5)
        _carve_lake(surface, rng, cx, cy, radius, bounds=bounds)

    # 4. Convert grass adjacent to water into dirt banks
    _add_water_banks(surface, x_min, y_min, x_max, y_max)

    # 5. Scatter mineable patches on banks (~10%) and grass (~3%)
    _scatter_mineable(surface, rng, x_min, y_min, x_max, y_max, TYPE_DIRT, TYPE_MINEABLE_DIRT, 0.10)
    _scatter_mineable(
        surface, rng, x_min, y_min, x_max, y_max, TYPE_GRASS, TYPE_MINEABLE_GRASS, 0.03
    )


def _apply_cave_automata(surface: Surface) -> None:
    """Smooth the cave region with cellular automata to reduce isolated pockets.

    Runs 3 passes over cols 120-199. CAVE_WALL tiles that have fewer than 4 wall
    neighbours become CAVE_FLOOR (open up narrow choke points). CAVE_FLOOR tiles
    surrounded by 6+ walls become CAVE_WALL (fill tiny isolated holes). ORE and
    RICH_ORE tiles are never touched so the resource distribution is preserved.
    """
    cave_min_x = 120

    for _ in range(3):
        changes: dict = {}
        for y in range(MAP_HEIGHT):
            for x in range(cave_min_x, MAP_WIDTH):
                if _is_town(x, y):
                    continue
                current = surface.meta.get((x, y), {}).get("type", TYPE_CAVE_WALL)
                if current in (TYPE_ORE, TYPE_RICH_ORE):
                    continue  # preserve resource tiles

                wall_count = 0
                for dy in range(-1, 2):
                    for dx in range(-1, 2):
                        if dx == 0 and dy == 0:
                            continue
                        nx, ny = x + dx, y + dy
                        if nx < cave_min_x or nx >= MAP_WIDTH or ny < 0 or ny >= MAP_HEIGHT:
                            wall_count += 1
                        else:
                            n_type = surface.meta.get((nx, ny), {}).get("type", TYPE_CAVE_WALL)
                            if n_type == TYPE_CAVE_WALL:
                                wall_count += 1

                if current == TYPE_CAVE_WALL and wall_count < 4:
                    changes[(x, y)] = TYPE_CAVE_FLOOR
                elif current == TYPE_CAVE_FLOOR and wall_count > 5:
                    changes[(x, y)] = TYPE_CAVE_WALL

        for (x, y), type_name in changes.items():
            _apply_tile(surface, x, y, type_name)


def ensure_connectivity(surface: Surface, start_x: int, start_y: int) -> None:
    """BFS from start, then carve corridors to any disconnected walkable tile clusters.

    Repeats up to 50 passes. Each pass does a fresh BFS so that newly carved
    corridor tiles (and the cluster tile they connect) are found reachable on the
    next pass — avoiding the "start tile never added to reachable" edge case of
    purely incremental approaches.
    """

    def is_walkable(px: int, py: int) -> bool:
        return surface.meta.get((px, py), {}).get("walkable", False)

    if not is_walkable(start_x, start_y):
        return

    for _ in range(50):
        # Fresh BFS from the start to find all currently reachable tiles.
        reachable: set = set()
        q: deque = deque([(start_x, start_y)])
        reachable.add((start_x, start_y))
        while q:
            cx, cy = q.popleft()
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT:
                    if (nx, ny) not in reachable and is_walkable(nx, ny):
                        reachable.add((nx, ny))
                        q.append((nx, ny))

        unreachable = [
            (x, y)
            for (x, y), meta in surface.meta.items()
            if meta.get("walkable") and (x, y) not in reachable
        ]

        if not unreachable:
            break  # fully connected

        # Find the unreachable tile closest to any reachable tile.
        # Sample the reachable set (≤300 tiles) to keep this O(|unreachable| * 300).
        reachable_list = list(reachable)
        stride = max(1, len(reachable_list) // 300)
        sample = reachable_list[::stride]

        ux, uy = min(
            unreachable,
            key=lambda p: min(abs(p[0] - r[0]) + abs(p[1] - r[1]) for r in sample),
        )
        rx, ry = min(reachable, key=lambda p: abs(p[0] - ux) + abs(p[1] - uy))

        # Carve a straight-line corridor from (ux, uy) toward (rx, ry) using
        # biome-appropriate tiles so caves get cave floor, hillside gets dirt, etc.
        cx, cy = ux, uy
        while (cx, cy) != (rx, ry):
            if cx != rx:
                cx += 1 if rx > cx else -1
            elif cy != ry:
                cy += 1 if ry > cy else -1
            if not is_walkable(cx, cy):
                _apply_tile(surface, cx, cy, _biome_corridor_tile(cx, cy))
        # After this pass the next BFS will find (ux, uy) reachable because it is
        # now adjacent to a newly walkable corridor tile.


def _carve_bsp_band(
    surface: Surface,
    rng: random.Random,
    band_x: int,
    band_y: int,
    band_w: int,
    band_h: int,
    floor_tile: str,
    wall_tile: str,
    river_band: bool = False,
) -> None:
    root = BSPNode(x=band_x, y=band_y, width=band_w, height=band_h)
    split(root, rng, min_size=8)
    place_rooms(root, rng)

    for leaf in get_leaves(root):
        if leaf.room_x is None:
            continue
        for ry in range(leaf.room_y, leaf.room_y + leaf.room_h):
            for rx in range(leaf.room_x, leaf.room_x + leaf.room_w):
                if 0 <= rx < MAP_WIDTH and 0 <= ry < MAP_HEIGHT:
                    if river_band:
                        row_within_room = ry - leaf.room_y
                        tile = TYPE_SHALLOW if row_within_room % 2 == 0 else TYPE_BANK
                    else:
                        tile = floor_tile
                    _apply_tile(surface, rx, ry, tile)

    for x1, y1, x2, y2 in connect_rooms(root):
        cx = x1
        step = 1 if x2 >= x1 else -1
        while cx != x2:
            if 0 <= cx < MAP_WIDTH and 0 <= y1 < MAP_HEIGHT:
                _apply_tile(surface, cx, y1, _biome_corridor_tile(cx, y1))
            cx += step
        if 0 <= x2 < MAP_WIDTH and 0 <= y1 < MAP_HEIGHT:
            _apply_tile(surface, x2, y1, _biome_corridor_tile(x2, y1))

        cy = y1
        step = 1 if y2 >= y1 else -1
        while cy != y2:
            if 0 <= x2 < MAP_WIDTH and 0 <= cy < MAP_HEIGHT:
                _apply_tile(surface, x2, cy, _biome_corridor_tile(x2, cy))
            cy += step
        if 0 <= x2 < MAP_WIDTH and 0 <= y2 < MAP_HEIGHT:
            _apply_tile(surface, x2, y2, _biome_corridor_tile(x2, y2))


# Bump whenever a change to generation moves tiles for an existing seed: saved tile
# coordinates (depleted tiles, fog, picked-up gems) are only valid for this version.
WORLDGEN_VERSION = 1


def generate_world(seed: int) -> tuple[Surface, dict[tuple[int, int], str]]:
    """Generate the 200×80 procedural world.

    Returns a tuple of (surface, world_gems) where world_gems maps (x, y)
    coordinates to gem names for visible gems placed on the map.
    """
    rng = random.Random(seed)
    surface = Surface(MAP_WIDTH, MAP_HEIGHT)

    # Fill entire map with solid wall tiles by biome column band
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            if x <= 49:
                _apply_tile(surface, x, y, TYPE_TREE)
            elif x >= 120:
                _apply_tile(surface, x, y, TYPE_CAVE_WALL)
            elif y <= 39:
                _apply_tile(surface, x, y, TYPE_ROCK)
            else:
                _apply_tile(surface, x, y, TYPE_DEEP)

    # Meadow region: x [0, 49], y [0, 79] — grass clearings with scattered trees
    _generate_meadow(surface, rng)

    # Hillside region: x [50, 119], y [0, 39] — dirt with rocks and mineable patches
    _generate_hillside(surface, rng)

    # River Delta: x [50, 119], y [40, 79] — organic streams + lakes
    _generate_river_delta(surface, rng)

    # Cave band: x [120, 199], y [0, 79]
    _carve_bsp_band(
        surface,
        rng,
        band_x=120,
        band_y=0,
        band_w=80,
        band_h=80,
        floor_tile=TYPE_CAVE_FLOOR,
        wall_tile=TYPE_CAVE_WALL,
    )

    # Town perimeter: ring of PATH tiles around the town cluster
    for bx in range(TOWN_LEFT - 1, TOWN_RIGHT + 2):
        for by in range(TOWN_TOP - 1, TOWN_BOTTOM + 2):
            if not _is_town(bx, by) and 0 <= bx < MAP_WIDTH and 0 <= by < MAP_HEIGHT:
                _apply_tile(surface, bx, by, TYPE_PATH)

    # Town interior: buildings and ground tiles
    for by in range(TOWN_TOP, TOWN_BOTTOM + 1):
        for bx in range(TOWN_LEFT, TOWN_RIGHT + 1):
            if bx == SHOP_X and by == SHOP_Y:
                _apply_tile(surface, bx, by, TYPE_SHOP)
            elif bx == LAPIDARY_X and by == LAPIDARY_Y:
                _apply_tile(surface, bx, by, TYPE_LAPIDARY)
            elif bx == SAVE_X and by == SAVE_Y:
                _apply_tile(surface, bx, by, TYPE_SAVE)
            else:
                _apply_tile(surface, bx, by, TYPE_TOWN)

    # Cave cellular automata — smooth out isolated pockets
    _apply_cave_automata(surface)

    # Convert legacy cave ore tiles to mineable variants and scatter prospecting features
    _retile_cave_resources(surface, rng)

    # Connectivity check from town centre
    ensure_connectivity(surface, TOWN_CENTER_X, TOWN_CENTER_Y)

    surface.start_pos = (TOWN_CENTER_X, TOWN_CENTER_Y)

    # Visible gems on the map — placed in water tiles across all regions.
    # Each region uses its own biome for the gem table lookup.
    world_gems: dict[tuple[int, int], str] = {}
    region_gem_specs = [
        # (bounds, biome, density)
        ((0, 0, 50, 80), "meadow", 0.06),
        ((50, 0, 120, 40), "hillside", 0.06),
        ((50, 40, 120, 80), "river", 0.05),
        ((120, 0, 200, 80), "cave", 0.08),
    ]
    for bounds, biome, density in region_gem_specs:
        world_gems.update(
            _place_visible_gems(
                surface,
                rng,
                eligible_types=(TYPE_STREAM, TYPE_LAKE),
                region_bounds=bounds,
                biome=biome,
                density=density,
            )
        )

    return surface, world_gems
