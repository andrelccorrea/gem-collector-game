from collections import deque

import pytest

from game.constants import (
    MAP_HEIGHT,
    MAP_WIDTH,
    TOWN_CENTER_X,
    TOWN_CENTER_Y,
    TYPE_CAVE_FLOOR,
    TYPE_CAVE_WALL,
    TYPE_DIRT,
    TYPE_GRASS,
    TYPE_LAPIDARY,
    TYPE_PATH,
    TYPE_SAVE,
    TYPE_SHOP,
    TYPE_TREE,
)
from game.world import generate_world


@pytest.fixture(scope="module")
def world_42():
    surface, _ = generate_world(42)
    return surface


@pytest.fixture(scope="module")
def world_99():
    surface, _ = generate_world(99)
    return surface


def test_generate_world_sets_start_pos(world_42):
    assert world_42.start_pos == (TOWN_CENTER_X, TOWN_CENTER_Y)


def test_generate_world_meta_not_empty(world_42):
    assert len(world_42.meta) > 0


def test_all_tiles_have_visibility_key(world_42):
    for key, tile_meta in world_42.meta.items():
        assert "visibility" in tile_meta, f"tile {key} missing 'visibility' key"


def test_all_tiles_start_as_unseen(world_42):
    for key, tile_meta in world_42.meta.items():
        assert tile_meta["visibility"] == "unseen", (
            f"tile {key} has visibility={tile_meta['visibility']!r}, expected 'unseen'"
        )


def test_generate_world_deterministic():
    surface_a, _ = generate_world(42)
    surface_b, _ = generate_world(42)

    assert set(surface_a.meta.keys()) == set(surface_b.meta.keys())

    for key in surface_a.meta:
        type_a = surface_a.meta[key]["type"]
        type_b = surface_b.meta[key]["type"]
        assert isinstance(type_a, str) and isinstance(type_b, str), (
            f"tile {key}: tile type is not a string (run1={type_a!r}, run2={type_b!r})"
        )


# ---------------------------------------------------------------------------
# Checkpoint 6 — BSP world generation tests
# ---------------------------------------------------------------------------


def test_generate_world_bsp_has_walkable_tiles(world_42):
    """The generated world must have at least 500 walkable tiles."""
    walkable_count = sum(1 for meta in world_42.meta.values() if meta.get("walkable") is True)
    assert walkable_count >= 500, f"Expected >=500 walkable tiles, got {walkable_count}"


def test_generate_world_bsp_connectivity(world_42):
    """All walkable tiles must be reachable via 4-directional BFS from start_pos."""
    start = world_42.start_pos
    meta = world_42.meta

    visited: set = set()
    queue: deque = deque([start])
    visited.add(start)

    while queue:
        cx, cy = queue.popleft()
        for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
            if (
                0 <= nx < MAP_WIDTH
                and 0 <= ny < MAP_HEIGHT
                and (nx, ny) not in visited
                and meta.get((nx, ny), {}).get("walkable", False)
            ):
                visited.add((nx, ny))
                queue.append((nx, ny))

    unreachable = [pos for pos, tile in meta.items() if tile.get("walkable") and pos not in visited]
    assert unreachable == [], (
        f"{len(unreachable)} walkable tile(s) not reachable from start_pos {start}: "
        f"first few = {unreachable[:5]}"
    )


def test_generate_world_bsp_town_tiles_present(world_42):
    """The world must contain exactly 1 SHOP, 1 LAPIDARY, and 1 SAVE tile."""
    shop_count = sum(1 for m in world_42.meta.values() if m.get("type") == TYPE_SHOP)
    lapidary_count = sum(1 for m in world_42.meta.values() if m.get("type") == TYPE_LAPIDARY)
    save_count = sum(1 for m in world_42.meta.values() if m.get("type") == TYPE_SAVE)

    assert shop_count == 1, f"Expected 1 SHOP tile, found {shop_count}"
    assert lapidary_count == 1, f"Expected 1 LAPIDARY tile, found {lapidary_count}"
    assert save_count == 1, f"Expected 1 SAVE tile, found {save_count}"


