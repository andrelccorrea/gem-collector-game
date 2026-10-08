import pytest

from clingine.renderer import StubRenderer
from game import profile
from game.gems import bag_capacity
from game.input import Action, InputState
from game.lantern import lantern_capacity
from game.menu import (
    MENU_ITEMS,
    _select_menu_item,
    render_perks,
    update_daily_end,
    update_death_screen,
    update_perks,
    update_win_screen,
)
from game.objects.registry import PERKS, REPUTATION
from game.persistence import load_game, save_game
from game.simulation import new_run
from game.state import GameState

CONFIRM = InputState(pressed=frozenset({Action.CONFIRM}))
DOWN = InputState(pressed=frozenset({Action.MOVE_DOWN}))


def _give_reputation(amount):
    p = profile.load_profile()
    p["reputation"] = amount
    profile.save_profile(p)


def _menu(item_id):
    return [i for i, _ in MENU_ITEMS].index(item_id)


@pytest.mark.parametrize("outcome", ["win", "hardcore_death", "daily"])
def test_finished_runs_earn_reputation(outcome):
    gained = profile.award_reputation(5_000, outcome, "run-1")
    assert gained == 5_000 // REPUTATION[f"{outcome}_divisor"]
    assert profile.load_profile()["reputation"] == gained
    assert profile.load_profile()["runs_finished"] == 1


def test_perks_cost_reputation_level_by_level():
    _give_reputation(100)
    for _ in PERKS["max_hp"]["costs"]:
        assert profile.buy_perk("max_hp")
    p = profile.load_profile()
    assert p["perks"]["max_hp"] == len(PERKS["max_hp"]["costs"])
    assert p["reputation"] == 100 - sum(PERKS["max_hp"]["costs"])
    assert not profile.buy_perk("max_hp")  # maxed


def test_cannot_buy_without_enough_reputation():
    _give_reputation(PERKS["start_gold"]["costs"][0] - 1)
    assert not profile.buy_perk("start_gold")
    assert profile.load_profile()["perks"]["start_gold"] == 0


def test_perks_shape_a_new_run():
    state = new_run(4)
    base_gold, base_hp = state.player_gold, state.player_max_hp
    base_bag, base_light = bag_capacity(state), lantern_capacity(state)
    owned = profile.new_profile()
    owned["perks"] = {key: 2 for key in PERKS}
    profile.apply_perks(state, owned)
    assert state.player_gold == base_gold + 2 * PERKS["start_gold"]["per_level"]
    assert state.player_max_hp == state.player_hp == base_hp + 2 * PERKS["max_hp"]["per_level"]
    assert bag_capacity(state) == base_bag + 2 * PERKS["bag_bonus"]["per_level"]
    assert lantern_capacity(state) == pytest.approx(base_light * (1 + 2 * 0.2))
    assert state.lantern_fuel == pytest.approx(lantern_capacity(state))


def test_new_games_use_perks_but_daily_runs_do_not(monkeypatch):
    import random

    monkeypatch.setattr(random, "randint", lambda a, b: 99)
    _give_reputation(100)
    profile.buy_perk("start_gold")
    state = GameState(menu_cursor=_menu("new"))
    _select_menu_item(state, save_exists=False)
    assert state.player_gold == 50 + PERKS["start_gold"]["per_level"]
    state = GameState(menu_cursor=_menu("daily"))
    _select_menu_item(state, save_exists=False)
    assert state.player_gold == 50


def test_run_endings_award_reputation_once_each():
    win = GameState(lifetime_earnings=10_000, active_scene="win")
    update_win_screen(CONFIRM, win)
    expected = 10_000 // REPUTATION["win_divisor"]
    assert profile.load_profile()["reputation"] == expected

    dead = GameState(lifetime_earnings=3_000, hardcore=True, active_scene="death")
    update_death_screen(CONFIRM, dead)
    expected += 3_000 // REPUTATION["hardcore_death_divisor"]
    assert profile.load_profile()["reputation"] == expected

    daily = GameState(lifetime_earnings=4_000, daily="2026-10-08", active_scene="daily_end")
    update_daily_end(CONFIRM, daily)
    expected += 4_000 // REPUTATION["daily_divisor"]
    assert profile.load_profile()["reputation"] == expected


def test_normal_death_earns_nothing():
    state = new_run(2)
    state.lifetime_earnings, state.active_scene = 8_000, "death"
    update_death_screen(CONFIRM, state)
    assert profile.load_profile()["reputation"] == 0


def test_perks_screen_lists_perks_and_buys_the_selected_one():
    _give_reputation(50)
    state = GameState(active_scene="perks")
    update_perks(DOWN, state)
    update_perks(CONFIRM, state)
    second = list(PERKS)[1]
    assert profile.load_profile()["perks"][second] == 1
    renderer = StubRenderer(80, 24)
    render_perks(renderer, state)
    screen = "\n".join("".join(renderer.get_cell(x, y)[0] for x in range(80)) for y in range(24))
    assert "Reputation:" in screen and PERKS[second]["name"] in screen


def test_run_perk_bonuses_are_saved():
    state = new_run(3)
    state.bag_bonus, state.lantern_bonus = 10, 0.4
    save_game(state)
    loaded = load_game()
    assert (loaded.bag_bonus, loaded.lantern_bonus) == (10, 0.4)


def test_damaged_profile_is_kept_aside_and_a_fresh_one_starts(isolated_data_dir):
    (isolated_data_dir / "profile.json").write_text("{nope")
    assert profile.load_profile() == profile.new_profile()
    assert (isolated_data_dir / "profile.json.bak").read_text() == "{nope"


def test_profile_is_written_atomically(isolated_data_dir):
    _give_reputation(7)
    assert not (isolated_data_dir / "profile.json.tmp").exists()
    assert profile.load_profile()["reputation"] == 7


def test_a_run_pays_reputation_only_once():
    assert profile.award_reputation(10_000, "win", "run-A") > 0
    assert profile.award_reputation(10_000, "win", "run-A") == 0
    assert profile.award_reputation(10_000, "win", "run-B") > 0


def test_reloading_a_save_from_before_the_win_does_not_pay_again():
    state = new_run(8)
    state.lifetime_earnings = 9_990
    save_game(state)  # saved just before winning
    state.lifetime_earnings, state.active_scene = 10_000, "win"
    update_win_screen(CONFIRM, state)
    first = profile.load_profile()["reputation"]
    assert first > 0

    reloaded = load_game()
    assert reloaded.run_id == state.run_id
    reloaded.lifetime_earnings, reloaded.active_scene = 10_000, "win"
    update_win_screen(CONFIRM, reloaded)
    assert profile.load_profile()["reputation"] == first


def test_perks_notice_does_not_follow_to_the_main_menu():
    state = GameState(active_scene="perks")
    update_perks(CONFIRM, state)  # not enough reputation -> notice
    assert state.menu_notice
    update_perks(InputState(pressed=frozenset({Action.CANCEL})), state)
    assert state.active_scene == "menu" and state.menu_notice == ""


def test_screens_promise_nothing_for_an_already_rewarded_run(stub_renderer):
    from game.menu import render_win_screen

    profile.award_reputation(10_000, "win", "run-X")
    assert profile.reputation_preview(10_000, "hardcore_death", "run-X") == 0
    state = GameState(lifetime_earnings=10_000, run_id="run-X", active_scene="win")
    render_win_screen(stub_renderer, state)
    screen = "\n".join(
        "".join(stub_renderer.get_cell(x, y)[0] for x in range(80)) for y in range(24)
    )
    assert "+0 reputation" in screen
