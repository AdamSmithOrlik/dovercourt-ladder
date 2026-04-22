import streamlit as st
import pandas as pd

from db import (
    get_players,
    get_matches,
    get_all_sets,
    get_current_player_statuses,
    get_upcoming_player_status_changes,
)

st.set_page_config(page_title="Players", layout="wide")

st.title("Players")


# -----------------------------------------------------
# LOAD DATA
# -----------------------------------------------------

players = get_players()
current_statuses = get_current_player_statuses()
upcoming_status_changes = get_upcoming_player_status_changes()
matches = get_matches()
sets = get_all_sets()

players_df = pd.DataFrame(players)
status_df = pd.DataFrame(current_statuses) if current_statuses else pd.DataFrame()
upcoming_df = pd.DataFrame(upcoming_status_changes) if upcoming_status_changes else pd.DataFrame()
matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

if not matches_df.empty:
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")

if not sets_df.empty:
    sets_df["player_games"] = pd.to_numeric(sets_df["player_games"], errors="coerce")
    sets_df["opponent_games"] = pd.to_numeric(sets_df["opponent_games"], errors="coerce")

if not players_df.empty:
    players_df = players_df.drop(columns=["active"], errors="ignore")

if players_df.empty:
    st.info("No players found.")
    st.stop()


# -----------------------------------------------------
# MERGE CURRENT STATUS
# -----------------------------------------------------

if not status_df.empty:
    status_df = status_df[["player_id", "active"]].drop_duplicates(subset=["player_id"], keep="last")
    players_df = players_df.merge(status_df, on="player_id", how="left")
else:
    players_df["active"] = False

players_df["active"] = players_df["active"].fillna(False)


# -----------------------------------------------------
# PLAYER STATS
# -----------------------------------------------------

player_stats = []

for _, player in players_df.iterrows():
    pid = player["player_id"]

    player_matches = matches_df[
        (matches_df["player_id"] == pid)
        | (matches_df["opponent_id"] == pid)
    ] if not matches_df.empty else pd.DataFrame()

    matches_played = len(player_matches)

    if not player_matches.empty:
        last_match = player_matches["match_date"].max()
    else:
        last_match = None

    player_stats.append({
        "Player": player["name"],
        "Active": "🟢" if bool(player["active"]) else "⚪",
        "Email": player.get("email", ""),
        "Phone": player.get("cell_phone", ""),
        "Matches": matches_played,
        "Last Match": last_match,
    })

stats_df = pd.DataFrame(player_stats)

if not stats_df.empty:
    stats_df = stats_df.sort_values(
        by=["Player", "Email"],
        ascending=[True, True]
    )


# -----------------------------------------------------
# DISPLAY TABLE
# -----------------------------------------------------

st.dataframe(
    stats_df,
    use_container_width=True,
    hide_index=True
)


# -----------------------------------------------------
# UPCOMING STATUS CHANGES
# -----------------------------------------------------

st.subheader("⏳ Upcoming Status Changes")

if upcoming_df.empty:
    st.info("No upcoming status changes scheduled.")
else:
    upcoming_df["Status"] = upcoming_df["active"].apply(
        lambda x: "Active" if x else "Inactive"
    )

    display_df = upcoming_df[[
        "name",
        "email",
        "Status",
        "effective_date",
        "end_date",
    ]].rename(columns={
        "name": "Player",
        "email": "Email",
        "effective_date": "Start",
        "end_date": "End",
    })

    st.dataframe(
        display_df.sort_values(by=["Start", "Player"]),
        use_container_width=True,
        hide_index=True
    )