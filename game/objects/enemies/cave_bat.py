from game.objects.base import EnemyDef

cave_bat = EnemyDef(
    name="cave_bat",
    hp=15,
    attack=4,
    char="v",
    color=((100, 0, 150), (10, 10, 10)),
    biomes=("cave",),
    loot="bat_wing",
    loot_value=15,
    aggro_range=6,
    speed=3.0,
    attack_cooldown=1.5,
)
