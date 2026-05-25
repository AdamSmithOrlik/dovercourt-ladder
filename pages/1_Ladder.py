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
from utils.ladder import compute_live_ranking, assign_boxes
from db import get_latest_ladder_box_snapshot

st.set_page_config(page_title="Ladder", layout="wide")
st.title("Ladder")

BOX_SIZE = 5


# ---------------------------------------------------
# Box helpers
# ---------------------------------------------------

def format_ladder_table(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["player_id", "Box", "Rank", "Player", "Round Record", "Record", "Elo"])

    display_table = df.copy()

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

    return pd.DataFrame(table_rows)


# ---------------------------------------------------
# Stats helpers
# ---------------------------------------------------

def build_player_stats(year: int, round_number: int) -> pd.DataFrame:
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

    player_base = active_df[["player_id", "name"]].copy()
    player_base = player_base.rename(columns={"name": "player_name"})

    if not standings_df.empty:
        player_base = player_base.merge(
            standings_df[["player_id", "elo"]],
            on="player_id",
            how="left",
        )
    else:
        player_base["elo"] = 1500.0

    if not all_matches_df.empty:
        wins_df = (
            all_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="wins")
            .rename(columns={"winner_id": "player_id"})
        )

        player_side = all_matches_df[["player_id", "winner_id"]]
        opponent_side = all_matches_df[["opponent_id", "winner_id"]].rename(
            columns={"opponent_id": "player_id"}
        )

        participant_rows = pd.concat([player_side, opponent_side], ignore_index=True)

        losses_df = (
            participant_rows[participant_rows["player_id"] != participant_rows["winner_id"]]
            .groupby("player_id")
            .size()
            .reset_index(name="losses")
        )
    else:
        wins_df = pd.DataFrame(columns=["player_id", "wins"])
        losses_df = pd.DataFrame(columns=["player_id", "losses"])

    if not round_matches_df.empty:
        round_wins_df = (
            round_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="round_wins")
            .rename(columns={"winner_id": "player_id"})
        )

        round_player_side = round_matches_df[["player_id", "winner_id"]]
        round_opponent_side = round_matches_df[["opponent_id", "winner_id"]].rename(
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

def build_last_completed_round_seeded_boxes(
    live_stats_df: pd.DataFrame,
    year: int,
    completed_round: int,
) -> pd.DataFrame:
    if live_stats_df.empty:
        return live_stats_df.copy()

    active_players = get_active_players()
    active_df = pd.DataFrame(active_players) if active_players else pd.DataFrame()

    if active_df.empty:
        return live_stats_df.copy()

    player_base = active_df[["player_id", "name"]].copy()
    player_base = player_base.rename(columns={"name": "player_name"})

    round_window = get_round_window(year, completed_round)
    season_start_date = get_season_start_date(year)

    if round_window is None or season_start_date is None:
        return compute_live_ranking(live_stats_df)

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
        player_base = player_base.rename(columns={"elo": "seed_elo"})
    else:
        player_base["seed_elo"] = 1500.0

    if not round_matches_df.empty:
        wins_df = (
            round_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="seed_round_wins")
            .rename(columns={"winner_id": "player_id"})
        )
    else:
        wins_df = pd.DataFrame(columns=["player_id", "seed_round_wins"])

    player_base = player_base.merge(wins_df, on="player_id", how="left")

    player_base["seed_elo"] = pd.to_numeric(
        player_base["seed_elo"], errors="coerce"
    ).fillna(1500.0)

    player_base["seed_round_wins"] = (
        player_base["seed_round_wins"].fillna(0).astype(int)
    )

    seeded_df = live_stats_df.merge(
        player_base[["player_id", "seed_elo", "seed_round_wins"]],
        on="player_id",
        how="left",
    )

    seeded_df["seed_elo"] = pd.to_numeric(
        seeded_df["seed_elo"], errors="coerce"
    ).fillna(1500.0)

    seeded_df["seed_round_wins"] = (
        seeded_df["seed_round_wins"].fillna(0).astype(int)
    )

    seeded_df = seeded_df.sort_values(
        ["seed_elo", "seed_round_wins", "player_name"],
        ascending=[False, False, True],
    ).reset_index(drop=True)

    seeded_df["rank"] = range(1, len(seeded_df) + 1)

    return assign_boxes(seeded_df, BOX_SIZE)


