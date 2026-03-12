import streamlit as st
import pandas as pd
from db import get_players, insert_match

st.set_page_config(page_title="Submit Match", layout="wide")
st.title("Submit Match")

players = get_players()

if not players:
    st.error("No players found in the database.")
    st.stop()

players_df = pd.DataFrame(players)

players_df_display = players_df.rename(
    columns={"name": "Player Name", "email": "Email", "active": "Active"}
)

player_options = {player["name"]: player["id"] for player in players}

st.subheader("Player List")
st.dataframe(
    players_df_display[["Player Name", "Email", "Active"]],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Submit a New Match")
with st.form("match_form"):
    player1_name = st.selectbox("Player 1", list(player_options.keys()))
    player2_name = st.selectbox("Player 2", list(player_options.keys()))
    winner_name = st.selectbox("Winner", list(player_options.keys()))
    score_text = st.text_input("Score", placeholder="6-4,3-6,7-5(10-8)")
    match_date = st.date_input("Match Date")
    submitted_by_email = st.text_input("Your Email")

    submitted = st.form_submit_button("Submit Match")

if submitted:
    player1_id = player_options[player1_name]
    player2_id = player_options[player2_name]
    winner_id = player_options[winner_name]
    loser_id = player2_id if winner_id == player1_id else player1_id

    if player1_id == player2_id:
        st.error("Player 1 and Player 2 must be different.")
    elif winner_id not in [player1_id, player2_id]:
        st.error("Winner must be one of the two selected players.")
    elif not score_text.strip():
        st.error("Please enter a score.")
    elif not submitted_by_email.strip():
        st.error("Please enter your email.")
    else:
        match_data = {
            "player1_id": player1_id,
            "player2_id": player2_id,
            "winner_id": winner_id,
            "loser_id": loser_id,
            "score_text": score_text,
            "match_date": str(match_date),
            "submitted_by_email": submitted_by_email.strip(),
        }

        try:
            insert_match(match_data)
            st.success("Match submitted successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to submit match: {e}")
