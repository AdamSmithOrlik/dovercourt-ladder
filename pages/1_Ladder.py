import streamlit as st
import pandas as pd

from db import (
    get_active_players,
    get_players,
    get_matches_for_year,
    get_matches_for_year_and_round,
    get_sets,
)

from utils.elo import get_latest_elo_standings, get_elo_time_series
from utils.rounds import (
    get_round_window,
    get_last_completed_round_from_date,
    get_default_round_for_year,
    get_season_start_date,
    get_round_cutoff_exclusive,
)

st.set_page_config(page_title="Ladder", layout="wide")
st.title("Ladder")

BOX_SIZE = 5


# ---------------------------------------------------
# Box helpers
# ---------------------------------------------------

def assign_boxes(df: pd.DataFrame, box_size: int = 5) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df["box"] = ((df["rank"] - 1) // box_size) + 1

    last_box = int(df["box"].max())
    last_box_count = int((df["box"] == last_box).sum())

    if last_box > 1 and last_box_count < box_size:
        df.loc[df["box"] == last_box, "box"] = last_box - 1

    return df


# ---------------------------------------------------
# Stats helpers
# ---------------------------------------------------

def build_player_stats(year: int, round_number: int) -> pd.DataFrame:
    """
    Live stats for display:
    - live Elo for the year
    - overall wins/losses for the year
    - current round wins/losses
    """
    active_players = get_active_players()
    active_df = pd.DataFrame(active_players) if active_players else pd.DataFrame()

    if active_df.empty:
        return pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "elo",
                "wins",
                "losses",
                "round_wins",
                "round_losses",
            ]
        )

    season_start_date = get_season_start_date(year)

    standings_df = get_latest_elo_standings(
        year=year,
        season_start_date=season_start_date,
    )
    standings_df = (
        standings_df.copy()
        if standings_df is not None and not standings_df.empty
        else pd.DataFrame(columns=["player_id", "player_name", "elo"])
    )

    all_matches = get_matches_for_year(year)
    round_matches = get_matches_for_year_and_round(year, round_number)

    all_matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()
    round_matches_df = pd.DataFrame(round_matches) if round_matches else pd.DataFrame()

    if "player_id" not in active_df.columns:
        raise ValueError("get_active_players() must return a 'player_id' field.")

    player_base = active_df[["player_id", "name"]].copy()
    player_base = player_base.rename(columns={"name": "player_name"})

    if not standings_df.empty:
        player_base = player_base.merge(
            standings_df[["player_id", "elo"]],
            on="player_id",
            how="left",
        )
    else:
        player_base["elo"] = None

    # Overall wins / losses
    if not all_matches_df.empty:
        wins_df = (
            all_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="wins")
            .rename(columns={"winner_id": "player_id"})
        )

        player_side = all_matches_df[["player_id", "winner_id"]].copy()

        opponent_side = all_matches_df[["opponent_id", "winner_id"]].copy()
        opponent_side = opponent_side.rename(columns={"opponent_id": "player_id"})

        participant_rows = pd.concat(
            [player_side, opponent_side],
            ignore_index=True,
        )

        losses_df = (
            participant_rows[
                participant_rows["player_id"] != participant_rows["winner_id"]
            ]
            .groupby("player_id")
            .size()
            .reset_index(name="losses")
        )
    else:
        wins_df = pd.DataFrame(columns=["player_id", "wins"])
        losses_df = pd.DataFrame(columns=["player_id", "losses"])

    # Current round wins / losses
    if not round_matches_df.empty:
        round_wins_df = (
            round_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="round_wins")
            .rename(columns={"winner_id": "player_id"})
        )

        round_player_side = round_matches_df[["player_id", "winner_id"]].copy()

        round_opponent_side = round_matches_df[["opponent_id", "winner_id"]].copy()
        round_opponent_side = round_opponent_side.rename(
            columns={"opponent_id": "player_id"}
        )

        round_participant_rows = pd.concat(
            [round_player_side, round_opponent_side],
            ignore_index=True,
        )

        round_losses_df = (
            round_participant_rows[
                round_participant_rows["player_id"] != round_participant_rows["winner_id"]
            ]
            .groupby("player_id")
            .size()
            .reset_index(name="round_losses")
        )
    else:
        round_wins_df = pd.DataFrame(columns=["player_id", "round_wins"])
        round_losses_df = pd.DataFrame(columns=["player_id", "round_losses"])

    player_base = player_base.merge(wins_df, on="player_id", how="left")
    player_base = player_base.merge(losses_df, on="player_id", how="left")
    player_base = player_base.merge(round_wins_df, on="player_id", how="left")
    player_base = player_base.merge(round_losses_df, on="player_id", how="left")

    player_base["wins"] = player_base["wins"].fillna(0).astype(int)
    player_base["losses"] = player_base["losses"].fillna(0).astype(int)
    player_base["round_wins"] = player_base["round_wins"].fillna(0).astype(int)
    player_base["round_losses"] = player_base["round_losses"].fillna(0).astype(int)
    player_base["elo"] = pd.to_numeric(player_base["elo"], errors="coerce").fillna(1500.0)

    return player_base