# ---------------------------------------------------
# Player detail helpers
# ---------------------------------------------------

def get_player_season_match_history(year: int, player_id) -> pd.DataFrame:
    season_start_date = get_season_start_date(year)

    elo_history_df = get_elo_time_series(
        year=year,
        season_start_date=season_start_date,
    )

    if elo_history_df is None or elo_history_df.empty:
        return pd.DataFrame()

    elo_history_df = elo_history_df.copy()
    elo_history_df = elo_history_df[elo_history_df["player_id"] == player_id].copy()

    if elo_history_df.empty:
        return pd.DataFrame()

    all_matches = get_matches_for_year(year)
    matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()

    if matches_df.empty:
        return pd.DataFrame()

    all_players = get_players()
    players_df = pd.DataFrame(all_players) if all_players else pd.DataFrame()
    name_map = dict(zip(players_df["player_id"], players_df["name"])) if not players_df.empty else {}

    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")

    player_matches = matches_df[
        (matches_df["player_id"] == player_id)
        | (matches_df["opponent_id"] == player_id)
    ].copy()

    if player_matches.empty:
        return pd.DataFrame()

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

    player_matches["opponent_id_display"] = player_matches.apply(opponent_for_row, axis=1)
    player_matches["opponent_name"] = player_matches["opponent_id_display"].map(name_map)
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

    return history_df[
        ["match_date", "opponent_name", "result", "score", "elo", "elo_change"]
    ].sort_values(["match_date", "match_id"])


