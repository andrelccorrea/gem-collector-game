from game.objects.base import GemDef

garnet = GemDef(
    name="garnet",
    value=25,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((180, 20, 20), (0, 0, 0)),
    biomes=("hillside", "cave"),
    rarity_weight=25,
)
