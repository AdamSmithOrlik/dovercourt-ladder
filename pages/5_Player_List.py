import streamlit as st
import pandas as pd

from db import get_players, get_matches, get_all_sets

st.set_page_config(page_title="Players", layout="wide")

st.title("Players")


# -----------------------------------------------------
# LOAD DATA
# -----------------------------------------------------

players = get_players()
matches = get_matches()
sets = get_all_sets()

players_df = pd.DataFrame(players)
matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()

if not matches_df.empty:
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")


sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

# fix mixed types from CSV import
if not sets_df.empty:
    sets_df["player_games"] = pd.to_numeric(sets_df["player_games"], errors="coerce")
    sets_df["opponent_games"] = pd.to_numeric(sets_df["opponent_games"], errors="coerce")


if players_df.empty:
    st.info("No players found.")
    st.stop()


# -----------------------------------------------------
# PLAYER STATS
# -----------------------------------------------------

player_stats = []

for _, player in players_df.iterrows():

    pid = player["player_id"]

    player_matches = matches_df[
        (matches_df["player_id"] == pid)
        | (matches_df["opponent_id"] == pid)
    ]

    wins = (player_matches["winner_id"] == pid).sum()
    matches_played = len(player_matches)
    losses = matches_played - wins

    win_pct = round((wins / matches_played) * 100, 1) if matches_played else 0

    # -------------------------------------------------
    # LAST MATCH DATE
    # -------------------------------------------------

    if not player_matches.empty:
        last_match = player_matches["match_date"].max()
    else:
        last_match = None


    player_stats.append({
        "Player": player["name"],
        "Active": "🟢" if player["active"] else "⚪",
        "Email": player.get("email", ""),
        "Phone": player.get("cell_phone", ""),
        "Matches": matches_played,
        "Last Match": last_match
    })


stats_df = pd.DataFrame(player_stats)

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

