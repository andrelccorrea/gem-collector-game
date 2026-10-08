# Map dimensions
MAP_WIDTH = 200
MAP_HEIGHT = 80

# Window/Viewport
WINDOW_WIDTH = 80
WINDOW_HEIGHT = 24
HUD_ROWS = 3  # status rows below the world view
# The simulation's view of the world, centered on the player. Enemies spawn outside it,
# so it is fixed (never derived from a device's screen) to keep runs reproducible.
# Frontends draw a view of at most this size, so spawns are never in sight.
VIEW_WIDTH = 79
VIEW_HEIGHT = 21
FPS = 30
FOG_RADIUS: int = 8

# Player defaults
PLAYER_START_HP = 20
PLAYER_START_GOLD = 50
PLAYER_CHAR = "☻"
HP_REGEN_RATE = 1  # HP per 10 seconds in town
HP_REGEN_INTERVAL = 10.0  # seconds

# Win condition
WIN_LIFETIME_EARNINGS = 10000

# Movement step cooldown
MOVE_COOLDOWN = 0.15
# Recall charm: one-use teleport back to town, sold at the shop.
RECALL_CHARM_COST = 35

# Minimum game time between player attacks (holding F auto-repeats the key).
PLAYER_ATTACK_COOLDOWN = 0.35

# Town center (in map coordinates)
TOWN_CENTER_X = 100
TOWN_CENTER_Y = 40

# Town building positions (relative offsets from town center)
SHOP_X = TOWN_CENTER_X - 2
SHOP_Y = TOWN_CENTER_Y
LAPIDARY_X = TOWN_CENTER_X + 2
LAPIDARY_Y = TOWN_CENTER_Y
SAVE_X = TOWN_CENTER_X
SAVE_Y = TOWN_CENTER_Y + 2

# Biome boundaries (x range for biome detection)
BIOME_MEADOW_MAX_X = 49
BIOME_CAVE_MIN_X = 120
BIOME_HILLSIDE_MAX_Y = 39  # upper center

# Enemy config
MAX_ENEMIES_BASE = 8
ENEMY_SPAWN_INTERVAL = 5.0  # seconds between spawn attempts
ENEMY_PATH_RECALC_INTERVAL = 0.5  # seconds
ENEMY_MAX_DISTANCE = 60  # despawn if farther than this

# Color palettes - all as ((fg_r,fg_g,fg_b),(bg_r,bg_g,bg_b))
# Biomes
COLOR_MEADOW = ((100, 200, 100), (0, 30, 0))  # green on dark green
COLOR_HILLSIDE = ((180, 180, 180), (40, 40, 40))  # gray on dark gray
COLOR_RIVER = ((100, 180, 255), (0, 0, 80))  # light blue on dark blue
COLOR_CAVE = ((120, 80, 40), (10, 10, 10))  # brown on near-black
COLOR_TOWN = ((255, 220, 100), (40, 30, 0))  # gold on dark brown

# Players/Entities
COLOR_PLAYER = ((255, 255, 255), (0, 0, 0))  # white on black

# UI
COLOR_HUD_BG = ((200, 200, 200), (0, 0, 60))  # light text on dark blue
COLOR_HUD_HP_HIGH = ((0, 220, 0), (0, 0, 60))  # green HP
COLOR_HUD_HP_MID = ((220, 180, 0), (0, 0, 60))  # yellow HP
COLOR_HUD_HP_LOW = ((220, 0, 0), (0, 0, 60))  # red HP
COLOR_MENU_TITLE = ((255, 200, 0), (0, 0, 0))  # gold on black
COLOR_MENU_SELECTED = ((0, 0, 0), (255, 200, 0))  # black on gold (inverted)
COLOR_MENU_NORMAL = ((200, 200, 200), (0, 0, 0))  # light gray
COLOR_MENU_DIMMED = ((80, 80, 80), (0, 0, 0))  # dark gray (disabled)
COLOR_BUILDING = ((255, 200, 0), (60, 40, 0))  # gold on dark brown

