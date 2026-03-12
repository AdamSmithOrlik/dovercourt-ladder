import streamlit as st
import pandas as pd
from db import get_players, get_player_by_email, insert_player

st.set_page_config(page_title="Sign Up", layout="wide")
st.title("Player Sign Up")

st.write("Join the Dovercourt Ladder.")

with st.form("signup_form"):
    name = st.text_input("Full Name")
    email = st.text_input("Email")
    submitted = st.form_submit_button("Sign Up")
    # agree = st.checkbox("I want to join the ladder")

if submitted:
    name = name.strip()
    email = email.strip().lower()

    if not name:
        st.error("Please enter your name.")
    elif not email:
        st.error("Please enter your email.")
    elif "@" not in email or "." not in email:
        st.error("Please enter a valid email.")
    else:
        existing = get_player_by_email(email)

        if existing:
            st.warning("A player with this email already exists.")
        else:
            player_data = {
                "name": name,
                "email": email,
                "active": True,
            }

            try:
                insert_player(player_data)
                st.success(f"{name} was added successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to add player: {e}")

st.subheader("Current Players")

players = get_players()
if players:
    players_df = pd.DataFrame(players)
    display_df = players_df.rename(
        columns={
            "name": "Player Name",
            "active": "Active",
        }
    )
    cols = [c for c in ["Player Name", "Active"] if c in display_df.columns]
    st.dataframe(display_df[cols], width="content", hide_index=True)
else:
    st.info("No players found.")
