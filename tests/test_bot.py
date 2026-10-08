from game.bot import simulate_run


def test_bot_runs_are_reproducible():
    assert simulate_run(3, max_minutes=2) == simulate_run(3, max_minutes=2)


def test_bot_makes_progress_through_the_real_rules():
    report = simulate_run(5, max_minutes=4)
    assert report.lifetime_earnings > 0
    assert set(report.earnings_by_biome) <= {"meadow", "hillside", "river", "cave"}
    assert report.minutes_played <= 4.0 + 1e-6
