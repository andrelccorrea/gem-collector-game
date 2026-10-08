from game.objects.base import ToolDef

pickaxe = ToolDef(
    name="pickaxe",
    cost=80,
    compatible_biomes=("hillside", "cave"),
    compatible_types=("mineable_rock", "mineable_dirt"),
    melee_damage=5,
    base_yield=1,
    desc="Breaks rocky seams to expose valuable gems",
)
