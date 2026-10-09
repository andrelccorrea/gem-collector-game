"""Peaceful animals that make the world feel alive: rabbits, deer, birds, frogs, fish,
fireflies and cave beetles (catalogs.toml [[critters]]).

They never attack. Each wanders slowly and bolts when the player comes within its flee
range, faster than the player walks; when one bolts, its herd mates nearby bolt too.
Day animals only appear by day, fireflies only at night.

They draw from their own random generator, so gameplay rolls (``state.rng``) are the
same with or without them, and they are not saved: a loaded game spawns new ones.
"""

import random
from dataclasses import dataclass

from game import daylight, weather
from game.camera import OBJECT
from game.constants import (
    MAP_HEIGHT,
    MAP_WIDTH,
    TYPE_DEEP,
    TYPE_LAKE,
    TYPE_SHALLOW,
    TYPE_STREAM,
)
from game.daylight import mix, shade, tint_at
from game.events import emit
from game.geography import biome_at, in_town
from game.objects.registry import CRITTERS
from game.player import set_hud_message

MAX_CRITTERS = 10
SPAWN_INTERVAL = 2.0  # game seconds between spawn attempts
SPAWN_MIN, SPAWN_MAX = 8, 24  # distance from the player (Chebyshev) of a new herd
DESPAWN_DISTANCE = 32
FLEE_SECONDS = 2.0  # how long a scared animal keeps running once out of range
HERD_RADIUS = 4  # herd mates this close bolt together
HERD_SPREAD = 3  # a herd member farther than this from its mates walks back to them
FLOWN_OFF = 10  # a startled flier this far from the player has left for good
JUMP_CHANCE = 0.04  # per wander step of a jumping fish
SPLASH = "splash"
SPOOK, PET = "spook", "pet"
STILL_CALM = 1.5  # seconds standing still before animals let the player near
FRIEND_TRUST = 3  # pets that befriend a species
WATER = {TYPE_STREAM, TYPE_LAKE, TYPE_SHALLOW, TYPE_DEEP}
_STEPS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]


@dataclass
class Critter:
    name: str
    x: int
    y: int
    move_timer: float = 0.0
    scared: float = 0.0  # seconds of fleeing left
    trust: int = 0  # times petted; a petted animal no longer runs from the player

    @property
    def kind(self) -> dict:
        return CRITTERS[self.name]


def _rng(state) -> random.Random:
    if state.critter_rng is None:
        state.critter_rng = random.Random(state.seed * 7919 + 17)
    return state.critter_rng


def _can_stand(state, x: int, y: int, habitat: str) -> bool:
    if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT) or in_town(x, y, 2):
        return False
    tile = state.world_tiles.meta.get((x, y))
    if tile is None:
        return False
    if habitat == "water":
        return tile["type"] in WATER
    return tile["walkable"] and tile["type"] not in WATER


def _occupied(state, x: int, y: int) -> bool:
    return (
        (x, y) == (state.player_x, state.player_y)
        or any((e.x, e.y) == (x, y) for e in state.enemies)
        or any((c.x, c.y) == (x, y) for c in state.critters)
    )


def _species_for(state, x: int, y: int, rng: random.Random) -> str | None:
    time_of_day = daylight.phase(state)[0]
    awake = "night" if time_of_day == "night" else "day"
    raining = weather.is_raining(state)
    names, weights = [], []
    for name, kind in CRITTERS.items():
        if biome_at(x, y) not in kind["biomes"] or kind["active"] not in (awake, "any"):
            continue
        if raining and kind.get("rain") == "avoids":
            continue
        names.append(name)
        likes_rain = raining and kind.get("rain") == "likes"
        weights.append(kind.get("weight", 1.0) * (2 if likes_rain else 1))
    return rng.choices(names, weights)[0] if names else None


