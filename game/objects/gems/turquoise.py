from game.objects.base import GemDef

turquoise = GemDef(
    name="turquoise",
    value=30,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((64, 224, 208), (0, 0, 0)),
    biomes=("hillside", "river"),
    rarity_weight=15,
)
