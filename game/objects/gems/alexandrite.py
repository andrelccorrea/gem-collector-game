from game.objects.base import GemDef

alexandrite = GemDef(
    name="alexandrite",
    value=100,
    polished_min_mult=2.5,
    polished_max_mult=3.0,
    char="o",
    color=((140, 0, 180), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=6,
)
