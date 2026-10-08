"""Save slot and leaderboard storage.

Save format (``schema_version`` 12, compact JSON):
    schema_version, worldgen_version, seed, player{...}, inventory{...},
    polished_gem_values {"<gem>_polished": [price per gem, highest first]},
    lapidary_level, bag_level, armor_level, boots_level, market {kind: saturation},
    lantern {level, fuel}, hardcore, dropped_bag {x, y, gems, loot, polished} or null,
    recall_charms, supplies {key: count}, museum,
    perk_bonuses {bag, lantern}, run_id,
    depleted_tiles [[x, y]...],
    world_gems [[x, y, name]...], fog (run-length string, row-major),
    rng_state (gameplay RNG state, so a continued run keeps its roll sequence)

Older saves are upgraded through ``MIGRATIONS``. Tile coordinates are only valid for
the world generator version that wrote them, so on a ``worldgen_version`` mismatch the
player's progress is kept and the map is reset.
"""

import json
import os
import shutil
import sys
from datetime import date

from game.constants import MAP_HEIGHT, MAP_WIDTH

SCHEMA_VERSION = 12
SAVE_NAME = "save.json"
LEADERBOARD_NAME = "leaderboard.json"
DAILY_NAME = "daily.json"
APP_DIR_NAME = "GemCollector"
# Frontends without a desktop home directory (e.g. Android) point this at app storage.
DATA_DIR_ENV = "GEM_COLLECTOR_DATA_DIR"

_FOG_CODES = {"unseen": "u", "explored": "e", "visible": "v"}
_FOG_NAMES = {code: name for name, code in _FOG_CODES.items()}


class SaveLoadError(Exception):
    """The save slot exists but cannot be loaded; the message is shown to the player."""


# ---------------------------------------------------------------------------
# Locations
# ---------------------------------------------------------------------------


def data_dir() -> str:
    """Per-user directory for saves and the leaderboard (created by writers, not here)."""
    path = os.environ.get(DATA_DIR_ENV)
    if not path:
        home = os.path.expanduser("~")
        if sys.platform == "darwin":
            path = os.path.join(home, "Library", "Application Support", APP_DIR_NAME)
        elif sys.platform == "win32":
            path = os.path.join(os.environ.get("APPDATA", home), APP_DIR_NAME)
        else:
            base = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
            path = os.path.join(base, APP_DIR_NAME.lower())
    return path


def save_path() -> str:
    return os.path.join(data_dir(), SAVE_NAME)


def leaderboard_path() -> str:
    return os.path.join(data_dir(), LEADERBOARD_NAME)


def import_legacy_files(*legacy_dirs: str) -> None:
    """Copy saves that older versions wrote to the launch directory into data_dir().

    Runs once: a marker file stops a stale legacy save from coming back later (e.g.
    after the current save was moved aside as damaged). Failures are ignored; the game
    simply starts without the old files.
    """
    marker = os.path.join(data_dir(), ".legacy_imported")
    if os.path.exists(marker):
        return
    try:
        os.makedirs(data_dir(), exist_ok=True)
        for name in (SAVE_NAME, LEADERBOARD_NAME):
            new = os.path.join(data_dir(), name)
            for legacy_dir in legacy_dirs:
                old = os.path.join(legacy_dir, name)
                if os.path.isfile(old) and not os.path.exists(new):
                    shutil.copy2(old, new)
        open(marker, "w").close()
    except OSError:
        pass


def has_save() -> bool:
    return os.path.isfile(save_path())


# Scenes in which a run is being played (the only ones an automatic save may capture).
PLAY_SCENES = frozenset({"game", "shop", "lapidary", "save_point"})


def autosave_allowed(state) -> bool:
    """Whether a run may be saved automatically (e.g. when a mobile app is paused).

    Only while it is being played: not daily runs (never saved), not end screens (a win
    pays its rewards when confirmed; a finished hardcore run must stay deleted) and not
    menus (the run still in memory may already be over).
    """
    return state.active_scene in PLAY_SCENES and not state.daily and state.world_tiles is not None


def delete_save() -> None:
    try:
        os.remove(save_path())
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Fog encoding
# ---------------------------------------------------------------------------


