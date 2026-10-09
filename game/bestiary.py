"""Bestiary: every creature the player has seen, kept in the profile across runs.

A first sighting is announced and remembered with where and when it happened (its
context of play). Seeing enough of them unlocks achievements.
"""

from game import daylight
from game.events import emit
from game.geography import region_name
from game.player import set_hud_message

ENTRIES = {
    "rabbit": ("Rabbit", "Nibbles clover by day; bolts in pairs."),
    "deer": ("Deer", "Grazes in small herds; spooks from far away."),
    "bird": ("Songbird", "Flocks over the meadow; hides from the rain."),
    "frog": ("Frog", "Croaks on the banks, loudest in the rain."),
    "fish": ("Fish", "Darts through streams and lakes."),
    "firefly": ("Firefly", "Lights up summer nights; fearless."),
    "beetle": ("Cave beetle", "Clicks along the cave floor."),
    "butterfly": ("Butterfly", "Flutters among the flowers on dry days."),
    "duck": ("Duck", "Paddles the river; loves a shower."),
    "owl": ("Owl", "A rare night hunter on the hills."),
    "fox": ("Fox", "Rarely seen, and never for long."),
    "goat": ("Goat", "Climbs the hillside in small herds."),
    "crab": ("Crab", "Scuttles sideways along the river banks."),
    "glowworm": ("Glowworm", "A living lantern deep in the caves."),
    "hedgehog": ("Hedgehog", "Snuffles about on wet nights; curls up when startled."),
    "squirrel": ("Squirrel", "Darts between the trees, hiding nuts."),
    "heron": ("Heron", "Stands patiently by the river; rarely lets you near."),
    "lizard": ("Lizard", "Basks on warm hillside rocks; hides from rain."),
    "snail": ("Snail", "Comes out in the rain. In no hurry at all."),
    "bear": ("Bear", "Dangerous. Its pelt sells well."),
    "cave_bat": ("Cave bat", "Dangerous. Swoops from the dark."),
    "snake": ("Snake", "Dangerous. Hides in the grass."),
}


def seen_now(state) -> set:
    """Kinds of creatures standing on visible tiles."""
    meta = state.world_tiles.meta if state.world_tiles is not None else {}
    names = set()
    for thing in [*state.critters, *state.enemies]:
        if meta.get((thing.x, thing.y), {}).get("visibility") == "visible":
            names.add(thing.name)
    return names & set(ENTRIES)


def context(state) -> str:
    """Where and when, e.g. "Meadow, at night"."""
    time_of_day = daylight.phase(state)[0]
    when = {"day": "by day", "dusk": "at dusk", "night": "at night", "dawn": "at dawn"}
    return f"{region_name(state.player_x, state.player_y)}, {when[time_of_day]}"


def announce(state, name: str, total_seen: int) -> None:
    set_hud_message(
        state, f"New in your bestiary: {ENTRIES[name][0]} ({total_seen}/{len(ENTRIES)})", 3.0
    )
    emit(state, "detect", "", (255, 230, 120))
