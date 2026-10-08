"""Game content catalogs, loaded from game/data/catalogs.toml (stdlib tomllib).

A single data file keeps a fixed, explicit order (world generation draws from it)
and needs no module discovery, which also works inside packaged mobile builds.
"""

import tomllib
from pathlib import Path

from game.objects.base import EnemyDef, GemDef, ToolDef

CATALOG_PATH = Path(__file__).resolve().parent.parent / "data" / "catalogs.toml"


def _tuples(value):
    """TOML arrays -> tuples (catalog entries are frozen and hashable)."""
    if isinstance(value, list):
        return tuple(_tuples(v) for v in value)
    return value


def _build(entries: list, cls) -> dict:
    catalog = {}
    for entry in entries:
        item = cls(**{key: _tuples(value) for key, value in entry.items()})
        if item.name in catalog:
            raise ValueError(f"duplicate {cls.__name__} name: {item.name!r}")
        catalog[item.name] = item
    return catalog


def build_gem_catalog(entries: list | None = None) -> dict[str, GemDef]:
    return _build(load_catalogs()["gems"] if entries is None else entries, GemDef)


def build_tool_catalog(entries: list | None = None) -> dict[str, ToolDef]:
    return _build(load_catalogs()["tools"] if entries is None else entries, ToolDef)


def build_enemy_catalog(entries: list | None = None) -> dict[str, EnemyDef]:
    return _build(load_catalogs()["enemies"] if entries is None else entries, EnemyDef)


def load_catalogs(path: Path = CATALOG_PATH) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


_DATA = load_catalogs()
GEM_CATALOG: dict[str, GemDef] = build_gem_catalog(_DATA["gems"])
TOOL_CATALOG: dict[str, ToolDef] = build_tool_catalog(_DATA["tools"])
ENEMY_CATALOG: dict[str, EnemyDef] = build_enemy_catalog(_DATA["enemies"])
TOOL_MAX_LEVEL: int = _DATA["tool_upgrades"]["max_level"]
TOOL_UPGRADE_COSTS: dict[int, int] = {
    int(level): cost for level, cost in _DATA["tool_upgrades"]["costs"].items()
}
TOOL_UPGRADE_UNLOCK_AT: dict[int, int] = {
    int(level): earned for level, earned in _DATA["tool_upgrades"].get("unlock_at", {}).items()
}
BAG_CAPACITIES: list[int] = _DATA["bag"]["capacities"]
BAG_COSTS: list[int] = _DATA["bag"]["costs"]
BAG_UNLOCK_AT: list[int] = _DATA["bag"]["unlock_at"]
LANTERN: dict = _DATA["lantern"]
ARMOR: dict = _DATA["armor"]
BOOTS: dict = _DATA["boots"]
SUPPLIES: dict = _DATA["supplies"]
PERKS: dict = _DATA["perks"]
REPUTATION: dict = _DATA["reputation"]
