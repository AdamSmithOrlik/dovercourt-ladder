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
    columns={"name": "Player Name", "active": "Active", "ladder_group": "Ladder Group"}
)

players_df_display["Active"] = players_df_display["Active"].map(
    {True: "🟢", False: "⚪"}
)
# sort by Ladder Group
players_df_display = players_df_display.sort_values(
    by="Ladder Group", na_position="last"
)

player_options = {player["name"]: player["id"] for player in players}

st.subheader("Player List")
st.dataframe(
    players_df_display[["Player Name", "Active", "Ladder Group"]],
    width="content",
    hide_index=True,
)

# initialize session state flags
if "match_submit_in_progress" not in st.session_state:
    st.session_state.match_submit_in_progress = False

if "match_submit_success" not in st.session_state:
    st.session_state.match_submit_success = False


# show success notice after rerun
if st.session_state.match_submit_success:
    st.success("Match submitted successfully.")
    st.session_state.match_submit_success = False


st.subheader("Submit a New Match")
with st.form("match_form"):
    player1_name = st.selectbox(
        "Player 1",
        list(player_options.keys()),
        index=None,
        placeholder="Select Player...",
    )
    player2_name = st.selectbox(
        "Player 2",
        list(player_options.keys()),
        index=None,
        placeholder="Select Player...",
    )
    winner_name = st.selectbox(
        "Winner",
        list(player_options.keys()),
        index=None,
        placeholder="Select Winner...",
    )
    score_text = st.text_input(
        "Score (leave blank for default)", placeholder="6-4,3-6,7-5(10-8)"
    )
    match_date = st.date_input("Match Date")
    submitted_by_email = st.text_input("Your Email")

    submitted = st.form_submit_button(
        "Submit Match",
        disabled=st.session_state.match_submit_in_progress,
    )

if submitted:
    # prevent double submission
    if st.session_state.match_submit_in_progress:
        st.warning("Submission already in progress.")
    else:
        st.session_state.match_submit_in_progress = True

        player1_id = player_options[player1_name]
        player2_id = player_options[player2_name]
        winner_id = player_options[winner_name]
        loser_id = player2_id if winner_id == player1_id else player1_id

        if player1_id == player2_id:
            st.error("Player 1 and Player 2 must be different.")
            st.session_state.match_submit_in_progress = False

        elif winner_id not in [player1_id, player2_id]:
            st.error("Winner must be one of the two selected players.")
            st.session_state.match_submit_in_progress = False

        elif not score_text.strip():
            st.error("Please enter a score.")
            st.session_state.match_submit_in_progress = False

        elif not submitted_by_email.strip():
            st.error("Please enter your email.")
            st.session_state.match_submit_in_progress = False

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
                st.session_state.match_submit_success = True
                st.session_state.match_submit_in_progress = False
                st.rerun()

            except Exception as e:
                st.session_state.match_submit_in_progress = False
                st.error(f"Failed to submit match: {e}")
