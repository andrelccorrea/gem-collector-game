from game.objects.base import GemDef

emerald = GemDef(
    name="emerald",
    value=80,
    polished_min_mult=2.25,
    polished_max_mult=2.75,
    char="o",
    color=((0, 200, 80), (0, 0, 0)),
    biomes=("cave", "hillside"),
    rarity_weight=8,
)