def _encode_fog(meta) -> str:
    """Run-length encode tile visibility in row-major order, e.g. "120u8e3v..."."""
    runs = []
    prev, count = None, 0
    for y in range(MAP_HEIGHT):
        for x in range(MAP_WIDTH):
            code = _FOG_CODES.get(meta.get((x, y), {}).get("visibility", "unseen"), "u")
            if code == prev:
                count += 1
            else:
                if prev is not None:
                    runs.append(f"{count}{prev}")
                prev, count = code, 1
    runs.append(f"{count}{prev}")
    return "".join(runs)


def _decode_fog(encoded: str) -> list:
    """Inverse of _encode_fog: a row-major list of visibility names."""
    cells, digits = [], ""
    for ch in encoded:
        if ch.isdigit():
            digits += ch
        else:
            cells.extend([_FOG_NAMES[ch]] * int(digits))
            digits = ""
    if len(cells) != MAP_WIDTH * MAP_HEIGHT:
        raise ValueError(f"fog covers {len(cells)} tiles, expected {MAP_WIDTH * MAP_HEIGHT}")
    return cells


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------


def _migrate_v0_to_v1(data: dict) -> dict:
    """Unversioned saves: fog was a list of [x, y, visibility] entries."""
    grid = {}
    for x, y, vis in data.get("fog", []):
        grid[(x, y)] = {"visibility": vis}
    data["fog"] = _encode_fog(grid)
    # v0 predates generator versioning; it was written by the first generator.
    data["worldgen_version"] = 1
    return data


def _migrate_v1_to_v2(data: dict) -> dict:
    """v1 kept one price per polished gem kind; v2 keeps one price per gem."""
    gems = data.get("inventory", {}).get("gems", {})
    data["polished_gem_values"] = {
        key: [price] * gems.get(key, 0)
        for key, price in data.get("polished_gem_values", {}).items()
        if gems.get(key, 0) > 0
    }
    return data


def _migrate_v2_to_v3(data: dict) -> dict:
    """v3 adds bag upgrades; older saves start with the basic bag."""
    data["bag_level"] = 0
    return data


def _migrate_v3_to_v4(data: dict) -> dict:
    """v4 adds shop saturation; older saves start with a fresh market."""
    data["market"] = {}
    return data


def _migrate_v4_to_v5(data: dict) -> dict:
    """v5 adds the lantern; older saves get the basic lantern, full."""
    from game.objects.registry import LANTERN

    data["lantern"] = {"level": 0, "fuel": float(LANTERN["capacities"][0])}
    return data


def _migrate_v5_to_v6(data: dict) -> dict:
    """v6 adds hardcore runs and the bag dropped on death."""
    data["hardcore"] = False
    data["dropped_bag"] = None
    return data


def _migrate_v6_to_v7(data: dict) -> dict:
    """v7 adds recall charms."""
    data["recall_charms"] = 0
    return data


def _migrate_v7_to_v8(data: dict) -> dict:
    """v8 adds the museum."""
    data["museum"] = []
    return data


def _migrate_v8_to_v9(data: dict) -> dict:
    """v9 adds the run's perk bonuses (runs started before perks have none)."""
    data["perk_bonuses"] = {"bag": 0, "lantern": 0.0}
    return data


def _migrate_v9_to_v10(data: dict) -> dict:
    """v10 adds the run id that keeps one-time rewards from being paid twice.

    Derived from the save's content, so reloading the same old save (without saving
    again) always yields the same id instead of a fresh one each time.
    """
    import hashlib

    digest = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    data["run_id"] = digest[:32]
    return data


def _migrate_v10_to_v11(data: dict) -> dict:
    """v11 adds armor and boots; older saves get the basic ones."""
    data["armor_level"] = 0
    data["boots_level"] = 0
    return data


def _migrate_v11_to_v12(data: dict) -> dict:
    """v12 adds supplies (consumables); older saves carry none."""
    data["supplies"] = {}
    return data


