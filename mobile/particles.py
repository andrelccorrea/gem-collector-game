"""Particle bursts for world events (sparkles on a find, dust on a miss, sparks on a hit),
as plain data so tests can check them without Kivy.

Each event kind has a preset (count, speed, lifetime, size, gravity, damping, direction).
Positions are kept as a world tile plus an offset in cell widths, so bursts stay put
while the world scrolls; the frontend turns them into small square "pixels".
"""

import math
from dataclasses import dataclass

# kind -> preset. speed in cell widths per second; gravity pulls down (negative floats up);
# damping is the share of speed kept per second; up = only upward directions.
PRESETS = {
    "find": dict(count=14, speed=(2.0, 5.0), life=(0.5, 0.9), size=0.3, gravity=6.0,
                 damping=0.3, up=False),
    "miss": dict(count=8, speed=(1.0, 2.5), life=(0.35, 0.6), size=0.3, gravity=5.0,
                 damping=0.2, up=True),
    "hit": dict(count=8, speed=(4.0, 8.0), life=(0.15, 0.3), size=0.2, gravity=0.0,
                damping=0.1, up=False),
    "hurt": dict(count=8, speed=(2.0, 5.0), life=(0.3, 0.5), size=0.25, gravity=8.0,
                 damping=0.3, up=False),
    "loot": dict(count=6, speed=(1.5, 3.5), life=(0.5, 0.8), size=0.25, gravity=4.0,
                 damping=0.3, up=True),
    "achievement": dict(count=24, speed=(3.0, 7.0), life=(0.7, 1.2), size=0.3, gravity=5.0,
                        damping=0.3, up=False),
    "splash": dict(count=7, speed=(1.0, 2.2), life=(0.3, 0.5), size=0.2, gravity=7.0,
                   damping=0.3, up=True),
    "heal": dict(count=6, speed=(0.5, 1.5), life=(0.6, 0.9), size=0.25, gravity=-2.5,
                 damping=0.5, up=True),
}  # fmt: skip
DUST_COLOR = (170, 140, 100)
SPARK_COLOR = (255, 240, 170)


@dataclass
class Particle:
    wx: int  # world tile it came from
    wy: int
    ox: float  # offset from the tile's center, in cell widths (y up)
    oy: float
    vx: float
    vy: float
    life: float
    color: tuple
    size: float
    gravity: float
    damping: float
    age: float = 0.0

    @property
    def alpha(self) -> float:
        """Fully visible for the first half of its life, then fading out."""
        left = 1.0 - self.age / self.life
        return max(0.0, min(1.0, left * 2))


def burst(kind: str, wx: int, wy: int, color, rng) -> list:
    """The particles for an event of ``kind`` at tile (wx, wy); none for unknown kinds."""
    preset = PRESETS.get(kind)
    if preset is None:
        return []
    if kind == "miss":
        color = DUST_COLOR
    elif kind == "hit":
        color = SPARK_COLOR
    particles = []
    for _ in range(preset["count"]):
        angle = rng.uniform(0.15, math.pi - 0.15) if preset["up"] else rng.uniform(0, 2 * math.pi)
        speed = rng.uniform(*preset["speed"])
        particles.append(
            Particle(
                wx,
                wy,
                0.0,
                0.0,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                rng.uniform(*preset["life"]),
                tuple(color),
                preset["size"],
                preset["gravity"],
                preset["damping"],
            )
        )
    return particles


def step(particles: list, dt: float) -> list:
    """Advance every particle by ``dt`` seconds; returns those still alive."""
    alive = []
    for p in particles:
        p.age += dt
        if p.age >= p.life:
            continue
        keep = p.damping**dt
        p.vx *= keep
        p.vy = p.vy * keep - p.gravity * dt
        p.ox += p.vx * dt
        p.oy += p.vy * dt
        alive.append(p)
    return alive
