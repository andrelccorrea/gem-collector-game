import random
from dataclasses import dataclass, field
from typing import Any


def gameplay_rng(seed: int) -> random.Random:
    """RNG for gameplay rolls (drops, polishing, spawns) of the run with this seed.

    Derived from the seed but independent of the world-generation stream, so the
    same seed always yields the same world and the same sequence of rolls.
    """
    return random.Random(f"{seed}:gameplay")


@dataclass
class GameState:
    # Scene management
    active_scene: str = "menu"
    menu_cursor: int = 0
    has_won: bool = False
    run_id: str = ""  # identifies a run across saves (rewards are paid once per run)
    hardcore: bool = False  # death ends the run (and erases its save)
    daily: str | None = None  # ISO date of a daily run (time-limited, never saved)
    quit_requested: bool = False
    menu_notice: str = ""  # one-off message shown on the main menu
    perks_cursor: int = 0

    # Map
    seed: int = 0
    # Every gameplay roll must use this RNG (never the global `random` module).
    rng: random.Random = field(default_factory=lambda: gameplay_rng(0))
    world_tiles: Any = None  # TileMap, set after generation

    # Player position
    player_x: int = 100
    player_y: int = 40

    # Player stats
    player_hp: int = 20
    player_max_hp: int = 20
    player_gold: int = 50
    lifetime_earnings: int = 0
    equipped_tool: str | None = None

    # Inventory: {"gems": {"quartz": 2, ...}, "tools": {"shovel": {"level": 1}}, "loot": {...}}
    inventory: dict = field(
        default_factory=lambda: {
            "gems": {},
            "tools": {"shovel": {"level": 1}},
            "loot": {},
        }
    )

    # Top-left corner of the simulation view (constants.VIEW_WIDTH x VIEW_HEIGHT)
    camera_x: int = 0
    camera_y: int = 0

    # Enemies (list of dicts)
    enemies: list = field(default_factory=list)

    # Timers
    spawn_timer: float = 0.0
    regen_timer: float = 0.0
    move_cooldown: float = 0.0
    last_move: Any = None  # Action of the last step taken
    queued_move: Any = None  # direction change pressed during the move cooldown
    # Seconds of in-game time; advances only while the game scene is simulated.
    game_time: float = 0.0
    last_combat_time: float = float("-inf")
    last_attack_time: float = float("-inf")

    # Depleted tiles: set of (x, y) tuples
    depleted_tiles: set = field(default_factory=set)
    depleted_at: dict = field(default_factory=dict)  # tile -> game time worked out (regrow.py)
    tiles_version: int = 0  # bumped whenever a tile changes (drawing caches key on it)

    # Visible gems on the map: (x, y) -> gem_name (string)
    world_gems: dict = field(default_factory=dict)

    # Fog of war: set of (x, y) coords currently marked "visible"
    visible_tiles: set = field(default_factory=set)
    # (x, y, radius) the fog was last computed for; None forces a recompute
    fog_key: Any = None

    # Shop saturation per item kind (sales recently made); see game/market.py
    market: dict = field(default_factory=dict)

    # Everything carried when the player last died: {"x", "y", "gems", "loot", "polished"}
    dropped_bag: Any = None

    recall_charms: int = 0
    # Consumables by key ("bandage", "lamp_oil"), see game/supplies.py
    supplies: dict = field(default_factory=dict)
    museum: list = field(default_factory=list)  # gem kinds donated, in donation order

    # Lantern: fuel left (seconds of light at drain 1) and upgrade level
    lantern_fuel: float = 240.0
    lantern_level: int = 0

    # Bag upgrade level (index into the catalog's bag capacities)
    bag_level: int = 0
    # Armor and boots levels (indexes into the catalog's armor / boots tables)
    armor_level: int = 0
    boots_level: int = 0
    dowsing_level: int = 0
    has_dog: bool = False
    dog_training: int = 0  # level in catalogs.toml [dog_training]
    trinkets: list = field(default_factory=list)  # owned this run
    trinket: Any = None  # the one worn (key) or None
    feather_day: int = -1  # last game day the Homing Feather was used
    merchant_log: list = field(default_factory=list)  # [day, offer or "sell"] trades
    visited_landmarks: set = field(default_factory=set)  # (x, y) of landmarks seen this run
    contracts_done: set = field(default_factory=set)  # (game day, board slot) delivered
    stats: dict = field(default_factory=dict)  # this run's counters (game/stats.py); not saved
    dog: Any = None  # {"x", "y", "timer", "bark"} while it follows (game/dog.py); not saved
    dowse_tier: Any = None  # last hot/cold tier of the rod (game/dowsing.py); not saved
    # Run-long bonuses from perks bought between runs (game/profile.py)
    bag_bonus: int = 0
    lantern_bonus: float = 0.0

    # Lapidary level
    lapidary_level: int = 1

    # HUD message (temporary notification)
    hud_message: str = ""
    hud_message_timer: float = 0.0
    # First-time tips already shown (game/tips.py), kept in the profile, and when the
    # last one was shown
    tips_seen: set = field(default_factory=set)
    # Outfit worn (cosmetic, kept in the profile; loaded by the game scene)
    outfit: str = "prospector"
    # Creature kinds in the profile's bestiary (loaded by the game scene)
    seen_species: set = field(default_factory=set)
    last_tip_time: float = float("-inf")
    # Peaceful animals (game/critters.py) and their own RNG; never saved
    critters: list = field(default_factory=list)
    townsfolk: list = field(default_factory=list)  # villagers (game/townsfolk.py); not saved
    town_rng: Any = None
    still_for: float = 0.0  # seconds since the player last stepped (animals trust stillness)
    friends: set = field(default_factory=set)  # species befriended (kept in the profile)
    goal: int = 0  # index of the current starter goal (game/goals.py; kept in the profile)
    critter_rng: Any = None
    critter_timer: float = 0.0
    # World events not yet shown by the frontend (game/events.py); never saved
    events: list = field(default_factory=list)

    # Shop/Lapidary sub-scene state
    shop_cursor: int = 0
    shop_tab: int = 0  # 0=buy_tools, 1=upgrade_tools, 2=sell_gems, 3=sell_loot
    lapidary_cursor: int = 0
    cut_streak: int = 0  # consecutive Excellent-or-better cuts (not saved)
    cut_result: Any = None  # the last cut, shown for a moment: {"text", "position", ...}

    # Gem being cut in the lapidary minigame: {"gem": name, "elapsed": seconds} or None
    cutting: Any = None

    # Polished gem sell prices: "quartz_polished" -> int value
    polished_gem_values: dict = field(default_factory=dict)
