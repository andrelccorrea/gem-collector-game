"""Landmarks: a few remarkable spots per region (an old campfire, a mine cart...).

They help the player find their way, tell a line of the place's story and, on the first
visit of a run, sometimes hold a little gold. Their places come from a stable hash of
the seed (never the gameplay RNG), so a seed's world always has the same ones; they sit
on walkable ground and never change where anyone can walk.
"""

from game.constants import MAP_HEIGHT, MAP_WIDTH
from game.decor import stable_random
from game.events import GAIN_COLOR, LOOT, emit
from game.geography import biome_at, in_town

# kind -> (name, ground type, biome, how many, gold on the first visit, lore)
LANDMARKS = {
    "campfire": ("Old campfire", "grass", "meadow", 2, 10,
                 "Still warm. Someone camped here not long ago."),
    "tent": ("Torn tent", "grass", "meadow", 1, 0,
             "A diary inside: 'rubies glitter deep in the eastern caves'."),
    "well": ("Stone well", "grass", "meadow", 1, 25, "Coins glint at the bottom."),
    "cart": ("Mine cart", "dirt", "hillside", 2, 15,
             "Abandoned half full; a few coins rattle in a corner."),
    "statue": ("Weathered statue", "dirt", "hillside", 1, 0,
               "The town's founder, who found the first gem on this hill."),
    "boat": ("Wrecked boat", "bank", "river", 2, 15, "Its owner never came back for it."),
    "shrine": ("Crystal shrine", "cave_floor", "cave", 2, 20,
               "Miners left offerings here for luck below ground."),
}  # fmt: skip
SPACING = 15  # tiles between two landmarks (Chebyshev)
_cache: dict = {}


def landmarks(state) -> dict:
    """{(x, y): kind} for this world (computed once per world)."""
    key = (state.seed, id(state.world_tiles))
    if key not in _cache:
        _cache.clear()
        _cache[key] = _place(state)
    return _cache[key]


def _place(state) -> dict:
    meta = state.world_tiles.meta
    placed: dict = {}
    for k, (kind, (_, ground, biome, count, _, _)) in enumerate(LANDMARKS.items()):
        wanted = count
        for i in range(600):
            if not wanted:
                break
            x = int(stable_random(state.seed, k, i, 1) * MAP_WIDTH)
            y = int(stable_random(state.seed, k, i, 2) * MAP_HEIGHT)
            tile = meta.get((x, y))
            if tile is None or tile["type"] != ground or biome_at(x, y) != biome:
                continue
            if in_town(x, y, 3) or (x, y) in state.world_gems:
                continue
            if any(max(abs(x - px), abs(y - py)) < SPACING for px, py in placed):
                continue
            placed[(x, y)] = kind
            wanted -= 1
    return placed


def landmark_at(state, x: int, y: int):
    return landmarks(state).get((x, y)) if state.world_tiles is not None else None


def visit(state) -> None:
    """First visit of a run: tell the landmark's story and hand over its gold."""
    from game.player import set_hud_message  # player draws through camera, which needs us

    pos = (state.player_x, state.player_y)
    kind = landmark_at(state, *pos)
    if kind is None or pos in state.visited_landmarks:
        return
    state.visited_landmarks.add(pos)
    state.stats["landmarks"] = state.stats.get("landmarks", 0) + 1
    name, _, _, _, gold, lore = LANDMARKS[kind]
    found = f" You find {gold} gold." if gold else ""
    set_hud_message(state, f"{name}: {lore}{found}", 5.0)
    if gold:
        state.player_gold += gold
        emit(state, LOOT, f"+${gold}", GAIN_COLOR)
