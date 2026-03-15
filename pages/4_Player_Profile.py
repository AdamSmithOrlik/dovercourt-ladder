import streamlit as st
import pandas as pd

from db import get_players, get_matches, get_all_sets

st.set_page_config(page_title="Player Profile", layout="wide")


# ---------------------------------------------------
# LOAD DATA
# ---------------------------------------------------

players = get_players()
matches = get_matches()
sets = get_all_sets()

players_df = pd.DataFrame(players)
matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()
sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

player_name_map = {
    player["player_id"]: player["name"]
    for player in players
}


# ---------------------------------------------------
# PLAYER SELECTOR
# ---------------------------------------------------

player_names = sorted(players_df["name"].tolist())

selected_player = st.selectbox(
    "Select Player",
    player_names
)

player_id = players_df.loc[
    players_df["name"] == selected_player, "player_id"
].iloc[0]


# ---------------------------------------------------
# PLAYER MATCHES
# ---------------------------------------------------

player_matches = matches_df[
    (matches_df["player_id"] == player_id)
    | (matches_df["opponent_id"] == player_id)
].copy()


wins = (player_matches["winner_id"] == player_id).sum()
matches_played = len(player_matches)
losses = matches_played - wins


# ---------------------------------------------------
# SCORE DIFFERENTIAL (FAST VERSION)
# ---------------------------------------------------

if not sets_df.empty and not player_matches.empty:

    match_sets = sets_df.merge(
        player_matches[["match_id", "player_id", "opponent_id"]],
        on="match_id",
        how="inner"
    )

    match_sets["player_games_for_player"] = match_sets.apply(
        lambda r: r["player_games"]
        if r["player_id"] == player_id
        else r["opponent_games"],
        axis=1,
    )

    match_sets["opponent_games_for_player"] = match_sets.apply(
        lambda r: r["opponent_games"]
        if r["player_id"] == player_id
        else r["player_games"],
        axis=1,
    )

    score_diff = (
        match_sets["player_games_for_player"].sum()
        - match_sets["opponent_games_for_player"].sum()
    )

else:

    score_diff = 0


# ---------------------------------------------------
# HEADER
# ---------------------------------------------------

st.title(selected_player)

col1, col2, col3 = st.columns(3)

col1.metric("Record", f"{wins}-{losses}")
col2.metric("Matches Played", matches_played)
col3.metric("Score Differential", score_diff)

st.divider()


# ---------------------------------------------------
# RECENT MATCHES
# ---------------------------------------------------

st.subheader("Recent Matches")

if not player_matches.empty:

    display_df = player_matches.copy()

    display_df["Opponent"] = display_df.apply(
        lambda r: player_name_map[r["opponent_id"]]
        if r["player_id"] == player_id
        else player_name_map[r["player_id"]],
        axis=1,
    )

    display_df["Result"] = display_df["winner_id"].apply(
        lambda w: "Win" if w == player_id else "Loss"
    )

    display_df = display_df.sort_values(
        by="match_date",
        ascending=False
    )

    st.dataframe(
        display_df[
            [
                "match_date",
                "Opponent",
                "Result",
                "type",
            ]
        ],
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No matches found.")


# ---------------------------------------------------
# OPPONENT HISTORY
# ---------------------------------------------------

st.subheader("Opponent History")

if not player_matches.empty:

    opponent_matches = player_matches.copy()

    opponent_matches["opponent"] = opponent_matches.apply(
        lambda r: r["opponent_id"]
        if r["player_id"] == player_id
        else r["player_id"],
        axis=1,
    )

    opponent_matches["opponent_name"] = opponent_matches["opponent"].map(
        player_name_map
    )

    opponent_matches["win"] = opponent_matches["winner_id"] == player_id

    opponent_summary = (
        opponent_matches.groupby("opponent_name")
        .agg(
            Wins=("win", "sum"),
            Matches=("win", "count")
        )
        .reset_index()
    )

    opponent_summary["Losses"] = (
        opponent_summary["Matches"] - opponent_summary["Wins"]
    )

    opponent_summary["Record"] = (
        opponent_summary["Wins"].astype(str)
        + "-"
        + opponent_summary["Losses"].astype(str)
    )

    opponent_summary = opponent_summary.sort_values(
        by="Wins",
        ascending=False
    )

    st.dataframe(
        opponent_summary[
            ["opponent_name", "Record", "Matches"]
        ].rename(columns={"opponent_name": "Opponent"}),
        hide_index=True,
        use_container_width=True
    )

else:

    st.info("No opponent history yet.")
