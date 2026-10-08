from game.objects.base import GemDef

aquamarine = GemDef(
    name="aquamarine",
    value=55,
    polished_min_mult=2.25,
    polished_max_mult=2.75,
    char="o",
    color=((60, 200, 220), (0, 0, 0)),
    biomes=("cave", "river"),
    rarity_weight=10,
)
