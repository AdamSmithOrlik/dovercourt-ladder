import streamlit as st
from db import get_player_by_email_ex, update_player_active_status

st.set_page_config(page_title="Update Status", layout="wide")
st.title("Update Player Status")

if "player_lookup" not in st.session_state:
    st.session_state.player_lookup = None

st.write("Enter your email to view and update your ladder activity status.")

with st.form("status_form"):
    email = st.text_input("Email")
    email_confirm = st.text_input("Confirm Email")
    submitted = st.form_submit_button("Check Status")

if submitted:
    email = email.strip().lower()
    email_confirm = email_confirm.strip().lower()

    if not email:
        st.error("Please enter your email.")
    elif email != email_confirm:
        st.error("The email addresses do not match.")
    else:
        player_data = get_player_by_email_ex(email)

        if not player_data:
            st.error("No player found with that email.")
            st.session_state.player_lookup = None
        else:
            st.session_state.player_lookup = player_data[0]

player = st.session_state.player_lookup

if player is not None:
    current_status = bool(player["active"])
    new_status = not current_status

    st.success(f"Player found: {player['name']}")
    st.write(f"Current status: {'Active' if current_status else 'Inactive'}")

    toggle_label = (
        "Set myself to Inactive" if current_status else "Set myself to Active"
    )

    if st.button(toggle_label):
        try:
            update_player_active_status(player["email"], new_status)
            st.success(
                f"Your status has been updated to {'Active' if new_status else 'Inactive'}."
            )
            st.session_state.player_lookup = None
            st.rerun()
        except Exception as e:
            st.error(f"Failed to update status: {e}")
