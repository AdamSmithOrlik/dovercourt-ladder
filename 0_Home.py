import streamlit as st
from db import get_players, get_matches
from utils.rankings import compute_rankings

st.set_page_config(page_title="Dovercourt Ladder", layout="wide")

st.title("Dovercourt Ladder")
st.write("Welcome to the summer tennis ladder.")

players = get_players()
matches = get_matches()

rankings_df = compute_rankings(players, matches)

st.subheader("Rankings")
st.dataframe(rankings_df, use_container_width=True)
