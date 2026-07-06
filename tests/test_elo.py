"""Tests for the ELO logic in :mod:`elo`."""

import numpy as np
import pandas as pd
import pytest

import elo


# ---------------------------------------------------------------------------
# expected_result_prob
# ---------------------------------------------------------------------------
def test_equal_ratings_no_home_advantage_is_a_coin_flip():
    home, away = elo.expected_result_prob(1500, 1500, home_field_advantage=0)
    assert home == pytest.approx(0.5)
    assert away == pytest.approx(0.5)


def test_probabilities_sum_to_one():
    home, away = elo.expected_result_prob(1600, 1400)
    assert home + away == pytest.approx(1.0)


def test_stronger_team_has_higher_expected_score():
    strong, _ = elo.expected_result_prob(1800, 1400, home_field_advantage=0)
    weak, _ = elo.expected_result_prob(1400, 1800, home_field_advantage=0)
    assert strong > 0.5 > weak


def test_home_advantage_helps_the_home_team():
    without = elo.expected_result_prob(1500, 1500, home_field_advantage=0)[0]
    with_hfa = elo.expected_result_prob(1500, 1500, home_field_advantage=100)[0]
    assert with_hfa > without


# ---------------------------------------------------------------------------
# actual_result
# ---------------------------------------------------------------------------
def test_actual_result_mapping():
    assert elo.actual_result("H") == (1.0, 0.0)
    assert elo.actual_result("A") == (0.0, 1.0)
    assert elo.actual_result("D") == (0.5, 0.5)


def test_actual_result_rejects_bad_input():
    with pytest.raises(ValueError):
        elo.actual_result("X")


# ---------------------------------------------------------------------------
# calculate_elo
# ---------------------------------------------------------------------------
def test_home_win_raises_home_rating_and_lowers_away():
    home_before, away_before = 1500, 1500
    home_after, away_after, _ = elo.calculate_elo(
        home_before, away_before, "H", home_field_advantage=0
    )
    assert home_after > home_before
    assert away_after < away_before


def test_rating_changes_are_zero_sum():
    home_after, away_after, _ = elo.calculate_elo(1600, 1400, "A")
    delta = (home_after - 1600) + (away_after - 1400)
    assert delta == pytest.approx(0.0, abs=1e-6)


def test_bigger_k_means_bigger_swing():
    small = elo.calculate_elo(1500, 1500, "H", k_value=10, home_field_advantage=0)[0]
    big = elo.calculate_elo(1500, 1500, "H", k_value=40, home_field_advantage=0)[0]
    assert (big - 1500) > (small - 1500)


# ---------------------------------------------------------------------------
# league tables (synthetic fixture)
# ---------------------------------------------------------------------------
@pytest.fixture
def three_team_season():
    # A beats B, A draws C, B beats C.
    return pd.DataFrame(
        {
            "Date": pd.to_datetime(["2020-01-01", "2020-01-08", "2020-01-15"]),
            "HomeTeam": ["A", "A", "B"],
            "AwayTeam": ["B", "C", "C"],
            "FTHG": [2, 1, 3],
            "FTAG": [0, 1, 1],
            "FTR": ["H", "D", "H"],
        }
    )


def test_plain_table_points_and_ranking(three_team_season):
    table = elo.create_league_table(three_team_season)
    final, history = elo.update_league_table(table, three_team_season)

    points = final.set_index("team")["points"]
    assert points["A"] == 4  # win + draw
    assert points["B"] == 3  # loss + win
    assert points["C"] == 1  # draw + loss
    assert final.iloc[0]["team"] == "A"  # top of the table
    # history records both teams after each of the 3 matches
    assert len(history) == len(table) + 3 * 2


def test_elo_table_rewards_the_winning_team(three_team_season):
    table = elo.create_elo_league_table(three_team_season, default_elo=1500)
    final, _ = elo.update_elo_league_table(table, three_team_season)
    elos = final.set_index("team")["elo"]
    # A never lost, so it should end above its 1500 start and above C, who lost.
    assert elos["A"] > 1500
    assert elos["A"] > elos["C"]


# ---------------------------------------------------------------------------
# read_results (uses the real CSVs on disk)
# ---------------------------------------------------------------------------
def test_read_results_loads_expected_columns():
    df = elo.read_results()
    assert not df.empty
    for col in ("Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR"):
        assert col in df.columns
    assert np.issubdtype(df["Date"].dtype, np.datetime64)


def test_read_results_verbose_does_not_crash(capsys):
    # Regression: `verbose=True` used to crash because a `print` argument
    # shadowed the builtin print().
    df = elo.read_results(verbose=True)
    assert not df.empty
    assert capsys.readouterr().out  # something was printed
