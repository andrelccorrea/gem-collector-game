from game.objects.base import GemDef

sapphire = GemDef(
    name="sapphire",
    value=160,
    polished_min_mult=2.5,
    polished_max_mult=3.0,
    char="o",
    color=((0, 60, 220), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=3,
)
