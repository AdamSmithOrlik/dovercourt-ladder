from __future__ import annotations

from typing import Tuple

import pandas as pd

from db import (
    get_completed_matches_for_year,
    get_players_by_ids,
    get_sets_for_match_ids,
)

DEFAULT_INITIAL_RATING = 1500.0
DEFAULT_K_BASE = 24.0
DEFAULT_ALPHA = 1.0
DEFAULT_ELO_YEAR = 2025
DEFAULT_2025_SEASON_START = "2025-04-01"


def expected_score(rating_a: float, rating_b: float) -> float:
    """Compute expected Elo score for player A against player B."""
    return 1.0 / (1.0 + 10 ** ((rating_b - rating_a) / 400.0))


def compute_margin_multiplier(
    set_rows: pd.DataFrame,
    winner_id,
    player_id,
    opponent_id,
) -> float | None:
    """Compute margin multiplier using total game differential from set rows.

    Formula:
        margin_multiplier = (games_winner - games_loser) / total_games
    """
    if set_rows.empty:
        return None

    cleaned_sets = set_rows.copy()
    cleaned_sets["player_games"] = pd.to_numeric(
        cleaned_sets["player_games"], errors="coerce"
    )
    cleaned_sets["opponent_games"] = pd.to_numeric(
        cleaned_sets["opponent_games"], errors="coerce"
    )
    cleaned_sets = cleaned_sets.dropna(subset=["player_games", "opponent_games"])

    if cleaned_sets.empty:
        return None

    total_player_games = float(cleaned_sets["player_games"].sum())
    total_opponent_games = float(cleaned_sets["opponent_games"].sum())

    if winner_id == player_id:
        games_winner = total_player_games
        games_loser = total_opponent_games
    elif winner_id == opponent_id:
        games_winner = total_opponent_games
        games_loser = total_player_games
    else:
        return None

    total_games = games_winner + games_loser

    if total_games <= 0:
        return None

    game_diff = games_winner - games_loser
    return game_diff / total_games


def _parse_match_date_series(match_date_series: pd.Series) -> pd.Series:
    """Parse full YYYY-MM-DD dates and drop partial/invalid date strings."""
    date_part = match_date_series.astype(str).str.extract(r"^(\d{4}-\d{2}-\d{2})")[0]
    return pd.to_datetime(date_part, format="%Y-%m-%d", errors="coerce")


