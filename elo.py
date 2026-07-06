"""ELO rating system for English Premier League results.

This module contains the reusable, tested implementation behind the
``elo_pl.ipynb`` notebook. The notebook imports these functions so there is a
single source of truth for the logic.

Data comes from https://www.football-data.co.uk/englandm.php and is stored as
CSV files under ``data/pl/``. Only a handful of columns are needed:

    Date, HomeTeam, AwayTeam, FTHG, FTAG, FTR

where ``FTHG``/``FTAG`` are full-time home/away goals and ``FTR`` is the
full-time result: ``'H'`` (home win), ``'A'`` (away win) or ``'D'`` (draw).
"""

from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd

DEFAULT_COLUMNS = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG", "FTR", "filename"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
def read_results(
    path: str = "data/pl",
    columns_to_keep: list[str] | None = None,
    verbose: bool = False,
) -> pd.DataFrame:
    """Read and concatenate every ``.csv`` file in ``path`` into one DataFrame.

    Parameters
    ----------
    path:
        Folder containing the season CSV files.
    columns_to_keep:
        Columns to retain. Defaults to :data:`DEFAULT_COLUMNS`. Pass an empty
        list to keep every column.
    verbose:
        Print each file that gets loaded (handy for debugging).
    """
    if columns_to_keep is None:
        columns_to_keep = DEFAULT_COLUMNS

    all_files = glob.glob(os.path.join(path, "*.csv"))
    if verbose:
        print(all_files)

    frames = []
    for filename in all_files:
        if verbose:
            print(filename)
        df = pd.read_csv(filename)
        df["filename"] = filename.replace('\\', '/')  # keep the source file as a column,
                                                      # and normalize windows paths
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    if columns_to_keep:
        combined = combined[columns_to_keep]

    if "Date" in combined.columns:
        combined["Date"] = pd.to_datetime(combined["Date"], format="%d/%m/%Y")

    return combined


# ---------------------------------------------------------------------------
# Plain league table (points, wins/draws/losses, goals)
# ---------------------------------------------------------------------------
def create_league_table(data: pd.DataFrame) -> pd.DataFrame:
    """Create an empty league table seeded with the teams found in ``data``."""
    league_table = pd.DataFrame()
    league_table["team"] = _unique_teams(data)
    league_table["ranking"] = 0
    league_table["points"] = 0
    league_table["w"] = 0
    league_table["d"] = 0
    league_table["l"] = 0
    league_table["goals_for"] = 0
    league_table["goals_against"] = 0
    league_table["goal_difference"] = 0
    league_table["matched_played"] = 0
    league_table["last_date"] = min(data["Date"]) if "Date" in data.columns else 0
    return league_table


