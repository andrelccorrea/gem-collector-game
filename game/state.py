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
    quit_requested: bool = False
    menu_notice: str = ""  # one-off message shown on the main menu

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

    # Visible gems on the map: (x, y) -> gem_name (string)
    world_gems: dict = field(default_factory=dict)

    # Fog of war: set of (x, y) coords currently marked "visible"
    visible_tiles: set = field(default_factory=set)

    # Lapidary level
    lapidary_level: int = 1

    # HUD message (temporary notification)
    hud_message: str = ""
    hud_message_timer: float = 0.0

    # Shop/Lapidary sub-scene state
    shop_cursor: int = 0
    shop_tab: int = 0  # 0=buy_tools, 1=upgrade_tools, 2=sell_gems, 3=sell_loot
    lapidary_cursor: int = 0

    # Polished gem sell prices: "quartz_polished" -> int value
    polished_gem_values: dict = field(default_factory=dict)