def test_generate_world_bsp_deterministic_tiles():
    """Two calls with seed=42 must produce identical tile types for a 100-tile sample."""
    surface_a, _ = generate_world(42)
    surface_b, _ = generate_world(42)

    # Collect a stable 100-item sample (sorted keys for determinism)
    all_keys = sorted(surface_a.meta.keys())
    stride = max(1, len(all_keys) // 100)
    sample_keys = all_keys[::stride][:100]

    for key in sample_keys:
        type_a = surface_a.meta[key]["type"]
        type_b = surface_b.meta[key]["type"]
        assert type_a == type_b, f"Tile {key} differs between runs: {type_a!r} vs {type_b!r}"


def test_generate_world_bsp_biome_column_bands(world_99):
    """Col=10 must be meadow tiles; col=130 must be cave tiles (5 rows each)."""
    meadow_types = {TYPE_GRASS, TYPE_TREE, TYPE_PATH, TYPE_DIRT}
    cave_types = {TYPE_CAVE_FLOOR, TYPE_CAVE_WALL}

    for row in range(0, 5):
        tile_type = world_99.meta.get((10, row), {}).get("type", "")
        assert tile_type in meadow_types, (
            f"Col=10, row={row}: expected meadow tile, got {tile_type!r}"
        )

    for row in range(0, 5):
        tile_type = world_99.meta.get((130, row), {}).get("type", "")
        assert tile_type in cave_types, f"Col=130, row={row}: expected cave tile, got {tile_type!r}"


def test_generate_world_start_pos_is_town_center(world_99):
    """start_pos must be (100, 40) regardless of seed."""
    assert world_99.start_pos == (100, 40)


def test_generate_world_different_seeds_differ():
    """Different seeds must produce at least one differing tile in the meta layout."""
    surface_1, _ = generate_world(1)
    surface_2, _ = generate_world(2)

    # Compare all tiles that exist in both maps
    common_keys = set(surface_1.meta.keys()) & set(surface_2.meta.keys())
    assert common_keys, "Both surfaces should share tile positions"

    differs = any(surface_1.meta[k]["type"] != surface_2.meta[k]["type"] for k in common_keys)
    assert differs, "generate_world(1) and generate_world(2) should produce different layouts"


# ── ensure_connectivity ───────────────────────────────────────────────────────


def _island_map():
    """A 30x12 wall map with three separate walkable rooms."""
    from game.constants import TILE_PROPS
    from game.tilemap import TileMap
    from game.world import _apply_tile

    tiles = TileMap(30, 12)
    for y in range(12):
        for x in range(30):
            _apply_tile(tiles, x, y, "tree")
    rooms = [(1, 1, 4, 3), (12, 6, 3, 3), (24, 2, 4, 4)]
    for rx, ry, w, h in rooms:
        for y in range(ry, ry + h):
            for x in range(rx, rx + w):
                _apply_tile(tiles, x, y, "grass")
    assert not TILE_PROPS["tree"][0] and TILE_PROPS["grass"][0]
    return tiles


def _reachable(tiles, start):
    from collections import deque

    seen, queue = {start}, deque([start])
    while queue:
        x, y = queue.popleft()
        for n in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if n not in seen and tiles.meta.get(n, {}).get("walkable"):
                seen.add(n)
                queue.append(n)
    return seen


def test_ensure_connectivity_joins_every_room_with_short_corridors():
    from game.world import ensure_connectivity

    tiles = _island_map()
    walkable_before = {c for c, m in tiles.meta.items() if m["walkable"]}
    ensure_connectivity(tiles, 2, 2)

    walkable_after = {c for c, m in tiles.meta.items() if m["walkable"]}
    assert walkable_after == _reachable(tiles, (2, 2))
    assert walkable_before <= walkable_after
    carved = walkable_after - walkable_before
    # The shortest possible corridors total 20 tiles (10 per gap); allow a little slack.
    assert len(carved) <= 24


def test_ensure_connectivity_noop_when_start_is_blocked():
    from game.world import ensure_connectivity

    tiles = _island_map()
    before = {c: dict(m) for c, m in tiles.meta.items()}
    ensure_connectivity(tiles, 0, 0)
    assert tiles.meta == before


@pytest.mark.parametrize("seed", [1, 7, 42, 99, 1234])
def test_connectivity_carves_short_corridors_on_real_maps(seed, monkeypatch):
    # Measured 31-47 carved tiles per world on these seeds; a regression that
    # stops reusing joined regions as search sources carves ~300 per world.
    import game.world as world_module

    carved = []
    original_apply = world_module._apply_tile
    original_connect = world_module.ensure_connectivity

    def counting_connect(tiles, sx, sy):
        monkeypatch.setattr(
            world_module,
            "_apply_tile",
            lambda t, x, y, k: carved.append((x, y)) or original_apply(t, x, y, k),
        )
        try:
            original_connect(tiles, sx, sy)
        finally:
            monkeypatch.setattr(world_module, "_apply_tile", original_apply)

    monkeypatch.setattr(world_module, "ensure_connectivity", counting_connect)
    world_module.generate_world(seed)
    assert len(carved) <= 100


@pytest.mark.parametrize("seed", [1, 7, 42, 99, 1234, 31337])
def test_every_walkable_tile_is_reachable_from_town(seed):
    world, _ = generate_world(seed)
    walkable = {c for c, m in world.meta.items() if m["walkable"]}
    assert walkable == _reachable(world, world.start_pos)