def build_last_completed_round_order_stats(year: int, completed_round: int) -> pd.DataFrame:
    """
    Ordering stats from the last completed round only.

    Order should be:
    1. Elo as of the end of the last completed round
    2. wins in the last completed round
    3. player name
    """
    active_players = get_active_players()
    active_df = pd.DataFrame(active_players) if active_players else pd.DataFrame()

    if active_df.empty:
        return pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "completed_round_elo",
                "completed_round_wins",
            ]
        )

    player_base = active_df[["player_id", "name"]].copy()
    player_base = player_base.rename(columns={"name": "player_name"})

    round_window = get_round_window(year, completed_round)
    season_start_date = get_season_start_date(year)

    if round_window is None or season_start_date is None:
        player_base["completed_round_elo"] = 1500.0
        player_base["completed_round_wins"] = 0
        return player_base

    completed_round_end_exclusive = get_round_cutoff_exclusive(round_window["end_date"])

    completed_round_elo_df = get_latest_elo_standings(
        year=year,
        season_start_date=season_start_date,
        season_end_date=completed_round_end_exclusive,
    )

    completed_round_elo_df = (
        completed_round_elo_df.copy()
        if completed_round_elo_df is not None and not completed_round_elo_df.empty
        else pd.DataFrame(columns=["player_id", "elo"])
    )

    round_matches = get_matches_for_year_and_round(year, completed_round)
    round_matches_df = pd.DataFrame(round_matches) if round_matches else pd.DataFrame()

    if not completed_round_elo_df.empty:
        player_base = player_base.merge(
            completed_round_elo_df[["player_id", "elo"]],
            on="player_id",
            how="left",
        )
        player_base = player_base.rename(columns={"elo": "completed_round_elo"})
    else:
        player_base["completed_round_elo"] = 1500.0

    if not round_matches_df.empty:
        wins_df = (
            round_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="completed_round_wins")
            .rename(columns={"winner_id": "player_id"})
        )
    else:
        wins_df = pd.DataFrame(columns=["player_id", "completed_round_wins"])

    player_base = player_base.merge(wins_df, on="player_id", how="left")

    player_base["completed_round_elo"] = pd.to_numeric(
        player_base["completed_round_elo"], errors="coerce"
    ).fillna(1500.0)
    player_base["completed_round_wins"] = (
        player_base["completed_round_wins"].fillna(0).astype(int)
    )

    return player_base


