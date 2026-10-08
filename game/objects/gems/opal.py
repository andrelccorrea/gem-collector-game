from game.objects.base import GemDef

opal = GemDef(
    name="opal",
    value=120,
    polished_min_mult=2.5,
    polished_max_mult=3.5,
    char="o",
    color=((255, 140, 0), (0, 0, 0)),
    biomes=("cave", "river"),
    rarity_weight=3,
)
