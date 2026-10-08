from game.objects.base import ToolDef

gold_pan = ToolDef(
    name="gold_pan",
    cost=60,
    compatible_biomes=("river",),
    compatible_types=("stream", "lake", "shallow"),
    melee_damage=2,
    base_yield=1,
    desc="Scoops gems from streams and lakes",
)