def render_player_details(year: int, player_id, player_name: str) -> None:
    st.markdown(f"### {player_name}")
    st.markdown("#### Season Match History + Elo Movement")

    season_history_df = get_player_season_match_history(year, player_id)

    if season_history_df.empty:
        st.caption("No completed match history found for this player in the selected year.")
        return

    display_history = season_history_df.copy()
    display_history["Date"] = pd.to_datetime(
        display_history["match_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    display_history["Elo After"] = pd.to_numeric(
        display_history["elo"], errors="coerce"
    ).round(1)

    display_history["Elo +/-"] = pd.to_numeric(
        display_history["elo_change"], errors="coerce"
    ).round(1)

    display_history = display_history.sort_values(
        "Date",
        ascending=False,
    )

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
current_round_window = get_round_window(selected_year, current_round)

stats_df = build_player_stats(selected_year, current_round)

if stats_df.empty:
    st.info("No active players found.")
    st.stop()

live_df = compute_live_ranking(stats_df)

completed_year, completed_round = get_last_completed_round_from_date()

has_completed_round_for_year = (
    selected_year == 2026
    and completed_year == selected_year
    and completed_round is not None
)

if has_completed_round_for_year:
    seeded_boxes_df = build_last_completed_round_seeded_boxes(
        live_stats_df=stats_df,
        year=selected_year,
        completed_round=completed_round,
    )
else:
    seeded_boxes_df = live_df.copy()


if selected_year == 2026 and current_round_window:
    st.caption(
        f"Current round: Round {current_round} "
        f"({current_round_window['start_date']} to {current_round_window['end_date']})"
    )

    if has_completed_round_for_year:
        st.caption(
            f"Left table shows boxes seeded from the end of Round {completed_round}. "
            f"Right table shows live rankings as of now."
        )
    else:
        st.caption(
            "No completed round found yet, so both tables currently use the live ranking."
        )
else:
    st.caption(f"Showing {selected_year} ladder.")


# ---------------------------------------------------
# Render ladders
# ---------------------------------------------------

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

left_col, right_col = st.columns(2)

latest_snapshot = get_latest_ladder_box_snapshot(selected_year)
snapshot_df = pd.DataFrame(latest_snapshot) if latest_snapshot else pd.DataFrame()

if snapshot_df.empty:
    seeded_table = format_ladder_table(live_df)
    snapshot_caption = "No saved box snapshot found yet, showing live boxes."
else:
    snapshot_formatted = snapshot_df.rename(
        columns={
            "box_number": "box",
            "overall_rank": "rank",
            "player_name": "player_name",
            "elo": "elo",
        }
    )

    snapshot_formatted = snapshot_formatted.merge(
        stats_df[
            [
                "player_id",
                "wins",
                "losses",
                "round_wins",
                "round_losses",
            ]
        ],
        on="player_id",
        how="left",
    )

    snapshot_formatted["wins"] = snapshot_formatted["wins"].fillna(0).astype(int)
    snapshot_formatted["losses"] = snapshot_formatted["losses"].fillna(0).astype(int)
    snapshot_formatted["round_wins"] = snapshot_formatted["round_wins"].fillna(0).astype(int)
    snapshot_formatted["round_losses"] = snapshot_formatted["round_losses"].fillna(0).astype(int)

    seeded_table = format_ladder_table(snapshot_formatted)

    snapshot_round = int(snapshot_df["round_number"].iloc[0])
    snapshot_created_at = snapshot_df["created_at"].iloc[0]

    snapshot_caption = (
        f"Saved snapshot for Round {snapshot_round}, "
        f"created at {snapshot_created_at}"
    )

live_table = format_ladder_table(live_df)

with left_col:
    st.subheader(f"Round {current_round} Boxes")
    st.caption(snapshot_caption)

    st.dataframe(
        seeded_table[["Box", "Rank", "Player", "Round Record", "Record", "Elo"]],
        width="stretch",
        height=500,
        hide_index=True,
        column_config={
            "Box": st.column_config.TextColumn("Box", width="small"),
            "Rank": st.column_config.TextColumn("Rank", width="small"),
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Round Record": st.column_config.TextColumn("Round Record", width="small"),
            "Elo": st.column_config.NumberColumn("Elo", format="%.1f", width="small"),
        },
    )

with right_col:
    st.subheader("Live Rankings")
    st.caption("click on the box in the first column to see a player's last 3 matches")

    live_table_for_editor = live_table.copy()
    live_table_for_editor["Show"] = False

    edited_live_table = st.data_editor(
        live_table_for_editor[
            ["Show", "Box", "Rank", "Player", "Round Record", "Record", "Elo"]
        ],
        width="stretch",
        height=500,
        hide_index=True,
        key="live_ladder_table_editor",
        disabled=["Box", "Rank", "Player", "Round Record", "Record", "Elo"],
        column_config={
            "Show": st.column_config.CheckboxColumn("Show", width="small"),
            "Box": st.column_config.TextColumn("Box", width="small"),
            "Rank": st.column_config.TextColumn("Rank", width="small"),
            "Player": st.column_config.TextColumn("Player", width="medium"),
            "Round Record": st.column_config.TextColumn("Round Record", width="small"),
            "Record": st.column_config.TextColumn("Record", width="small"),
            "Elo": st.column_config.NumberColumn("Elo", format="%.1f", width="small"),
        },
    )

    edited_live_table = edited_live_table.copy()
    edited_live_table["player_id"] = live_table_for_editor["player_id"].values


# ---------------------------------------------------
# Player details
# ---------------------------------------------------

selected_rows = edited_live_table[
    (edited_live_table["Show"] == True)
    & (edited_live_table["player_id"].notna())
]

if not selected_rows.empty:
    selected_row = selected_rows.iloc[0]

    render_player_details(
        year=selected_year,
        player_id=selected_row["player_id"],
        player_name=selected_row["Player"],
    )