"""Townsfolk: a few villagers who make the town feel lived in.

By day they wander the town square; at dusk they head home and stay in until dawn. When
the player stops beside one they greet them with a useful line, and two who meet chat
for a moment. They draw from their own random generator (gameplay rolls are unchanged)
and are not saved.
"""

import random

from game import daylight
from game.constants import TYPE_TOWN
from game.events import emit
from game.geography import in_town
from game.player import set_hud_message

GREET_COOLDOWN = 12.0
CHAT_COOLDOWN = 20.0
TALK = "talk"
TALK_COLOR = (235, 225, 200)
# id -> (name, glyph color, lines they say to the player, in turn)
VILLAGERS = {
    "ada": ("Ada the farmer", (120, 210, 110), [
        "Flowers grow thick where gems hide? Just a rumor.",
        "Dug-out ground grows back in a day or so.",
        "Rain brings the frogs and ducks out by the river.",
    ]),
    "bram": ("Bram the smith", (230, 120, 80), [
        "A better pickaxe finds rarer gems.",
        "Armor won't stop a bear, but it softens the blow.",
        "The Drill bites through any ground.",
    ]),
    "pip": ("Pip", (255, 220, 120), [
        "I saw a fox once! It ran so fast!",
        "The merchant's cart had a red roof!",
        "Fireflies only come out at night.",
    ]),
    "mo": ("Old Mo", (190, 190, 210), [
        "Don't sell all your gems at once. Prices drop.",
        "The museum pays you back, slowly.",
        "Deep in the caves the gems are worth the dark.",
    ]),
}  # fmt: skip
CHATTER = ["Morning!", "Fine day.", "Heard the news?", "Busy, busy."]


def _rng(state) -> random.Random:
    if state.town_rng is None:
        state.town_rng = random.Random(state.seed * 104729 + 3)
    return state.town_rng


def _homes(state) -> list:
    """A free square tile per villager, spread around the town."""
    meta = state.world_tiles.meta
    square = sorted(p for p, t in meta.items() if t["type"] == TYPE_TOWN and in_town(*p))
    step = max(1, len(square) // (len(VILLAGERS) + 1))
    return [square[step * (i + 1)] for i in range(len(VILLAGERS))] if square else []


def _out(state) -> bool:
    return daylight.phase(state)[0] in ("day", "dawn")


def update_townsfolk(state, dt: float) -> None:
    if state.world_tiles is None:
        return
    if not state.townsfolk:
        homes = _homes(state)
        state.townsfolk = [
            {"id": key, "x": x, "y": y, "home": (x, y), "timer": 0.0, "greet": 0.0, "chat": 0.0,
             "line": 0}
            for key, (x, y) in zip(VILLAGERS, homes, strict=False)
        ]  # fmt: skip
    rng = _rng(state)
    out = _out(state)
    meta = state.world_tiles.meta
    for v in state.townsfolk:
        v["greet"] = max(0.0, v["greet"] - dt)
        v["chat"] = max(0.0, v["chat"] - dt)
        if not out:
            v["x"], v["y"] = v["home"]  # indoors
            continue
        v["timer"] -= dt
        if v["timer"] <= 0:
            v["timer"] = rng.uniform(1.5, 3.0)
            if rng.random() < 0.5:
                dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
                nx, ny = v["x"] + dx, v["y"] + dy
                tile = meta.get((nx, ny))
                busy = (nx, ny) == (state.player_x, state.player_y) or any(
                    (o["x"], o["y"]) == (nx, ny) for o in state.townsfolk
                )
                if tile and tile["type"] == TYPE_TOWN and in_town(nx, ny) and not busy:
                    v["x"], v["y"] = nx, ny
        _talk(state, v)


def _talk(state, v) -> None:
    name, _, lines = VILLAGERS[v["id"]]
    near = max(abs(v["x"] - state.player_x), abs(v["y"] - state.player_y)) <= 1
    if near and v["greet"] <= 0:
        line = lines[v["line"] % len(lines)]
        v["line"] += 1
        v["greet"] = GREET_COOLDOWN
        set_hud_message(state, f'{name}: "{line}"', 4.0)
        emit(state, TALK, "Hi!", TALK_COLOR, at=(v["x"], v["y"]))
        return
    for other in state.townsfolk:
        meet = other is not v and max(abs(v["x"] - other["x"]), abs(v["y"] - other["y"])) <= 1
        if meet and v["chat"] <= 0 and other["chat"] <= 0:
            rng = _rng(state)
            emit(state, TALK, rng.choice(CHATTER), TALK_COLOR, at=(v["x"], v["y"]))
            v["chat"] = other["chat"] = CHAT_COOLDOWN


def render_townsfolk(renderer, state, view) -> None:
    from game.camera import OBJECT
    from game.daylight import shade, tint_at

    if not _out(state):
        return
    now = daylight.phase(state)
    for v in state.townsfolk:
        if not view.contains(v["x"], v["y"]):
            continue
        if state.world_tiles.meta.get((v["x"], v["y"]), {}).get("visibility") != "visible":
            continue
        light = tint_at(state, now, v["x"], v["y"])
        sx, sy = v["x"] - view.x, v["y"] - view.y
        color = (VILLAGERS[v["id"]][1], (40, 30, 0))
        renderer.set_cell(sx, sy, "☺", shade(color, light))
        renderer.set_sprite(sx, sy, OBJECT, f"villager_{v['id']}", light, entity=f"npc:{v['id']}")
