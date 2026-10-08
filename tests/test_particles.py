import importlib.util
import pathlib
import random

from game import events

_SPEC = importlib.util.spec_from_file_location(
    "particles", pathlib.Path(__file__).parent.parent / "mobile" / "particles.py"
)
particles = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(particles)


def test_each_event_kind_with_a_burst_has_a_preset():
    kinds = {events.FIND, events.MISS, events.HIT, events.HURT, events.LOOT, events.HEAL}
    kinds.add(events.ACHIEVE)
    assert kinds == set(particles.PRESETS)
    assert particles.burst(events.FULL, 0, 0, (1, 2, 3), random.Random(1)) == []


def test_a_burst_spreads_out_fades_and_ends():
    burst = particles.burst("find", 4, 5, (10, 20, 30), random.Random(1))
    assert len(burst) == particles.PRESETS["find"]["count"]
    assert all(p.color == (10, 20, 30) and (p.wx, p.wy) == (4, 5) for p in burst)
    alive = particles.step(list(burst), 0.2)
    assert all(abs(p.ox) + abs(p.oy) > 0 for p in alive)
    assert all(0 < p.alpha <= 1 for p in alive)
    for _ in range(20):
        alive = particles.step(alive, 0.1)
    assert alive == []


def test_dust_rises_then_falls_and_heal_floats_up():
    dust = particles.burst("miss", 0, 0, (0, 0, 0), random.Random(2))
    assert all(p.vy > 0 for p in dust) and dust[0].color == particles.DUST_COLOR
    heal = particles.burst("heal", 0, 0, (0, 255, 0), random.Random(2))
    for _ in range(5):
        heal = particles.step(heal, 0.1)
    assert all(p.oy > 0 for p in heal)
