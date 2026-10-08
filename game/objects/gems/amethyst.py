from game.objects.base import GemDef

amethyst = GemDef(
    name="amethyst",
    value=20,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((180, 0, 255), (0, 0, 0)),
    biomes=("hillside", "cave"),
    rarity_weight=30,
)
