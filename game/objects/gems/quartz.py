from game.objects.base import GemDef

quartz = GemDef(
    name="quartz",
    value=5,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((220, 220, 220), (0, 0, 0)),
    biomes=("meadow", "hillside", "river"),
    rarity_weight=50,
)
