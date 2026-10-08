from game.objects.base import GemDef

citrine = GemDef(
    name="citrine",
    value=8,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((255, 185, 0), (0, 0, 0)),
    biomes=("meadow", "hillside", "river"),
    rarity_weight=45,
)
