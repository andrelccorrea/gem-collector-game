"""Achievements: goals across a run, rewarded with reputation (spent on perks).

Every one can be unlocked, each has its own wording, and the reward grows with the
effort: easy goals pay 1 reputation, harder ones 2-3, winning 5. Unlocked achievements
live in the profile; the game scene checks them as the run goes on.
"""

from game import daylight
from game.events import ACHIEVE, emit
from game.geography import in_town
from game.objects.registry import ARMOR, BOOTS, CRITTERS, TOOL_CATALOG
from game.player import set_hud_message

GOLD = (255, 215, 90)


def _gems(state) -> dict:
    return state.inventory.get("gems", {})


# (id, name, description, reputation reward, condition)
ACHIEVEMENTS = [
    ("first_find", "First Glint", "Find your first gem",
     1, lambda s: any(n > 0 for n in _gems(s).values()) or s.lifetime_earnings > 0),
    ("night_walker", "Night Walker", "Be out of town at night",
     1, lambda s: daylight.phase(s)[0] == "night" and not in_town(s.player_x, s.player_y)),
    ("well_supplied", "Well Supplied", "Carry a Bandage and Lamp Oil at once",
     1, lambda s: s.supplies.get("bandage", 0) > 0 and s.supplies.get("lamp_oil", 0) > 0),
    ("prospector", "Prospector", "Earn $1,000 in one run",
     2, lambda s: s.lifetime_earnings >= 1000),
    ("cutting_edge", "Cutting Edge", "Own a polished gem",
     2, lambda s: any(k.endswith("_polished") and n > 0 for k, n in _gems(s).items())),
    ("bear_hunter", "Bear Hunter", "Carry a bear pelt",
     2, lambda s: s.inventory.get("loot", {}).get("bear_pelt", 0) > 0),
    ("curator", "Curator", "Donate 5 kinds of gems to the museum",
     2, lambda s: len(s.museum) >= 5),
    ("deep_delver", "Deep Delver", "Reach the far end of the caves",
     2, lambda s: s.player_x >= 185),
    ("field_notes", "Field Notes", "See 10 kinds of creatures",
     2, lambda s: len(s.seen_species) >= 10),
    ("naturalist", "Naturalist", "See every peaceful animal",
     3, lambda s: set(CRITTERS) <= s.seen_species),
    ("tycoon", "Tycoon", "Earn $5,000 in one run",
     3, lambda s: s.lifetime_earnings >= 5000),
    ("fully_geared", "Fully Geared", "Own every tool, the best armor and the best boots",
     3, lambda s: set(TOOL_CATALOG) <= set(s.inventory.get("tools", {}))
     and s.armor_level == len(ARMOR["costs"]) - 1
     and s.boots_level == len(BOOTS["costs"]) - 1),
    ("gem_legend", "Gem Legend", "Win a run",
     5, lambda s: s.has_won),
    ("iron_will", "Iron Will", "Win a Hardcore run",
     5, lambda s: s.has_won and s.hardcore),
]  # fmt: skip
BY_ID = {a[0]: a for a in ACHIEVEMENTS}


def newly_unlocked(state, unlocked: set) -> list:
    """Ids of achievements this state earns that are not in ``unlocked`` yet."""
    return [a[0] for a in ACHIEVEMENTS if a[0] not in unlocked and a[4](state)]


def announce(state, achievement_id: str) -> None:
    _, name, _, reward, _ = BY_ID[achievement_id]
    set_hud_message(state, f"Achievement: {name}! (+{reward} reputation)", 3.0)
    emit(state, ACHIEVE, name, GOLD, "gem", GOLD)