# MIGRATIONS[n] upgrades a version-n save to version n + 1.
MIGRATIONS = {
    0: _migrate_v0_to_v1,
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
    4: _migrate_v4_to_v5,
    5: _migrate_v5_to_v6,
    6: _migrate_v6_to_v7,
    7: _migrate_v7_to_v8,
    8: _migrate_v8_to_v9,
    9: _migrate_v9_to_v10,
    10: _migrate_v10_to_v11,
    11: _migrate_v11_to_v12,
}


def migrate(data: dict) -> dict:
    version = data.get("schema_version", 0)
    if version > SCHEMA_VERSION:
        raise SaveLoadError("This save was made by a newer version of the game.")
    while version < SCHEMA_VERSION:
        data = MIGRATIONS[version](data)
        version += 1
        data["schema_version"] = version
    return data


# ---------------------------------------------------------------------------
# Save / load
# ---------------------------------------------------------------------------


def save_game(state) -> str | None:
    """Atomically write the save slot. Returns None on success, else an error message."""
    from game.world import WORLDGEN_VERSION

    version, internal, gauss_next = state.rng.getstate()
    save_dict = {
        "schema_version": SCHEMA_VERSION,
        "worldgen_version": WORLDGEN_VERSION,
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
        "bag_level": state.bag_level,
        "armor_level": state.armor_level,
        "boots_level": state.boots_level,
        "market": state.market,
        "lantern": {"level": state.lantern_level, "fuel": state.lantern_fuel},
        "run_id": state.run_id,
        "hardcore": state.hardcore,
        "dropped_bag": state.dropped_bag,
        "recall_charms": state.recall_charms,
        "supplies": state.supplies,
        "museum": state.museum,
        "perk_bonuses": {"bag": state.bag_bonus, "lantern": state.lantern_bonus},
        "depleted_tiles": [[x, y] for x, y in sorted(state.depleted_tiles)],
        "world_gems": [[x, y, name] for (x, y), name in sorted(state.world_gems.items())],
        "fog": _encode_fog(state.world_tiles.meta),
        "rng_state": [version, list(internal), gauss_next],
    }

    tmp_file = None
    try:
        path = save_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_file = path + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(save_dict, f, separators=(",", ":"))
        os.replace(tmp_file, path)
        return None
    except OSError as e:
        if tmp_file is not None and os.path.exists(tmp_file):
            try:
                os.remove(tmp_file)
            except OSError:
                pass
        return f"Save failed: {e.strerror or e}"


def load_game():
    """Load the save slot.

    Returns a GameState, or None when there is no save. Raises SaveLoadError when the
    save cannot be used; an unreadable file is first moved aside to ``save.json.bak``.
    """
    path = save_path()
    if not os.path.isfile(path):
        return None

    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("save root is not an object")
        return _state_from_save(migrate(data))
    except SaveLoadError:
        raise
    except Exception as e:
        # The file is untrusted input: any parse or shape error means it is damaged.
        backup = path + ".bak"
        try:
            os.replace(path, backup)
        except OSError:
            backup = None
        detail = f" It was moved to {backup}." if backup else ""
        raise SaveLoadError(f"The save file is damaged and could not be loaded.{detail}") from e


