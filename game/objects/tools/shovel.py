from game.objects.base import ToolDef

shovel = ToolDef(
    name="shovel",
    cost=0,
    compatible_biomes=("meadow", "hillside", "river"),
    compatible_types=("mineable_grass", "mineable_dirt"),
    melee_damage=3,
    base_yield=1,
    desc="Digs promising patches of grass and dirt",
)
