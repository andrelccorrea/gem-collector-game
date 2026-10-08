from game.objects.base import GemDef

diamond = GemDef(
    name="diamond",
    value=400,
    polished_min_mult=3.0,
    polished_max_mult=4.0,
    char="o",
    color=((100, 200, 255), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=1,
)
