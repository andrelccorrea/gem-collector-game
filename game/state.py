from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class GameState:
    # Scene management
    active_scene: str = "menu"
    menu_cursor: int = 0
    has_won: bool = False

    # Map
    seed: int = 0
    world_tiles: Any = None  # Surface object, set after generation

    # Player position
    player_x: int = 100
    player_y: int = 40

    # Player stats
    player_hp: int = 20
    player_max_hp: int = 20
    player_gold: int = 50
    lifetime_earnings: int = 0
    equipped_tool: Optional[str] = None

    # Inventory: {"gems": {"quartz": 2, ...}, "tools": {"shovel": {"level": 1}}, "loot": {...}}
    inventory: dict = field(
        default_factory=lambda: {
            "gems": {},
            "tools": {"shovel": {"level": 1}},
            "loot": {},
        }
    )

    # Camera
    camera_x: int = 0
    camera_y: int = 0

    # Enemies (list of dicts)
    enemies: list = field(default_factory=list)

    # Timers
    spawn_timer: float = 0.0
    regen_timer: float = 0.0
    move_cooldown: float = 0.0
    last_combat_time: float = 0.0

    # Difficulty
    difficulty_level: int = 0

    # Depleted tiles: set of (x, y) tuples
    depleted_tiles: set = field(default_factory=set)

    # Visible gems on the map: (x, y) -> gem_name (string)
    world_gems: dict = field(default_factory=dict)

    # Fog of war: set of (x, y) coords currently marked "visible"
    visible_tiles: set = field(default_factory=set)
    respawn_timers: dict = field(default_factory=dict)  # (x,y) -> ticks_remaining

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
