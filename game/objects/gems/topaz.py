from game.objects.base import GemDef

topaz = GemDef(
    name="topaz",
    value=35,
    polished_min_mult=2.0,
    polished_max_mult=2.5,
    char="o",
    color=((200, 165, 50), (0, 0, 0)),
    biomes=("hillside", "cave"),
    rarity_weight=20,
)
