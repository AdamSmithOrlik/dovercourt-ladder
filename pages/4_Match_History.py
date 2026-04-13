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
# YEAR FILTER
# -----------------------------------------------------

st.subheader("Filters")

current_year = datetime.now().year
year_options = ["All"] + sorted(matches_df["match_date"].dt.year.unique())

year_selected = st.selectbox(
    "Year",
    year_options,
    index=year_options.index(current_year) if current_year in year_options else 0
)

filtered_matches = matches_df.copy()

if year_selected != "All":
    filtered_matches = filtered_matches[
        filtered_matches["match_date"].dt.year == year_selected
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

    names = players_df["name"].tolist()

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
# PLAYER RIVALRIES
# -----------------------------------------------------

st.subheader("Player Rivalries")

player_choice = st.selectbox(
    "Select Player",
    players_df["name"]
)

player_id = players_df.loc[
    players_df["name"] == player_choice, "player_id"
].iloc[0]

player_matches = filtered_matches[
    (filtered_matches["player_id"] == player_id)
    | (filtered_matches["opponent_id"] == player_id)
]

opponent_ids = []

for _, m in player_matches.iterrows():

    if m["player_id"] == player_id:
        opponent_ids.append(m["opponent_id"])
    else:
        opponent_ids.append(m["player_id"])

if opponent_ids:

    rival_counts = pd.Series(opponent_ids).value_counts()

    rivalry_df = pd.DataFrame({
        "Opponent": [player_name_map[i] for i in rival_counts.index],
        "Matches Played": rival_counts.values
    })

    st.dataframe(
        rivalry_df,
        use_container_width=True,
        hide_index=True
    )

else:

    st.write("No rivalries yet.")


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

        # -------------------------------------------------
        # BUILD SCORE STRING
        # -------------------------------------------------

        score_parts = []

        if not match_sets.empty:

            for _, s in match_sets.iterrows():

                p_games = int(s["player_games"])
                o_games = int(s["opponent_games"])

                score_parts.append(f"{p_games}-{o_games}")

        score_text = ", ".join(score_parts)

        # -------------------------------------------------
        # EXPANDER TITLE
        # -------------------------------------------------

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
