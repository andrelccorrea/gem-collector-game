from game.objects.base import GemDef

ruby = GemDef(
    name="ruby",
    value=150,
    polished_min_mult=2.5,
    polished_max_mult=3.0,
    char="o",
    color=((220, 0, 50), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=4,
)
