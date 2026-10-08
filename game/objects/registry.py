import importlib
import pkgutil

import game.objects.enemies as enemies_pkg
import game.objects.gems as gems_pkg
import game.objects.tools as tools_pkg
from game.objects.base import EnemyDef, GemDef, ToolDef


def build_gem_catalog() -> dict[str, GemDef]:
    catalog: dict[str, GemDef] = {}
    for _finder, module_name, _ispkg in pkgutil.iter_modules(
        gems_pkg.__path__, gems_pkg.__name__ + "."
    ):
        if module_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        module = importlib.import_module(module_name)
        for obj in vars(module).values():
            if isinstance(obj, GemDef):
                catalog[obj.name] = obj
    return catalog


def build_tool_catalog() -> dict[str, ToolDef]:
    catalog: dict[str, ToolDef] = {}
    for _finder, module_name, _ispkg in pkgutil.iter_modules(
        tools_pkg.__path__, tools_pkg.__name__ + "."
    ):
        if module_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        module = importlib.import_module(module_name)
        for obj in vars(module).values():
            if isinstance(obj, ToolDef):
                catalog[obj.name] = obj
    return catalog


def build_enemy_catalog() -> dict[str, EnemyDef]:
    catalog: dict[str, EnemyDef] = {}
    for _finder, module_name, _ispkg in pkgutil.iter_modules(
        enemies_pkg.__path__, enemies_pkg.__name__ + "."
    ):
        if module_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        module = importlib.import_module(module_name)
        for obj in vars(module).values():
            if isinstance(obj, EnemyDef):
                catalog[obj.name] = obj
    return catalog


GEM_CATALOG: dict[str, GemDef] = build_gem_catalog()
TOOL_CATALOG: dict[str, ToolDef] = build_tool_catalog()
ENEMY_CATALOG: dict[str, EnemyDef] = build_enemy_catalog()