def load_elo_source_data(
    year: int = DEFAULT_ELO_YEAR,
    season_start_date: str | None = None,
    season_end_date: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load year-scoped match, set, and player data needed for Elo computation."""
    matches = get_completed_matches_for_year(year)

    if not matches:
        empty_matches = pd.DataFrame(
            columns=["match_id", "player_id", "opponent_id", "winner_id", "match_date"]
        )
        empty_sets = pd.DataFrame(
            columns=["match_id", "set_number", "player_games", "opponent_games"]
        )
        empty_players = pd.DataFrame(columns=["player_id", "name"])
        return empty_matches, empty_sets, empty_players

    matches_df = pd.DataFrame(matches)
    matches_df["match_date"] = _parse_match_date_series(matches_df["match_date"])
    matches_df = matches_df.dropna(subset=["match_date"])
    matches_df = matches_df[matches_df["match_date"].dt.year == year].copy()

    if season_start_date:
        season_start_ts = pd.to_datetime(
            season_start_date, format="%Y-%m-%d", errors="coerce"
        )
        if pd.notna(season_start_ts):
            matches_df = matches_df[matches_df["match_date"] >= season_start_ts]

    if season_end_date:
        season_end_ts = pd.to_datetime(
            season_end_date, format="%Y-%m-%d", errors="coerce"
        )
        if pd.notna(season_end_ts):
            matches_df = matches_df[matches_df["match_date"] < season_end_ts]

    if matches_df.empty:
        empty_sets = pd.DataFrame(
            columns=["match_id", "set_number", "player_games", "opponent_games"]
        )
        empty_players = pd.DataFrame(columns=["player_id", "name"])
        return matches_df, empty_sets, empty_players

    matches_df = matches_df.sort_values(
        ["match_date", "match_id"], ascending=[True, True]
    )

    match_ids = matches_df["match_id"].dropna().tolist()
    sets = get_sets_for_match_ids(match_ids)
    sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

    if not sets_df.empty:
        sets_df = sets_df.sort_values(
            ["match_id", "set_number"], ascending=[True, True]
        )

    participant_ids = sorted(
        set(matches_df["player_id"].dropna().tolist())
        | set(matches_df["opponent_id"].dropna().tolist())
    )

    players = get_players_by_ids(participant_ids)
    players_df = (
        pd.DataFrame(players)
        if players
        else pd.DataFrame(columns=["player_id", "name"])
    )

    return matches_df, sets_df, players_df


def compute_elo_for_matches(
    matches_df: pd.DataFrame,
    sets_df: pd.DataFrame,
    players_df: pd.DataFrame,
    initial_rating: float = DEFAULT_INITIAL_RATING,
    k_base: float = DEFAULT_K_BASE,
    alpha: float = DEFAULT_ALPHA,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Compute Elo time-series rows and latest Elo standings for prepared dataframes."""
    history_columns = [
        "date",
        "match_id",
        "player_id",
        "player_name",
        "opponent_id",
        "elo",
        "elo_change",
        "effective_k",
        "margin_multiplier",
    ]

    standings_columns = ["player_id", "player_name", "elo"]

    if matches_df.empty:
        empty_history = pd.DataFrame(columns=history_columns)
        empty_standings = pd.DataFrame(columns=standings_columns)
        return empty_history, empty_standings

    if players_df.empty:
        player_name_map = {}
    else:
        player_name_map = dict(zip(players_df["player_id"], players_df["name"]))

    ratings = {}

    known_player_ids = sorted(
        set(matches_df["player_id"].dropna().tolist())
        | set(matches_df["opponent_id"].dropna().tolist())
        | set(players_df["player_id"].dropna().tolist())
    )

    for player_id in known_player_ids:
        ratings[player_id] = float(initial_rating)

    sets_by_match = {}
    if not sets_df.empty:
        for match_id, match_sets in sets_df.groupby("match_id"):
            sets_by_match[match_id] = match_sets.sort_values("set_number")

    history_rows = []

    sorted_matches = matches_df.sort_values(
        ["match_date", "match_id"], ascending=[True, True]
    )

    for _, match in sorted_matches.iterrows():
        match_id = match["match_id"]
        player_id = match["player_id"]
        opponent_id = match["opponent_id"]
        winner_id = match["winner_id"]

        if player_id not in ratings:
            ratings[player_id] = float(initial_rating)
        if opponent_id not in ratings:
            ratings[opponent_id] = float(initial_rating)

        if winner_id not in {player_id, opponent_id}:
            continue

        match_sets = sets_by_match.get(match_id)
        if match_sets is None or match_sets.empty:
            continue

        margin_multiplier = compute_margin_multiplier(
            set_rows=match_sets,
            winner_id=winner_id,
            player_id=player_id,
            opponent_id=opponent_id,
        )

        if margin_multiplier is None:
            continue

        effective_k = float(k_base) * (1.0 + float(alpha) * margin_multiplier)

        pre_player_rating = ratings[player_id]
        pre_opponent_rating = ratings[opponent_id]

        expected_player = expected_score(pre_player_rating, pre_opponent_rating)
        expected_opponent = 1.0 - expected_player

        player_actual = 1.0 if winner_id == player_id else 0.0
        opponent_actual = 1.0 - player_actual

        player_delta = effective_k * (player_actual - expected_player)
        opponent_delta = effective_k * (opponent_actual - expected_opponent)

        ratings[player_id] = pre_player_rating + player_delta
        ratings[opponent_id] = pre_opponent_rating + opponent_delta

        match_date = pd.to_datetime(match["match_date"]).normalize()

        history_rows.append(
            {
                "date": match_date,
                "match_id": match_id,
                "player_id": player_id,
                "player_name": player_name_map.get(player_id, str(player_id)),
                "opponent_id": opponent_id,
                "elo": ratings[player_id],
                "elo_change": player_delta,
                "effective_k": effective_k,
                "margin_multiplier": margin_multiplier,
            }
        )

        history_rows.append(
            {
                "date": match_date,
                "match_id": match_id,
                "player_id": opponent_id,
                "player_name": player_name_map.get(opponent_id, str(opponent_id)),
                "opponent_id": player_id,
                "elo": ratings[opponent_id],
                "elo_change": opponent_delta,
                "effective_k": effective_k,
                "margin_multiplier": margin_multiplier,
            }
        )

    history_df = pd.DataFrame(history_rows, columns=history_columns)

    if history_df.empty:
        standings_rows = [
            {
                "player_id": player_id,
                "player_name": player_name_map.get(player_id, str(player_id)),
                "elo": rating,
            }
            for player_id, rating in ratings.items()
        ]
        standings_df = pd.DataFrame(standings_rows, columns=standings_columns)
        standings_df = standings_df.sort_values(
            ["elo", "player_name"], ascending=[False, True]
        ).reset_index(drop=True)
        return history_df, standings_df

    history_df = history_df.sort_values(
        ["date", "match_id", "player_id"], ascending=[True, True, True]
    )
    history_df = history_df.reset_index(drop=True)

    standings_rows = [
        {
            "player_id": player_id,
            "player_name": player_name_map.get(player_id, str(player_id)),
            "elo": rating,
        }
        for player_id, rating in ratings.items()
    ]

    standings_df = pd.DataFrame(standings_rows, columns=standings_columns)
    standings_df = standings_df.sort_values(
        ["elo", "player_name"], ascending=[False, True]
    )
    standings_df = standings_df.reset_index(drop=True)

    return history_df, standings_df


def build_elo_data_for_year(
    year: int = DEFAULT_ELO_YEAR,
    initial_rating: float = DEFAULT_INITIAL_RATING,
    k_base: float = DEFAULT_K_BASE,
    alpha: float = DEFAULT_ALPHA,
    season_start_date: str | None = None,
    season_end_date: str | None = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Load source data and return (time_series_df, latest_standings_df).

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame]
        - time_series_df columns:
          [date, match_id, player_id, player_name, opponent_id, elo, elo_change,
           effective_k, margin_multiplier]
        - latest_standings_df columns:
          [player_id, player_name, elo]
    """
    matches_df, sets_df, players_df = load_elo_source_data(
        year=year,
        season_start_date=season_start_date,
        season_end_date=season_end_date,
    )

    return compute_elo_for_matches(
        matches_df=matches_df,
        sets_df=sets_df,
        players_df=players_df,
        initial_rating=initial_rating,
        k_base=k_base,
        alpha=alpha,
    )


def get_elo_time_series_2025(
    initial_rating: float = DEFAULT_INITIAL_RATING,
    k_base: float = DEFAULT_K_BASE,
    alpha: float = DEFAULT_ALPHA,
    season_start_date: str | None = DEFAULT_2025_SEASON_START,
) -> pd.DataFrame:
    """Convenience helper returning 2025 Elo time-series data."""
    time_series_df, _ = build_elo_data_for_year(
        year=DEFAULT_ELO_YEAR,
        initial_rating=initial_rating,
        k_base=k_base,
        alpha=alpha,
        season_start_date=season_start_date,
    )
    return time_series_df


def get_latest_elo_standings_2025(
    initial_rating: float = DEFAULT_INITIAL_RATING,
    k_base: float = DEFAULT_K_BASE,
    alpha: float = DEFAULT_ALPHA,
    season_start_date: str | None = DEFAULT_2025_SEASON_START,
) -> pd.DataFrame:
    """Convenience helper returning latest 2025 Elo standings."""
    _, standings_df = build_elo_data_for_year(
        year=DEFAULT_ELO_YEAR,
        initial_rating=initial_rating,
        k_base=k_base,
        alpha=alpha,
        season_start_date=season_start_date,
    )
    return standings_df