def compute_live_ranking(stats_df: pd.DataFrame) -> pd.DataFrame:
    """
    Fallback ranking when no completed round exists yet,
    or for non-2026 years.
    """
    if stats_df.empty:
        return stats_df.copy()

    ranked = stats_df.sort_values(
        ["elo", "player_name"],
        ascending=[False, True],
    ).reset_index(drop=True)

    ranked["rank"] = range(1, len(ranked) + 1)
    ranked = assign_boxes(ranked, BOX_SIZE)

    return ranked


def compute_frozen_order_from_last_completed_round(
    live_stats_df: pd.DataFrame,
    year: int,
    completed_round: int,
) -> pd.DataFrame:
    """
    Freeze displayed order from the last completed round:
    1. completed round Elo
    2. completed round wins
    3. player name

    Displayed stats remain live.
    """
    if live_stats_df.empty:
        return live_stats_df.copy()

    order_df = build_last_completed_round_order_stats(year, completed_round)

    ranked = live_stats_df.merge(
        order_df[
            ["player_id", "player_name", "completed_round_elo", "completed_round_wins"]
        ],
        on=["player_id", "player_name"],
        how="left",
    )

    ranked["completed_round_elo"] = pd.to_numeric(
        ranked["completed_round_elo"], errors="coerce"
    ).fillna(1500.0)
    ranked["completed_round_wins"] = (
        ranked["completed_round_wins"].fillna(0).astype(int)
    )

    ranked = ranked.sort_values(
        ["completed_round_elo", "completed_round_wins", "player_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    ranked["rank"] = range(1, len(ranked) + 1)
    ranked = assign_boxes(ranked, BOX_SIZE)

    return ranked


def load_display_ladder(year: int, current_round: int) -> tuple[pd.DataFrame, str]:
    """
    2026:
    - order frozen from last completed round
    - stats live

    2025:
    - live Elo order
    - stats live
    """
    live_stats_df = build_player_stats(year, current_round)
    if live_stats_df.empty:
        return live_stats_df, "No ladder data"

    if year != 2026:
        live_df = compute_live_ranking(live_stats_df)
        return live_df, f"Live ladder for {year}"

    completed_year, completed_round = get_last_completed_round_from_date()

    if completed_year is None or completed_round is None or completed_year != year:
        live_df = compute_live_ranking(live_stats_df)
        return live_df, "Live ladder preview (no completed round yet)"

    frozen_df = compute_frozen_order_from_last_completed_round(
        live_stats_df=live_stats_df,
        year=year,
        completed_round=completed_round,
    )

    return frozen_df, f"Order frozen from round {completed_round}; stats are live"


# ---------------------------------------------------
# Match detail helpers
# ---------------------------------------------------

def get_player_recent_matches(player_id, year: int, limit: int = 3) -> pd.DataFrame:
    """Return the player's most recent matches for the selected year."""
    all_matches = get_matches_for_year(year)
    matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()

    if matches_df.empty:
        return pd.DataFrame(
            columns=["match_date", "opponent_name", "result", "score"]
        )

    player_matches = matches_df[
        (matches_df["player_id"] == player_id)
        | (matches_df["opponent_id"] == player_id)
    ].copy()

    if player_matches.empty:
        return pd.DataFrame(
            columns=["match_date", "opponent_name", "result", "score"]
        )

    all_players = get_players()
    players_df = pd.DataFrame(all_players) if all_players else pd.DataFrame()

    name_map = {}
    if (
        not players_df.empty
        and "player_id" in players_df.columns
        and "name" in players_df.columns
    ):
        name_map = dict(zip(players_df["player_id"], players_df["name"]))

    def opponent_for_row(row):
        return row["opponent_id"] if row["player_id"] == player_id else row["player_id"]

    def result_for_row(row):
        if row["winner_id"] == player_id:
            return "W"
        if pd.isna(row["winner_id"]):
            return "-"
        return "L"

    def score_for_match(row):
        sets = get_sets(row["match_id"])
        sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

        if sets_df.empty:
            return ""

        sets_df["set_number"] = pd.to_numeric(sets_df["set_number"], errors="coerce")
        sets_df["player_games"] = pd.to_numeric(sets_df["player_games"], errors="coerce")
        sets_df["opponent_games"] = pd.to_numeric(sets_df["opponent_games"], errors="coerce")

        sets_df = sets_df.dropna(
            subset=["set_number", "player_games", "opponent_games"]
        ).sort_values("set_number")

        score_parts = []

        for _, set_row in sets_df.iterrows():
            if row["player_id"] == player_id:
                my_games = int(set_row["player_games"])
                opp_games = int(set_row["opponent_games"])
            else:
                my_games = int(set_row["opponent_games"])
                opp_games = int(set_row["player_games"])

            score_parts.append(f"{my_games}-{opp_games}")

        return ", ".join(score_parts)

    player_matches["match_date"] = pd.to_datetime(
        player_matches["match_date"], errors="coerce"
    )

    player_matches = player_matches.sort_values(
        ["match_date", "match_id"],
        ascending=[False, False]
    ).head(limit).copy()

    player_matches["opponent_id_display"] = player_matches.apply(opponent_for_row, axis=1)
    player_matches["opponent_name"] = player_matches["opponent_id_display"].map(name_map)
    player_matches["opponent_name"] = player_matches["opponent_name"].fillna(
        player_matches["opponent_id_display"].astype(str)
    )

    player_matches["result"] = player_matches.apply(result_for_row, axis=1)
    player_matches["score"] = player_matches.apply(score_for_match, axis=1)

    return player_matches[["match_date", "opponent_name", "result", "score"]]


def get_player_season_match_history(year: int, player_id) -> pd.DataFrame:
    """
    Returns season-long match history for one player, including:
    - date
    - opponent
    - result
    - score
    - Elo after match
    - Elo change from match
    """
    season_start_date = get_season_start_date(year)

    elo_history_df = get_elo_time_series(
        year=year,
        season_start_date=season_start_date,
    )

    if elo_history_df is None or elo_history_df.empty:
        return pd.DataFrame(
            columns=[
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    elo_history_df = elo_history_df.copy()
    elo_history_df = elo_history_df[elo_history_df["player_id"] == player_id].copy()

    if elo_history_df.empty:
        return pd.DataFrame(
            columns=[
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    all_matches = get_matches_for_year(year)
    matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()

    if matches_df.empty:
        return pd.DataFrame(
            columns=[
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    all_players = get_players()
    players_df = pd.DataFrame(all_players) if all_players else pd.DataFrame()
    name_map = {}
    if (
        not players_df.empty
        and "player_id" in players_df.columns
        and "name" in players_df.columns
    ):
        name_map = dict(zip(players_df["player_id"], players_df["name"]))

    matches_df = matches_df.copy()
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")

    player_matches = matches_df[
        (matches_df["player_id"] == player_id) | (matches_df["opponent_id"] == player_id)
    ].copy()

    if player_matches.empty:
        return pd.DataFrame(
            columns=[
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    def opponent_for_row(row):
        return row["opponent_id"] if row["player_id"] == player_id else row["player_id"]

    def result_for_row(row):
        if row["winner_id"] == player_id:
            return "W"
        if pd.isna(row["winner_id"]):
            return "-"
        return "L"

    def score_for_match(row):
        sets = get_sets(row["match_id"])
        sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

        if sets_df.empty:
            return ""

        sets_df["set_number"] = pd.to_numeric(sets_df["set_number"], errors="coerce")
        sets_df["player_games"] = pd.to_numeric(sets_df["player_games"], errors="coerce")
        sets_df["opponent_games"] = pd.to_numeric(sets_df["opponent_games"], errors="coerce")
        sets_df = sets_df.dropna(subset=["set_number", "player_games", "opponent_games"])
        sets_df = sets_df.sort_values("set_number")

        score_parts = []

        for _, set_row in sets_df.iterrows():
            if row["player_id"] == player_id:
                my_games = int(set_row["player_games"])
                opp_games = int(set_row["opponent_games"])
            else:
                my_games = int(set_row["opponent_games"])
                opp_games = int(set_row["player_games"])

            score_parts.append(f"{my_games}-{opp_games}")

        return ", ".join(score_parts)

    player_matches["opponent_id_display"] = player_matches.apply(opponent_for_row, axis=1)
    player_matches["opponent_name"] = player_matches["opponent_id_display"].map(name_map)
    player_matches["opponent_name"] = player_matches["opponent_name"].fillna(
        player_matches["opponent_id_display"].astype(str)
    )
    player_matches["result"] = player_matches.apply(result_for_row, axis=1)
    player_matches["score"] = player_matches.apply(score_for_match, axis=1)

    player_matches = player_matches[
        ["match_id", "match_date", "opponent_name", "result", "score"]
    ].copy()

    history_df = elo_history_df.merge(
        player_matches,
        on="match_id",
        how="left",
    )

    history_df["match_date"] = pd.to_datetime(history_df["date"], errors="coerce")
    history_df["elo"] = pd.to_numeric(history_df["elo"], errors="coerce")
    history_df["elo_change"] = pd.to_numeric(history_df["elo_change"], errors="coerce")

    history_df = history_df.sort_values(["match_date", "match_id"]).reset_index(drop=True)

    return history_df[
        ["match_date", "opponent_name", "result", "score", "elo", "elo_change"]
    ]


def render_player_details(year: int, player_id, player_name: str) -> None:
    st.markdown(f"### {player_name}")

    # Season Elo history
    st.markdown("#### Season Match History + Elo Movement")
    season_history_df = get_player_season_match_history(year, player_id)

    if season_history_df.empty:
        st.caption("No completed match history found for this player in the selected year.")
        return

    display_history = season_history_df.copy()

    display_history["match_date"] = pd.to_datetime(
        display_history["match_date"], errors="coerce"
    )

    display_history = display_history.sort_values(
        ["match_date"],
        ascending=False,
    ).reset_index(drop=True)

    display_history["Date"] = display_history["match_date"].dt.strftime("%Y-%m-%d")
    display_history["Elo After"] = pd.to_numeric(
        display_history["elo"], errors="coerce"
    ).round(1)
    display_history["Elo +/-"] = pd.to_numeric(
        display_history["elo_change"], errors="coerce"
    ).round(1)

    st.dataframe(
        display_history[
            ["Date", "opponent_name", "result", "score", "Elo +/-", "Elo After"]
        ].rename(
            columns={
                "opponent_name": "Opponent",
                "result": "Result",
                "score": "Score",
            }
        ),
        width="stretch",
        hide_index=True,
        column_config={
            "Date": st.column_config.TextColumn("Date", width="small"),
            "Opponent": st.column_config.TextColumn("Opponent", width="large"),
            "Result": st.column_config.TextColumn("Result", width="small"),
            "Score": st.column_config.TextColumn("Score", width="medium"),
            "Elo +/-": st.column_config.NumberColumn("Elo +/-", format="%.1f", width="small"),
            "Elo After": st.column_config.NumberColumn("Elo After", format="%.1f", width="small"),
        },
    )

    st.markdown("#### Elo Over Time")
    chart_df = season_history_df.copy()
    chart_df = chart_df.dropna(subset=["match_date", "elo"])
    chart_df = chart_df.sort_values("match_date")

    if not chart_df.empty:
        chart_df = chart_df[["match_date", "elo"]].rename(
            columns={"match_date": "Date", "elo": "Elo"}
        )
        chart_df = chart_df.set_index("Date")
        st.line_chart(chart_df)


# ---------------------------------------------------
# Main ladder data
# ---------------------------------------------------

year_options = [2026, 2025]

if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = 2026

selected_year = st.selectbox(
    "Year",
    options=year_options,
    key="selected_year",
)

current_round = get_default_round_for_year(selected_year)

stats_df = build_player_stats(selected_year, current_round)

if stats_df.empty:
    st.info("No active players found.")
    st.stop()

display_df, status_text = load_display_ladder(selected_year, current_round)
st.caption(status_text)

selected_round_window = get_round_window(selected_year, current_round)
if selected_year == 2026 and selected_round_window:
    st.caption(
        f"Current round: Round {current_round} ({selected_round_window['start_date']} to {selected_round_window['end_date']})"
    )
elif selected_year == 2025:
    st.caption("Showing 2025 ladder.")


# ---------------------------------------------------
# Render ladder
# ---------------------------------------------------

st.subheader(f"{selected_year} Ladder")
st.caption("Select a player row to view their last 3 matches")

st.markdown(
    """
    <style>
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

display_table = display_df.copy()

display_table["wins"] = display_table["wins"].fillna(0).astype(int)
display_table["losses"] = display_table["losses"].fillna(0).astype(int)
display_table["round_wins"] = display_table["round_wins"].fillna(0).astype(int)
display_table["round_losses"] = display_table["round_losses"].fillna(0).astype(int)
display_table["elo"] = pd.to_numeric(display_table["elo"], errors="coerce").fillna(1500.0)

display_table["Round Record"] = (
    display_table["round_wins"].astype(str)
    + "-"
    + display_table["round_losses"].astype(str)
)
display_table["Record"] = (
    display_table["wins"].astype(str)
    + "-"
    + display_table["losses"].astype(str)
)
display_table["Elo"] = display_table["elo"].round(1)

display_table = display_table.rename(
    columns={
        "box": "Box",
        "rank": "Rank",
        "player_name": "Player",
    }
)

display_table = display_table[
    ["player_id", "Box", "Rank", "Player", "Round Record", "Record", "Elo"]
].sort_values(["Box", "Rank"], ascending=[True, True]).reset_index(drop=True)

# Spacer rows between boxes
table_rows = []
for idx, row in display_table.iterrows():
    if idx > 0:
        prev_box = int(display_table.iloc[idx - 1]["Box"])
        curr_box = int(row["Box"])
        if curr_box != prev_box:
            table_rows.append(
                {
                    "player_id": None,
                    "Box": "",
                    "Rank": "",
                    "Player": "",
                    "Round Record": "",
                    "Record": "",
                    "Elo": None,
                }
            )

    table_rows.append(row.to_dict())

interactive_table = pd.DataFrame(table_rows)

interactive_table["Show"] = False

edited_table = st.data_editor(
    interactive_table[["Show", "Box", "Rank", "Player", "Round Record", "Record", "Elo"]],
    width="stretch",
    height=450,
    hide_index=True,
    key="ladder_table_editor",
    disabled=["Box", "Rank", "Player", "Round Record", "Record", "Elo"],
    column_config={
        "Show": st.column_config.CheckboxColumn("Show", width="small"),
        "Box": st.column_config.TextColumn("Box", width="small"),
        "Rank": st.column_config.TextColumn("Rank", width="small"),
        "Player": st.column_config.TextColumn("Player", width="large"),
        "Round Record": st.column_config.TextColumn("Round Record", width="small"),
        "Record": st.column_config.TextColumn("Record", width="small"),
        "Elo": st.column_config.NumberColumn("Elo", format="%.1f", width="small"),
    },
)

edited_table = edited_table.copy()
edited_table["player_id"] = interactive_table["player_id"].values

selected_rows = edited_table[
    (edited_table["Show"] == True)
    & (edited_table["player_id"].notna())
]

if not selected_rows.empty:
    selected_row = selected_rows.iloc[0]

    selected_player_id = selected_row["player_id"]
    selected_player_name = selected_row["Player"]

    render_player_details(
        year=selected_year,
        player_id=selected_player_id,
        player_name=selected_player_name,
    )