def update_league_table(
    league_table: pd.DataFrame, results_table: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Play through ``results_table`` and update the standings.

    Returns a tuple of ``(final_table, history)`` where ``history`` records the
    state of the two teams involved after every single match, so metric
    progression over time can be plotted.
    """
    league_table_all = league_table.copy()
    league_table_new = league_table.copy()

    for _, row in results_table.iterrows():
        home_team = row["HomeTeam"]
        away_team = row["AwayTeam"]
        home_team_goals = row["FTHG"]
        away_team_goals = row["FTAG"]
        full_time_result = row["FTR"]
        last_date = row["Date"]

        is_home = league_table_new["team"] == home_team
        is_away = league_table_new["team"] == away_team

        league_table_new.loc[is_home, "matched_played"] += 1
        league_table_new.loc[is_away, "matched_played"] += 1

        league_table_new.loc[is_home, "goals_for"] += home_team_goals
        league_table_new.loc[is_home, "goals_against"] += away_team_goals
        league_table_new.loc[is_away, "goals_for"] += away_team_goals
        league_table_new.loc[is_away, "goals_against"] += home_team_goals

        league_table_new.loc[is_home, "last_date"] = last_date
        league_table_new.loc[is_away, "last_date"] = last_date

        _apply_match_points(league_table_new, is_home, is_away, full_time_result)

        league_table_new["goal_difference"] = (
            league_table_new["goals_for"] - league_table_new["goals_against"]
        )
        league_table_new = _rank(league_table_new)

        updated_row = league_table_new[is_home | is_away]
        league_table_all = pd.concat([league_table_all, updated_row], ignore_index=True)

    return _rank(league_table_new), league_table_all


# ---------------------------------------------------------------------------
# ELO calculation
# ---------------------------------------------------------------------------
def expected_result_prob(
    home_score: float,
    away_score: float,
    weight: float = 400,
    home_field_advantage: float = 50,
) -> tuple[float, float]:
    """Expected win probability for the home and away team.

    Uses the standard ELO expected-score formula, with an optional constant
    added to the home team's rating to model home-field advantage::

        E_home = 1 / (1 + 10 ** (-(R_home - R_away + hfa) / weight))
    """
    diff_h_a = home_score - away_score + home_field_advantage
    we = 1 / (10 ** (-diff_h_a / weight) + 1)

    home_team_prob = np.round(we, 3)
    away_team_prob = np.round(1 - home_team_prob, 3)
    return home_team_prob, away_team_prob


def actual_result(result: str) -> tuple[float, float]:
    """Map a full-time result to ELO scores: win=1, draw=0.5, loss=0."""
    if result == "H":
        return 1.0, 0.0
    if result == "A":
        return 0.0, 1.0
    if result == "D":
        return 0.5, 0.5
    raise ValueError(f"FTR must be 'H', 'A' or 'D', got {result!r}")


def calculate_elo(
    elo_home: float,
    elo_away: float,
    final_result: str,
    k_value: float = 40,
    weight: float = 400,
    home_field_advantage: float = 50,
) -> tuple[float, float, list[float]]:
    """Return the updated home/away ELO ratings for a single match.

    Also returns ``stakes``: how many points each team would win/draw/lose,
    which is useful for illustrating what is at stake before a match.
    """
    k = k_value

    erh, era = expected_result_prob(
        elo_home, elo_away, weight=weight, home_field_advantage=home_field_advantage
    )
    arh, ara = actual_result(final_result)

    updated_elo_home = np.round(elo_home + k * (arh - erh), 3)
    updated_elo_away = np.round(elo_away + k * (ara - era), 3)

    stakes = [
        (1 - erh) * k,  # win_home
        (0 - erh) * k,  # lose_home
        (0.5 - erh) * k,  # draw_home
        (1 - era) * k,  # win_away
        (0 - era) * k,  # lose_away
        (0.5 - era) * k,  # draw_away
    ]

    return updated_elo_home, updated_elo_away, stakes


# ---------------------------------------------------------------------------
# ELO league table (plain table + an `elo` column)
# ---------------------------------------------------------------------------
def create_elo_league_table(
    data: pd.DataFrame, default_elo: float = 1500
) -> pd.DataFrame:
    """Create an empty league table with an ``elo`` column seeded to ``default_elo``."""
    league_table = pd.DataFrame()
    league_table["team"] = _unique_teams(data)
    league_table["ranking"] = 0
    # float() keeps the column as float so fractional ELO updates can be stored
    # (pandas refuses to assign a float into an int64 column).
    league_table["elo"] = float(default_elo)
    league_table["points"] = 0
    league_table["w"] = 0
    league_table["d"] = 0
    league_table["l"] = 0
    league_table["goals_for"] = 0
    league_table["goals_against"] = 0
    league_table["goal_difference"] = 0
    league_table["matched_played"] = 0
    league_table["last_date"] = min(data["Date"]) if "Date" in data.columns else 0
    return league_table


def update_elo_league_table(
    league_table: pd.DataFrame,
    results_table: pd.DataFrame,
    k_value: float = 40,
    weight: float = 400,
    home_field_advantage: float = 50,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Like :func:`update_league_table` but also updates each team's ELO rating."""
    league_table_all = league_table.copy()
    league_table_new = league_table.copy()

    for _, row in results_table.iterrows():
        home_team = row["HomeTeam"]
        away_team = row["AwayTeam"]
        home_team_goals = row["FTHG"]
        away_team_goals = row["FTAG"]
        full_time_result = row["FTR"]
        last_date = row["Date"]

        is_home = league_table_new["team"] == home_team
        is_away = league_table_new["team"] == away_team

        home_team_elo = league_table_new.loc[is_home, "elo"].values[0]
        away_team_elo = league_table_new.loc[is_away, "elo"].values[0]

        league_table_new.loc[is_home, "matched_played"] += 1
        league_table_new.loc[is_away, "matched_played"] += 1

        league_table_new.loc[is_home, "goals_for"] += home_team_goals
        league_table_new.loc[is_home, "goals_against"] += away_team_goals
        league_table_new.loc[is_away, "goals_for"] += away_team_goals
        league_table_new.loc[is_away, "goals_against"] += home_team_goals

        league_table_new.loc[is_home, "last_date"] = last_date
        league_table_new.loc[is_away, "last_date"] = last_date

        _apply_match_points(league_table_new, is_home, is_away, full_time_result)

        new_home_elo, new_away_elo, _ = calculate_elo(
            home_team_elo,
            away_team_elo,
            full_time_result,
            k_value=k_value,
            weight=weight,
            home_field_advantage=home_field_advantage,
        )
        league_table_new.loc[is_home, "elo"] = new_home_elo
        league_table_new.loc[is_away, "elo"] = new_away_elo

        league_table_new["goal_difference"] = (
            league_table_new["goals_for"] - league_table_new["goals_against"]
        )
        league_table_new = _rank(league_table_new)

        updated_row = league_table_new[is_home | is_away]
        league_table_all = pd.concat([league_table_all, updated_row], ignore_index=True)

    return _rank(league_table_new), league_table_all


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------
def _unique_teams(data: pd.DataFrame):
    """Every team appearing as home *or* away, in first-seen order."""
    return pd.concat([data["HomeTeam"], data["AwayTeam"]]).unique()


def _apply_match_points(table: pd.DataFrame, is_home, is_away, result: str) -> None:
    """Add points and win/draw/loss counts for a single match, in place."""
    if result == "H":
        table.loc[is_home, ["points", "w"]] += [3, 1]
        table.loc[is_away, "l"] += 1
    elif result == "A":
        table.loc[is_away, ["points", "w"]] += [3, 1]
        table.loc[is_home, "l"] += 1
    elif result == "D":
        table.loc[is_home | is_away, ["points", "d"]] += [1, 1]
    else:
        raise ValueError(f"FTR must be 'H', 'A' or 'D', got {result!r}")


def _rank(table: pd.DataFrame) -> pd.DataFrame:
    """Sort by points then tie-breakers and (re)assign the ``ranking`` column."""
    table = table.sort_values(
        by=["points", "goal_difference", "goals_for", "goals_against"],
        ascending=False,
    ).reset_index(drop=True)
    table["ranking"] = table.index + 1
    return table


if __name__ == "__main__":
    # Quick smoke test / demo: build the ELO table across all seasons on disk.
    results = read_results()
    table = create_elo_league_table(results, default_elo=1400)
    final_table, _ = update_elo_league_table(
        table, results, k_value=40, weight=400, home_field_advantage=60
    )
    top = final_table.sort_values("elo", ascending=False).head(10)
    print(top[["team", "elo", "points", "matched_played"]].to_string(index=False))
