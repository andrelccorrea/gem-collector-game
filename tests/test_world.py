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
        assert (
            tile_meta["visibility"] == "unseen"
        ), f"tile {key} has visibility={tile_meta['visibility']!r}, expected 'unseen'"


def test_generate_world_deterministic():
    surface_a, _ = generate_world(42)
    surface_b, _ = generate_world(42)

    assert set(surface_a.meta.keys()) == set(surface_b.meta.keys())

    for key in surface_a.meta:
        type_a = surface_a.meta[key]["type"]
        type_b = surface_b.meta[key]["type"]
        assert isinstance(type_a, str) and isinstance(
            type_b, str
        ), f"tile {key}: tile type is not a string (run1={type_a!r}, run2={type_b!r})"


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
        assert (
            tile_type in meadow_types
        ), f"Col=10, row={row}: expected meadow tile, got {tile_type!r}"

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