def _state_from_save(data: dict):
    from game import camera
    from game import world as world_module
    from game.player import set_hud_message
    from game.state import GameState, gameplay_rng

    state = GameState()

    state.seed = data["seed"]
    state.rng = gameplay_rng(state.seed)
    if "rng_state" in data:
        version, internal, gauss_next = data["rng_state"]
        state.rng.setstate((version, tuple(internal), gauss_next))
    state.world_tiles, state.world_gems = world_module.generate_world(state.seed)

    player = data["player"]
    state.player_x = player["x"]
    state.player_y = player["y"]
    state.player_hp = player["hp"]
    state.player_max_hp = player["max_hp"]
    state.player_gold = player["gold"]
    state.lifetime_earnings = player["lifetime_earnings"]
    state.equipped_tool = player["equipped_tool"]
    state.has_won = player["has_won"]

    # Tools are stored as name -> level; expand to name -> {"level": N}
    raw_inv = data["inventory"]
    state.inventory = {
        "gems": raw_inv.get("gems", {}),
        "tools": {k: {"level": v} for k, v in raw_inv.get("tools", {}).items()},
        "loot": raw_inv.get("loot", {}),
    }
    state.polished_gem_values = data.get("polished_gem_values", {})
    state.lapidary_level = data.get("lapidary_level", 1)
    state.bag_level = data["bag_level"]
    state.armor_level = data["armor_level"]
    state.boots_level = data["boots_level"]
    state.market = data["market"]
    state.lantern_level = data["lantern"]["level"]
    state.lantern_fuel = data["lantern"]["fuel"]
    state.run_id = data["run_id"]
    state.hardcore = data["hardcore"]
    state.dropped_bag = data["dropped_bag"]
    state.recall_charms = data["recall_charms"]
    state.supplies = {str(k): int(v) for k, v in data["supplies"].items()}
    state.museum = data["museum"]
    state.bag_bonus = data["perk_bonuses"]["bag"]
    state.lantern_bonus = data["perk_bonuses"]["lantern"]

    if data["worldgen_version"] == world_module.WORLDGEN_VERSION:
        _restore_map(state, data)
    else:
        # Saved coordinates belong to a different world layout: keep progress, reset map.
        if state.world_tiles.start_pos is not None:
            state.player_x, state.player_y = state.world_tiles.start_pos
        state.dropped_bag = None
        set_hud_message(
            state,
            "A game update reshaped the world: your gold, gems and tools were kept.",
            6.0,
        )

    camera.update_camera(state)
    return state


def _restore_map(state, data: dict) -> None:
    """Re-apply depleted tiles, picked-up gems and fog to the regenerated world."""
    state.depleted_tiles = set()
    for x, y in data.get("depleted_tiles", []):
        state.depleted_tiles.add((x, y))
        _deplete_tile_on_surface(state, x, y)

    # Saved entries override the regenerated set: the player may have picked some up.
    if "world_gems" in data:
        state.world_gems = {(x, y): name for x, y, name in data["world_gems"]}

    if data.get("fog"):
        meta = state.world_tiles.meta
        for i, vis in enumerate(_decode_fog(data["fog"])):
            coord = (i % MAP_WIDTH, i // MAP_WIDTH)
            if coord in meta:
                meta[coord]["visibility"] = vis

    state.visible_tiles = {
        coord
        for coord, tile in state.world_tiles.meta.items()
        if tile.get("visibility") == "visible"
    }


def _deplete_tile_on_surface(state, x: int, y: int) -> None:
    """Mark a tile as depleted on the world surface without modifying depleted_tiles set."""
    if state.world_tiles is None:
        return

    meta = state.world_tiles.meta.get((x, y), {})
    meta["depleted"] = True
    meta["interactable"] = False
    state.world_tiles.meta[(x, y)] = meta


# ---------------------------------------------------------------------------
# Leaderboard
# ---------------------------------------------------------------------------


def load_leaderboard() -> list:
    path = leaderboard_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return sorted(data.get("runs", []), key=lambda e: e.get("earnings", 0), reverse=True)
    except (OSError, ValueError, AttributeError, TypeError):
        return []


def save_leaderboard_entry(earnings: int) -> None:
    entries = load_leaderboard()
    entries.append({"earnings": earnings, "date": str(date.today())})
    entries = sorted(entries, key=lambda e: e.get("earnings", 0), reverse=True)[:10]
    try:
        os.makedirs(data_dir(), exist_ok=True)
        with open(leaderboard_path(), "w") as f:
            json.dump({"runs": entries}, f, indent=2)
    except OSError:
        pass


def _daily_path() -> str:
    return os.path.join(data_dir(), DAILY_NAME)


def _load_daily_file() -> dict:
    try:
        with open(_daily_path()) as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def load_daily(day: str) -> list:
    """Best earnings of the daily runs played on ``day`` (ISO date), highest first."""
    scores = _load_daily_file().get(day, [])
    return sorted((s for s in scores if isinstance(s, int)), reverse=True)


def save_daily_entry(day: str, earnings: int) -> None:
    data = _load_daily_file()
    data[day] = sorted(load_daily(day) + [earnings], reverse=True)[:10]
    try:
        os.makedirs(data_dir(), exist_ok=True)
        with open(_daily_path(), "w") as f:
            json.dump(data, f, indent=2)
    except OSError:
        pass
