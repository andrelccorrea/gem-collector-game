import json
import os
from datetime import date

from game.constants import CHAR_DEPLETED

SAVE_FILE = "save.json"
LEADERBOARD_FILE = "leaderboard.json"


def save_exists() -> bool:
    return os.path.exists(SAVE_FILE)


def save_game(state) -> None:
    """Atomically write game state to save.json."""
    save_dict = {
        "seed": state.seed,
        "player": {
            "x": state.player_x,
            "y": state.player_y,
            "hp": state.player_hp,
            "max_hp": state.player_max_hp,
            "gold": state.player_gold,
            "lifetime_earnings": state.lifetime_earnings,
            "equipped_tool": state.equipped_tool,
            "has_won": state.has_won,
        },
        "inventory": {
            "gems": state.inventory.get("gems", {}),
            "tools": {k: v["level"] for k, v in state.inventory.get("tools", {}).items()},
            "loot": state.inventory.get("loot", {}),
        },
        "polished_gem_values": state.polished_gem_values,
        "lapidary_level": state.lapidary_level,
        "depleted_tiles": [[x, y] for x, y in state.depleted_tiles],
        "world_gems": [[x, y, name] for (x, y), name in state.world_gems.items()],
        "fog": [
            [x, y, vis]
            for (x, y), tile in state.world_tiles.meta.items()
            if (vis := tile.get("visibility", "unseen")) != "unseen"
        ],
    }

    tmp_file = SAVE_FILE + ".tmp"
    try:
        with open(tmp_file, "w") as f:
            json.dump(save_dict, f, indent=2)
        os.replace(tmp_file, SAVE_FILE)
    except Exception:
        # If write fails, try to clean up temp file
        if os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except Exception:
                pass


def load_game():
    """Load game state from save.json. Returns a populated GameState or None."""
    if not os.path.exists(SAVE_FILE):
        return None

    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
    except Exception:
        return None

    try:
        from game import world as world_module
        from game.state import GameState

        state = GameState()

        # Seed and world
        state.seed = data["seed"]
        state.world_tiles, state.world_gems = world_module.generate_world(state.seed)

        # Player
        player = data["player"]
        state.player_x = player["x"]
        state.player_y = player["y"]
        state.player_hp = player["hp"]
        state.player_max_hp = player["max_hp"]
        state.player_gold = player["gold"]
        state.lifetime_earnings = player["lifetime_earnings"]
        state.equipped_tool = player["equipped_tool"]
        state.has_won = player["has_won"]

        # Inventory — tools stored as name->level in JSON; expand to name->{"level": N}
        raw_inv = data["inventory"]
        state.inventory = {
            "gems": raw_inv.get("gems", {}),
            "tools": {k: {"level": v} for k, v in raw_inv.get("tools", {}).items()},
            "loot": raw_inv.get("loot", {}),
        }

        # Polished gem values
        state.polished_gem_values = data.get("polished_gem_values", {})

        # Lapidary
        state.lapidary_level = data.get("lapidary_level", 1)

        # Depleted tiles — re-apply to the freshly generated world surface
        depleted_tiles = data.get("depleted_tiles", [])
        state.depleted_tiles = set()
        for pair in depleted_tiles:
            x, y = pair[0], pair[1]
            state.depleted_tiles.add((x, y))
            _deplete_tile_on_surface(state, x, y)

        # World gems — saved entries override the regenerated set, since the
        # player may have picked some up before saving.
        if "world_gems" in data:
            state.world_gems = {(entry[0], entry[1]): entry[2] for entry in data["world_gems"]}
        # else: keep the freshly regenerated dict (older saves predate this field)

        # Fog of war — restore visibility state
        for entry in data.get("fog", []):
            x, y, vis = entry
            if (x, y) in state.world_tiles.meta:
                state.world_tiles.meta[(x, y)]["visibility"] = vis

        state.visible_tiles = {
            (x, y)
            for (x, y), tile in state.world_tiles.meta.items()
            if tile.get("visibility") == "visible"
        }

        return state

    except Exception:
        return None


def _deplete_tile_on_surface(state, x: int, y: int) -> None:
    """Mark a tile as depleted on the world surface without modifying depleted_tiles set."""
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((x, y), {})
    meta["depleted"] = True
    meta["interactable"] = False
    state.world_tiles.meta[(x, y)] = meta

    # Change visual to depleted appearance
    depleted_color = ((80, 80, 80), (20, 20, 20))
    state.world_tiles.set_tile(x, y, CHAR_DEPLETED, depleted_color)


def load_leaderboard() -> list:
    if not os.path.exists(LEADERBOARD_FILE):
        return []
    try:
        with open(LEADERBOARD_FILE, "r") as f:
            data = json.load(f)
        return sorted(data.get("runs", []), key=lambda e: e.get("earnings", 0), reverse=True)
    except Exception:
        return []


def save_leaderboard_entry(earnings: int) -> None:
    entries = load_leaderboard()
    entries.append({"earnings": earnings, "date": str(date.today())})
    entries = sorted(entries, key=lambda e: e.get("earnings", 0), reverse=True)[:10]
    try:
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump({"runs": entries}, f, indent=2)
    except Exception:
        pass
