from game.objects.base import EnemyDef

snake = EnemyDef(
    name="snake",
    hp=8,
    attack=2,
    char="s",
    color=((100, 200, 50), (0, 30, 0)),
    biomes=("meadow", "river"),
    loot="snake_skin",
    loot_value=8,
    aggro_range=5,
    speed=2.0,
    attack_cooldown=2.0,
)
