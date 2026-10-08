from dataclasses import dataclass


@dataclass(frozen=True)
class GemDef:
    name: str
    value: int
    polished_min_mult: float
    polished_max_mult: float
    char: str
    color: tuple
    biomes: tuple
    rarity_weight: int
    min_tier: int = 1  # lowest tool tier that can find it by digging or panning


@dataclass(frozen=True)
class ToolDef:
    name: str
    cost: int
    compatible_biomes: tuple
    compatible_types: tuple
    melee_damage: int
    tier: int  # digging quality; higher tiers reach rarer gems
    desc: str


@dataclass(frozen=True)
class EnemyDef:
    name: str
    hp: int
    attack: int
    char: str
    color: tuple
    biomes: tuple
    loot: str
    loot_value: int
    aggro_range: int
    speed: float
    attack_cooldown: float
