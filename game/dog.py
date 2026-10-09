"""Companion dog: follows the player and barks when an enemy comes near.

An early warning, not a guard: it barks at most every BARK_COOLDOWN seconds, so the
player can't lean on it completely. It never fights and enemies ignore it. Bought at
the shop for the run; its position is not saved (it appears beside the player).
"""

from game.constants import MAP_HEIGHT, MAP_WIDTH
from game.events import emit, emit_gem
from game.gems import add_gem_to_inventory, bag_has_room, roll_gem_drop
from game.geography import biome_at, in_town
from game.objects.registry import DOG_TRAINING
from game.player import set_hud_message

DOG_COST = 250
BARK = "bark"
BARK_RANGE = 8  # tiles (Chebyshev)
BARK_COOLDOWN = 10.0  # game seconds between barks
FOLLOW_DISTANCE = 2  # it stays within this many tiles
STEP_SECONDS = 0.12  # a little faster than the player, so it keeps up
LOST_DISTANCE = 12  # further than this (recall, load) and it simply turns up beside you
_STEPS = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)]


def _free(state, x: int, y: int) -> bool:
    if not (0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT):
        return False
    tile = state.world_tiles.meta.get((x, y))
    return bool(tile and tile["walkable"]) and (x, y) != (state.player_x, state.player_y)


def _distance(state) -> int:
    return max(abs(state.dog["x"] - state.player_x), abs(state.dog["y"] - state.player_y))


def _place_beside_player(state) -> None:
    for dx, dy in _STEPS:
        if _free(state, state.player_x + dx, state.player_y + dy):
            state.dog.update(x=state.player_x + dx, y=state.player_y + dy)
            return
    state.dog.update(x=state.player_x, y=state.player_y)


def update_dog(state, dt: float) -> None:
    if not state.has_dog or state.world_tiles is None:
        return
    if state.dog is None:
        state.dog = {"x": state.player_x, "y": state.player_y, "timer": 0.0, "bark": -1e9}
        _place_beside_player(state)
    dog = state.dog
    if _distance(state) > LOST_DISTANCE:
        _place_beside_player(state)
    dog["timer"] -= dt
    if dog["timer"] <= 0 and _distance(state) > FOLLOW_DISTANCE:
        dog["timer"] = STEP_SECONDS
        options = [(dog["x"] + dx, dog["y"] + dy) for dx, dy in _STEPS]
        options = [p for p in options if _free(state, *p)]
        if options:
            px, py = state.player_x, state.player_y
            dog["x"], dog["y"] = min(options, key=lambda p: max(abs(p[0] - px), abs(p[1] - py)))
    _fetch(state, dog)
    near = any(max(abs(e.x - dog["x"]), abs(e.y - dog["y"])) <= BARK_RANGE for e in state.enemies)
    if near and state.game_time - dog["bark"] >= BARK_COOLDOWN:
        dog["bark"] = state.game_time
        emit(state, BARK, "Woof!", (255, 240, 200), at=(dog["x"], dog["y"]))
        set_hud_message(state, "Your dog barks: something is coming!", 2.0)


def _fetch(state, dog) -> None:
    """A trained dog now and then digs something up where it stands."""
    level = state.dog_training
    if not level or in_town(dog["x"], dog["y"]):
        return
    dog.setdefault("fetch_at", state.game_time + DOG_TRAINING["interval"])
    if state.game_time < dog["fetch_at"]:
        return
    dog["fetch_at"] = state.game_time + DOG_TRAINING["interval"]
    if state.rng.random() >= DOG_TRAINING["chances"][level] or not bag_has_room(state):
        return
    gem = roll_gem_drop(biome_at(dog["x"], dog["y"]), DOG_TRAINING["tiers"][level], state.rng)
    if gem is None:
        return
    add_gem_to_inventory(state, gem)
    emit_gem(state, gem)
    state.events[-1] = state.events[-1]._replace(x=dog["x"], y=dog["y"])
    set_hud_message(state, f"Your dog dug up a {gem.replace('_', ' ').title()}!", 3.0)


def render_dog(renderer, state, view) -> None:
    from game import daylight
    from game.camera import OBJECT
    from game.daylight import shade, tint_at

    dog = state.dog
    if dog is None or not view.contains(dog["x"], dog["y"]):
        return
    if state.world_tiles.meta.get((dog["x"], dog["y"]), {}).get("visibility") != "visible":
        return
    light = tint_at(state, daylight.phase(state), dog["x"], dog["y"])
    sx, sy = dog["x"] - view.x, dog["y"] - view.y
    renderer.set_cell(sx, sy, "h", shade(((200, 150, 90), (0, 0, 0)), light))
    renderer.set_sprite(sx, sy, OBJECT, "dog", light, entity="dog")
