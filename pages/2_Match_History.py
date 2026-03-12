import streamlit as st
import pandas as pd
from db import get_matches, get_players

st.set_page_config(page_title="Match History", layout="wide")
st.title("Match History")

players = get_players()
matches = get_matches()

if not matches:
    st.info("No matches found yet.")
    st.stop()

player_name_map = {player["id"]: player["name"] for player in players}
matches_df = pd.DataFrame(matches)

matches_df["Player 1"] = matches_df["player1_id"].map(player_name_map)
matches_df["Player 2"] = matches_df["player2_id"].map(player_name_map)
matches_df["Winner"] = matches_df["winner_id"].map(player_name_map)

display_cols = [
    "match_date",
    "Player 1",
    "Player 2",
    "Winner",
    "score_text",
    "submitted_by_email",
]

st.dataframe(matches_df[display_cols], width="content", hide_index=False)
