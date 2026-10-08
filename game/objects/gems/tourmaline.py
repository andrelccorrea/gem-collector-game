from game.objects.base import GemDef

tourmaline = GemDef(
    name="tourmaline",
    value=12,
    polished_min_mult=2.0,
    polished_max_mult=3.0,
    char="o",
    color=((0, 180, 90), (0, 0, 0)),
    biomes=("hillside", "cave"),
    rarity_weight=40,
)
