import streamlit as st
import pandas as pd
from datetime import datetime

from db import get_matches, get_players, get_all_sets

st.set_page_config(page_title="Match History", layout="wide")

st.title("Match History")


# -----------------------------------------------------
# LOAD DATA
# -----------------------------------------------------

players = get_players()
matches = get_matches()
sets = get_all_sets()

if not matches:
    st.info("No matches found yet.")
    st.stop()

players_df = pd.DataFrame(players)
matches_df = pd.DataFrame(matches)
sets_df = pd.DataFrame(sets)

matches_df["match_date"] = pd.to_datetime(matches_df["match_date"])


# -----------------------------------------------------
# PLAYER MAP
# -----------------------------------------------------

player_name_map = {
    p["player_id"]: p["name"]
    for p in players
}


# -----------------------------------------------------
# BUILD SCORE
# -----------------------------------------------------

def build_score(match_id):
    s = sets_df[sets_df["match_id"] == match_id].sort_values("set_number")

    if s.empty:
        return ""

    scores = []

    for _, r in s.iterrows():
        scores.append(f"{r['player_games']}-{r['opponent_games']}")

    return ", ".join(scores)


matches_df["Score"] = matches_df["match_id"].apply(build_score)

matches_df["Player"] = matches_df["player_id"].map(player_name_map)
matches_df["Opponent"] = matches_df["opponent_id"].map(player_name_map)
matches_df["Winner"] = matches_df["winner_id"].map(player_name_map)


# -----------------------------------------------------
# FILTERS
# -----------------------------------------------------

st.subheader("Filters")

current_year = datetime.now().year
year_options = ["All"] + sorted(matches_df["match_date"].dt.year.unique())

col1, col2 = st.columns(2)

with col1:
    year_selected = st.selectbox(
        "Year",
        year_options,
        index=year_options.index(current_year) if current_year in year_options else 0
    )

with col2:
    player_options = ["No player selected"] + sorted(players_df["name"].dropna().tolist())

    player_choice = st.selectbox(
        "Player",
        player_options,
        index=0
    )

filtered_matches = matches_df.copy()

if year_selected != "All":
    filtered_matches = filtered_matches[
        filtered_matches["match_date"].dt.year == year_selected
    ]

selected_player_id = None

if player_choice != "No player selected":
    selected_player_id = players_df.loc[
        players_df["name"] == player_choice,
        "player_id"
    ].iloc[0]

    filtered_matches = filtered_matches[
        (filtered_matches["player_id"] == selected_player_id)
        | (filtered_matches["opponent_id"] == selected_player_id)
    ]

filtered_sets = sets_df[
    sets_df["match_id"].isin(filtered_matches["match_id"])
]


# -----------------------------------------------------
# MATCH INSIGHTS
# -----------------------------------------------------

st.subheader("Match Insights")

if not filtered_matches.empty:

    total_matches = len(filtered_matches)

    total_points = (
        filtered_sets["player_games"].sum()
        + filtered_sets["opponent_games"].sum()
    )

    most_recent = filtered_matches.sort_values(
        "match_date",
        ascending=False
    ).iloc[0]

    col1, col2, col3 = st.columns(3)

    col1.metric("Matches Played", total_matches)
    col2.metric("Total Points Played", int(total_points))
    col3.metric(
        "Most Recent Match",
        f"{most_recent['Player']} vs {most_recent['Opponent']}"
    )

else:
    st.info("No matches for this selection.")


# -----------------------------------------------------
# HEAD TO HEAD MATRIX
# -----------------------------------------------------

with st.expander("Head-to-Head Matrix"):

    if selected_player_id is None:
        matrix_players = players_df.copy()
    else:
        relevant_player_ids = set()

        for _, match in filtered_matches.iterrows():
            relevant_player_ids.add(match["player_id"])
            relevant_player_ids.add(match["opponent_id"])

        matrix_players = players_df[
            players_df["player_id"].isin(relevant_player_ids)
        ]

    names = sorted(matrix_players["name"].dropna().tolist())

    matrix = pd.DataFrame("", index=names, columns=names)

    for _, match in filtered_matches.iterrows():

        p = player_name_map[match["player_id"]]
        o = player_name_map[match["opponent_id"]]
        w = player_name_map[match["winner_id"]]

        if w == p:
            matrix.loc[p, o] += "W"
            matrix.loc[o, p] += "L"
        else:
            matrix.loc[p, o] += "L"
            matrix.loc[o, p] += "W"

    st.dataframe(matrix, use_container_width=True)

# -----------------------------------------------------
# MATCH DETAILS
# -----------------------------------------------------

st.subheader("Match Details")

matches_sorted = filtered_matches.sort_values(
    "match_date",
    ascending=False
)

if matches_sorted.empty:

    st.info("No matches found.")

else:

    for _, row in matches_sorted.iterrows():

        winner = row["Winner"]
        p1 = row["Player"]
        p2 = row["Opponent"]

        loser = p2 if winner == p1 else p1

        match_sets = filtered_sets[
            filtered_sets["match_id"] == row["match_id"]
        ].sort_values("set_number")

        score_parts = []

        if not match_sets.empty:

            for _, s in match_sets.iterrows():

                p_games = int(s["player_games"])
                o_games = int(s["opponent_games"])

                score_parts.append(f"{p_games}-{o_games}")

        score_text = ", ".join(score_parts)

        title = f"{winner} def. {loser} {score_text} — {row['type']}"

        with st.expander(title):

            st.write("Winner:", winner)
            st.write("Match Type:", row["type"])
            st.write("Date:", row["match_date"].date())

            if not match_sets.empty:

                set_table = match_sets[[
                    "set_number",
                    "player_games",
                    "opponent_games",
                    "is_tiebreak"
                ]]

                set_table.columns = [
                    "Set",
                    p1,
                    p2,
                    "Tiebreak"
                ]

                st.dataframe(
                    set_table,
                    hide_index=True,
                    use_container_width=True
                )