def _spawn(state, rng: random.Random) -> None:
    px, py = state.player_x, state.player_y
    for _ in range(10):
        x = px + rng.choice((-1, 1)) * rng.randint(SPAWN_MIN, SPAWN_MAX)
        y = py + rng.randint(-SPAWN_MAX // 2, SPAWN_MAX // 2)
        name = _species_for(state, x, y, rng) if 0 <= x < MAP_WIDTH else None
        if name is None:
            continue
        kind = CRITTERS[name]
        # Appear only where the player cannot see them pop in.
        tile = state.world_tiles.meta.get((x, y))
        if tile is None or tile["visibility"] == "visible":
            continue
        if not _can_stand(state, x, y, kind["habitat"]) or _occupied(state, x, y):
            continue
        for i in range(rng.randint(*kind["herd"])):
            hx, hy = (x, y) if i == 0 else (x + rng.randint(-2, 2), y + rng.randint(-1, 1))
            if len(state.critters) < MAX_CRITTERS and _can_stand(state, hx, hy, kind["habitat"]):
                if not _occupied(state, hx, hy):
                    state.critters.append(Critter(name, hx, hy, rng.uniform(0, 1)))
        return


def _step(state, critter: Critter, rng: random.Random) -> None:
    kind = critter.kind
    flying = critter.scared > 0 and kind.get("flies")
    options = [
        (critter.x + dx, critter.y + dy)
        for dx, dy in _STEPS
        if (_in_map(critter.x + dx, critter.y + dy) if flying
            else _can_stand(state, critter.x + dx, critter.y + dy, kind["habitat"]))
        and not _occupied(state, critter.x + dx, critter.y + dy)
    ]  # fmt: skip
    if not options:
        return
    if critter.scared > 0 and kind.get("curls"):
        return  # rolled into a ball: it waits it out
    if critter.scared > 0:  # run (or fly): the step that gets furthest from the player
        px, py = state.player_x, state.player_y
        critter.x, critter.y = max(options, key=lambda p: max(abs(p[0] - px), abs(p[1] - py)))
        return
    center = _herd_center(state, critter)
    if center is not None:  # strayed from its herd: head back (cohesion)
        critter.x, critter.y = min(options, key=lambda p: max(abs(p[0] - center[0]),
                                                              abs(p[1] - center[1])))  # fmt: skip
    elif rng.random() < 0.6:  # wander, or just graze in place
        critter.x, critter.y = rng.choice(options)
    if kind.get("jumps") and rng.random() < JUMP_CHANCE:
        emit(state, SPLASH, "", (150, 200, 255), at=(critter.x, critter.y))


def _near(critter: Critter, x: int, y: int, reach: int) -> bool:
    return max(abs(critter.x - x), abs(critter.y - y)) <= reach


def pet(state) -> bool:
    """Use beside a calm animal: pet it. Returns whether an animal was petted."""
    px, py = state.player_x, state.player_y
    calm = [c for c in state.critters if c.scared <= 0 and _near(c, px, py, 1)]
    if not calm:
        return False
    critter = calm[0]
    critter.trust += 1
    name = critter.name.replace("_", " ")
    if critter.trust >= FRIEND_TRUST and critter.name not in state.friends:
        state.friends.add(critter.name)
        set_hud_message(state, f"The {name} trusts you now! (friends: {len(state.friends)})", 3.0)
        emit(state, PET, "Friend!", (255, 150, 190), "heart", at=(critter.x, critter.y))
    else:
        set_hud_message(state, f"You pet the {name}.", 1.5)
        emit(state, PET, "", (255, 150, 190), at=(critter.x, critter.y))
    return True


def _in_map(x: int, y: int) -> bool:
    return 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT


def _herd_center(state, critter: Critter):
    """The middle of its herd mates nearby, when it is more than HERD_SPREAD from it."""
    mates = [c for c in state.critters if c is not critter and c.name == critter.name
             and max(abs(c.x - critter.x), abs(c.y - critter.y)) <= HERD_RADIUS * 2]  # fmt: skip
    if not mates:
        return None
    cx = round(sum(c.x for c in mates) / len(mates))
    cy = round(sum(c.y for c in mates) / len(mates))
    if max(abs(cx - critter.x), abs(cy - critter.y)) <= HERD_SPREAD:
        return None
    return cx, cy


def update_critters(state, dt: float) -> None:
    """Spawn, scare, move and despawn the animals around the player."""
    if state.world_tiles is None:
        return
    rng = _rng(state)
    state.critter_timer += dt
    if state.critter_timer >= SPAWN_INTERVAL:
        state.critter_timer = 0.0
        if len(state.critters) < MAX_CRITTERS:
            _spawn(state, rng)

    px, py = state.player_x, state.player_y
    for critter in state.critters:
        reach = critter.kind["flee_range"]
        patient = state.still_for >= STILL_CALM  # a player standing still spooks nothing
        if reach and not patient and not critter.trust and _near(critter, px, py, reach):
            if critter.scared <= 0:
                emit(state, SPOOK, "!", (255, 230, 120), at=(critter.x, critter.y))
            for mate in state.critters:  # the herd bolts together
                near = max(abs(mate.x - critter.x), abs(mate.y - critter.y)) <= HERD_RADIUS
                if mate.name == critter.name and near and not mate.trust:
                    mate.scared = FLEE_SECONDS
    for critter in state.critters:
        critter.scared = max(0.0, critter.scared - dt)
        critter.move_timer -= dt
        if critter.move_timer <= 0:
            kind = critter.kind
            critter.move_timer = kind["flee_seconds"] if critter.scared else kind["wander_seconds"]
            _step(state, critter, rng)
    state.critters = [
        c
        for c in state.critters
        if max(abs(c.x - px), abs(c.y - py)) <= DESPAWN_DISTANCE
        and not (c.scared > 0 and c.kind.get("flies")
                 and max(abs(c.x - px), abs(c.y - py)) >= FLOWN_OFF)
    ]  # fmt: skip


def render_critters(renderer, state, view) -> None:
    now = daylight.phase(state)
    meta = state.world_tiles.meta
    for critter in state.critters:
        if not view.contains(critter.x, critter.y):
            continue
        if meta.get((critter.x, critter.y), {}).get("visibility") != "visible":
            continue
        kind = critter.kind
        sx, sy = critter.x - view.x, critter.y - view.y
        # Glowing animals (fireflies, glowworms): the dark does not dim them.
        light = None if kind.get("glow") else tint_at(state, now, critter.x, critter.y)
        color = (tuple(kind["color"][0]), tuple(kind["color"][1]))
        renderer.set_cell(sx, sy, kind["char"], shade(color, light))
        sprite = critter.name
        if kind.get("curls") and critter.scared > 0:
            sprite = f"{critter.name}_curled"
        renderer.set_sprite(sx, sy, OBJECT, sprite, mix(None, light), entity=id(critter))
