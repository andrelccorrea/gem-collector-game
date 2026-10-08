"""Decorations: flowers, mushrooms, reeds... scattered over the ground, for looks only.

They are not stored anywhere: a deterministic hash of (seed, x, y) decides them when the
world is drawn, so world generation, saves and the simulation never change. Each kind
grows in patches (a coarse hash per block) and is rare outside them, which reads more
natural than uniform noise.
"""

from game.constants import TYPE_BANK, TYPE_CAVE_FLOOR, TYPE_DIRT, TYPE_GRASS, TYPE_SHALLOW

# base tile type -> [(decoration, chance per cell inside a patch, chance elsewhere)]
DECOR = {
    TYPE_GRASS: [("flowers", 0.16, 0.01), ("flowers_yellow", 0.10, 0.005)],
    TYPE_CAVE_FLOOR: [("mushroom", 0.10, 0.01), ("crystal", 0.03, 0.003)],
    TYPE_BANK: [("reeds", 0.30, 0.04)],
    TYPE_SHALLOW: [("lily", 0.12, 0.0)],
    TYPE_DIRT: [("pebbles", 0.08, 0.02)],
}
DECOR_NAMES = {
    "flowers": "wildflowers",
    "flowers_yellow": "buttercups",
    "mushroom": "glowcaps",
    "crystal": "crystals",
    "reeds": "reeds",
    "lily": "lily pads",
    "pebbles": "pebbles",
}
PATCH_W, PATCH_H = 7, 4  # cells per patch block (cells are about twice as tall as wide)
PATCH_SHARE = 0.35  # share of blocks that are patches


def stable_random(*values: int) -> float:
    """A stable pseudo-random number in [0, 1) for these integers."""
    h = 0x9E3779B1
    for v in values:
        h = ((h ^ (v & 0xFFFFFFFF)) * 0x85EBCA6B) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0xC2B2AE35) & 0xFFFFFFFF
        h ^= h >> 16
    return h / 2**32


_cache: dict = {}  # (seed, x, y, type) -> decoration


def decoration(seed: int, x: int, y: int, tile: dict) -> str | None:
    """The decoration on tile (x, y), or None. Worked-out tiles are bare."""
    if tile.get("depleted"):
        return None
    key = (seed, x, y, tile["type"])
    if key not in _cache:
        if len(_cache) > 50_000:  # another world: forget the old one
            _cache.clear()
        _cache[key] = _decide(seed, x, y, tile["type"])
    return _cache[key]


def _decide(seed: int, x: int, y: int, tile_type: str) -> str | None:
    options = DECOR.get(tile_type)
    if not options:
        return None
    roll = stable_random(seed, x, y)
    for i, (name, in_patch, elsewhere) in enumerate(options):
        patch = stable_random(seed, x // PATCH_W, y // PATCH_H, i + 1) < PATCH_SHARE
        chance = in_patch if patch else elsewhere
        if roll < chance:
            return name
        roll -= chance
    return None
