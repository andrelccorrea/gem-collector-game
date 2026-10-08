from game.objects.base import GemDef

chrysoberyl = GemDef(
    name="chrysoberyl",
    value=90,
    polished_min_mult=2.25,
    polished_max_mult=2.75,
    char="o",
    color=((200, 200, 0), (0, 0, 0)),
    biomes=("cave",),
    rarity_weight=5,
)