# Tile characters — floor tiles use space (color-only), objects use single-width Unicode
# glyphs (theme.ASCII_FALLBACK maps them back to ASCII for terminals without UTF-8)
CHAR_GRASS = " "
CHAR_TREE = "♣"
CHAR_PATH = " "
CHAR_ROCK = "▲"
CHAR_ORE = "◇"
CHAR_DIRT = " "
CHAR_SHALLOW = " "
CHAR_BANK = " "
CHAR_DEEP = " "
CHAR_CAVE_FLOOR = " "
CHAR_CAVE_WALL = "▓"
CHAR_RICH_ORE = "◈"
CHAR_DEPLETED = "·"
CHAR_TOWN_GROUND = " "
CHAR_SHOP = "S"
CHAR_LAPIDARY = "L"
CHAR_SAVE = "P"
# Prospecting tiles — subtle visual hints + water bodies
CHAR_MINEABLE_GRASS = '"'
CHAR_MINEABLE_DIRT = "∴"
CHAR_MINEABLE_ROCK = "░"
CHAR_STREAM = "≈"
CHAR_LAKE = " "

# Tile types
TYPE_GRASS = "grass"
TYPE_TREE = "tree"
TYPE_PATH = "path"
TYPE_ROCK = "rock"
TYPE_ORE = "ore"
TYPE_DIRT = "dirt"
TYPE_SHALLOW = "shallow"
TYPE_BANK = "bank"
TYPE_DEEP = "deep"
TYPE_CAVE_FLOOR = "cave_floor"
TYPE_CAVE_WALL = "cave_wall"
TYPE_RICH_ORE = "rich_ore"
TYPE_TOWN = "town"
TYPE_SHOP = "shop"
TYPE_LAPIDARY = "lapidary"
TYPE_SAVE = "save"
TYPE_MINEABLE_GRASS = "mineable_grass"
TYPE_MINEABLE_DIRT = "mineable_dirt"
TYPE_MINEABLE_ROCK = "mineable_rock"
TYPE_STREAM = "stream"
TYPE_LAKE = "lake"

# Tile definitions: type -> (char, color_pair, walkable, interactable)
# Tile types that block line of sight (fog of war)
OPAQUE_TILE_TYPES = frozenset({TYPE_TREE, TYPE_ROCK, TYPE_CAVE_WALL})

# Gameplay properties per tile type: (walkable, interactable). Appearance lives in theme.py.
TILE_PROPS = {
    TYPE_GRASS: (True, False),
    TYPE_TREE: (False, False),
    TYPE_PATH: (True, False),
    TYPE_ROCK: (False, False),
    TYPE_ORE: (True, True),
    TYPE_DIRT: (True, False),
    TYPE_SHALLOW: (True, True),
    TYPE_BANK: (True, False),
    TYPE_DEEP: (False, False),
    TYPE_CAVE_FLOOR: (True, False),
    TYPE_CAVE_WALL: (False, False),
    TYPE_RICH_ORE: (True, True),
    TYPE_TOWN: (True, False),
    TYPE_SHOP: (True, True),
    TYPE_LAPIDARY: (True, True),
    TYPE_SAVE: (True, True),
    TYPE_MINEABLE_GRASS: (True, True),
    TYPE_MINEABLE_DIRT: (True, True),
    TYPE_MINEABLE_ROCK: (True, True),
    TYPE_STREAM: (True, True),
    TYPE_LAKE: (True, True),
}

# Biome detection helper
BIOME_NAMES = {
    "meadow": "Meadow",
    "hillside": "Hillside",
    "river": "River Delta",
    "cave": "Cave",
    "town": "Town",
}

# Lapidary upgrade: level -> {cost, multiplier_min, multiplier_max}
LAPIDARY_UPGRADES = {
    1: {"cost": 0, "mult_min": 2.0, "mult_max": 2.0},
    2: {"cost": 150, "mult_min": 2.0, "mult_max": 2.5},
    3: {"cost": 300, "mult_min": 2.25, "mult_max": 2.75},
    4: {"cost": 500, "mult_min": 2.5, "mult_max": 3.0, "unlock_at": 2500},
    5: {"cost": 800, "mult_min": 2.75, "mult_max": 3.25, "unlock_at": 5000},
}
LAPIDARY_CUT_FEE_RATIO = 0.30  # 30% of raw value

# Difficulty tiers: lifetime_earnings threshold -> stat overrides
DIFFICULTY_TIERS = {
    0: {"max_enemies": 8, "spawn_interval": 5.0},
    2500: {"max_enemies": 12, "spawn_interval": 4.0, "bear_hp": 35},
    5000: {"max_enemies": 16, "spawn_interval": 3.0, "snake_attack": 3, "bear_attack": 7},
    7500: {"max_enemies": 20, "spawn_interval": 2.5, "enable_cave_bat": True},
}
