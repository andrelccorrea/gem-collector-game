from game.objects.base import GemDef

imperial_topaz = GemDef(
    name="imperial_topaz",
    value=200,
    polished_min_mult=2.75,
    polished_max_mult=3.25,
    char="o",
    color=((255, 120, 40), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=2,
)
