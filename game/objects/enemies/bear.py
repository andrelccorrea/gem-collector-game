from game.objects.base import EnemyDef

bear = EnemyDef(
    name="bear",
    hp=25,
    attack=5,
    char="B",
    color=((160, 100, 40), (40, 30, 0)),
    biomes=("meadow", "hillside"),
    loot="bear_pelt",
    loot_value=35,
    aggro_range=4,
    speed=1.5,
    attack_cooldown=3.0,
)
