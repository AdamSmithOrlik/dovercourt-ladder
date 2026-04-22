import streamlit as st
import pandas as pd
from datetime import datetime

from db import (
    get_players,
    get_matches,
    get_sets,
    insert_match,
    insert_sets,
    insert_player,
    update_player_active_status,
    get_current_player_statuses,
    update_match,
    update_set,
    add_initial_player_status_for_next_round,
)

from utils.constants import MATCH_TYPES
from utils.score_parser import parse_score_flexible

from utils.rounds import get_current_round_from_date, ROUND_WINDOWS_2026

players = get_players()
current_statuses = get_current_player_statuses()

st.set_page_config(page_title="Dovercourt Ladder", layout="wide")

st.title("🎾 Dovercourt Ladder")

# -----------------------------------------------------
# STATE
# -----------------------------------------------------

if "active_page" not in st.session_state:
    st.session_state.active_page = None


# -----------------------------------------------------
# DATA
# -----------------------------------------------------

matches = get_matches()

players_df = pd.DataFrame(players)
matches_df = pd.DataFrame(matches) if matches else pd.DataFrame()

player_name_map = {p["player_id"]: p["name"] for p in players}


# -----------------------------------------------------
# ACTION BUTTONS
# -----------------------------------------------------

st.subheader("Actions")

row1 = st.columns(2)
row2 = st.columns(2)

if row1[0].button("🎾 Submit Match", use_container_width=True):
    st.session_state.active_page = "submit"

if row1[1].button("📝 Sign Up", use_container_width=True):
    st.session_state.active_page = "signup"

if row2[0].button("⚙️ Update Status", use_container_width=True):
    st.session_state.active_page = "status"

if row2[1].button("✏️ Edit Match", use_container_width=True):
    st.session_state.active_page = "edit"

st.divider()


# -----------------------------------------------------
# HOME DASHBOARD
# -----------------------------------------------------

if st.session_state.active_page is None:

    # -------------------------------------------------
    # WIN STREAKS
    # -------------------------------------------------

    st.subheader("🔥 Win Streaks")

    if matches:

        matches_df = matches_df.sort_values("match_date")

        streaks = {}

        for p in players:

            pid = p["player_id"]
            streak = 0

            player_matches = matches_df[
                (matches_df["player_id"] == pid)
                | (matches_df["opponent_id"] == pid)
            ].sort_values("match_date")

            for _, m in player_matches[::-1].iterrows():

                if m["winner_id"] == pid:
                    streak += 1
                else:
                    break

            if streak > 0:
                streaks[p["name"]] = streak

        if streaks:

            streak_df = pd.DataFrame(
                [{"Player": k, "Streak": v} for k, v in streaks.items()]
            ).sort_values("Streak", ascending=False)

            st.dataframe(
                streak_df,
                hide_index=True,
                use_container_width=True
            )

        else:
            st.write("No active streaks.")

    else:
        st.info("No matches recorded yet.")

    # -------------------------------------------------
    # ACTIVITY FEED
    # -------------------------------------------------

    st.subheader("📰 Activity Feed")

    if matches:

        feed = matches_df.sort_values("match_date", ascending=False).head(8)

        for _, row in feed.iterrows():

            winner = player_name_map[row["winner_id"]]
            p1 = player_name_map[row["player_id"]]
            p2 = player_name_map[row["opponent_id"]]

            loser = p2 if winner == p1 else p1

            st.markdown(
                f"**{winner}** def. {loser} — *{row['type']}*"
            )

    else:
        st.info("No activity yet.")


# -----------------------------
# SUBMIT MATCH
# -----------------------------

elif st.session_state.active_page == "submit":

    st.header("Submit Match")

    if not players:
        st.error("No players found.")
        st.stop()

    player_options = {p["name"]: p["player_id"] for p in players}

    # -----------------------------
    # PLAYER SELECTION (outside form)
    # -----------------------------

    player_name = st.selectbox(
        "Player",
        list(player_options.keys()),
        key="submit_player"
    )

    opponent_name = st.selectbox(
        "Opponent",
        list(player_options.keys()),
        key="submit_opponent"
    )

    score_text = st.text_input(
        "Score",
        placeholder="Examples: 6-4 4-6 10-8 | 8-6"
    )

    parsed_preview = parse_score_flexible(score_text)

    suggested_winner = None

    if parsed_preview:

        parsed_sets, p_sets, o_sets = parsed_preview

        preview = ", ".join(
            f"{s['player_games']}-{s['opponent_games']}"
            for s in parsed_sets
        )

        st.caption(f"Parsed sets: {preview}")

        if p_sets > o_sets:
            suggested_winner = player_name
        elif o_sets > p_sets:
            suggested_winner = opponent_name

    st.subheader("Confirm Winner")

    winner_name = st.radio(
        "Winner",
        options=[player_name, opponent_name],
        index=0 if suggested_winner != opponent_name else 1,
        horizontal=True
    )

    # -----------------------------
    # FORM (only for submission)
    # -----------------------------

    with st.form("match_form"):

        match_type = st.selectbox(
            "Match Type",
            MATCH_TYPES
        )

        match_date = st.date_input("Match Date")

        submitted = st.form_submit_button("Submit Match")

    # -----------------------------
    # SUBMIT
    # -----------------------------

    if submitted:

        if player_name == opponent_name:
            st.error("Player and opponent cannot be the same.")
            st.stop()

        parsed_result = parse_score_flexible(score_text)

        if not parsed_result:
            st.error("Invalid score format.")
            st.stop()

        parsed_sets, p_sets, o_sets = parsed_result

        player_id = player_options[player_name]
        opponent_id = player_options[opponent_name]
        winner_id = player_options[winner_name]

        match_date_obj = match_date if not isinstance(match_date, datetime) else match_date.date()
        calculated_year, calculated_round = get_current_round_from_date(match_date_obj)

        if calculated_round is None:
            st.error("That match date does not fall within a valid ladder round.")
            st.stop()

        match_data = {
            "player_id": player_id,
            "opponent_id": opponent_id,
            "winner_id": winner_id,
            "type": match_type,
            "match_date": str(match_date),
            "round": int(calculated_round),
        }

        match_row = insert_match(match_data)

        match_id = match_row["match_id"]

        sets_rows = []

        for s in parsed_sets:
            s["match_id"] = match_id
            sets_rows.append(s)

        insert_sets(sets_rows)

        st.success(f"Match submitted successfully for round {int(calculated_round)}.")

        st.session_state.active_page = None
        st.rerun()

# -----------------------------------------------------
# SIGN UP
# -----------------------------------------------------

elif st.session_state.active_page == "signup":

    st.header("Sign Up")

    with st.form("signup_form"):

        name = st.text_input("Name")
        email = st.text_input("Email")

        submitted = st.form_submit_button("Sign Up")

    if submitted:
        clean_name = name.strip()
        clean_email = email.strip().lower()

        if not clean_name or not clean_email:
            st.error("Name and email are required.")
        else:
            try:
                player_data = {
                    "name": clean_name,
                    "email": clean_email,
                }

                insert_player(player_data)
                add_initial_player_status_for_next_round(clean_email)

                st.success("Player added.")
                st.session_state.active_page = None
                st.rerun()

            except Exception as e:
                st.error(f"Could not add player: {e}")

# -----------------------------------------------------
# UPDATE STATUS
# -----------------------------------------------------



elif st.session_state.active_page == "status":

    st.header("Update Player Status")

    # Full roster: anyone can be selected
    player_options = {p["name"]: p for p in players}

    # Current effective statuses for toggle defaults
    status_by_player_id = {
        s["player_id"]: s
        for s in current_statuses
    }

    player_name = st.selectbox(
        "Search Player",
        list(player_options.keys())
    )

    player = player_options[player_name]
    current_status_row = status_by_player_id.get(player["player_id"])

    # Fallback default if no effective status row exists yet
    current_active = (
        current_status_row["active"]
        if current_status_row is not None
        else True
    )

    new_status = st.toggle(
        "Active",
        value=current_active
    )

    def format_round_option(round_info: dict) -> str:
        return (
            f"Round {round_info['round']} "
            f"({round_info['start_date'].strftime('%b %d, %Y')} - "
            f"{round_info['end_date'].strftime('%b %d, %Y')})"
        )

    round_options = {
        format_round_option(r): r
        for r in ROUND_WINDOWS_2026
    }

    current_year, current_round = get_current_round_from_date()
    if current_year == 2026 and current_round is not None:
        default_start_idx = next(
            (
                i for i, r in enumerate(ROUND_WINDOWS_2026)
                if r["round"] == current_round
            ),
            0
        )
    else:
        default_start_idx = 0

    start_round_label = st.selectbox(
        "Effective Starting Round",
        options=list(round_options.keys()),
        index=default_start_idx,
    )

    start_round = round_options[start_round_label]
    effective_date = start_round["start_date"].isoformat()

    eligible_end_rounds = [
        r for r in ROUND_WINDOWS_2026
        if r["start_date"] >= start_round["start_date"]
    ]

    end_round_options = {"No end date": None}
    end_round_options.update({
        format_round_option(r): r
        for r in eligible_end_rounds
    })

    end_round_label = st.selectbox(
        "End After Round",
        options=list(end_round_options.keys()),
        index=0,
        help="Choose the round after which this status should stop applying. Leave as 'No end date' for an ongoing status."
    )

    selected_end_round = end_round_options[end_round_label]
    end_date = (
        selected_end_round["end_date"].isoformat()
        if selected_end_round is not None
        else None
    )

    if st.button("Update Status", use_container_width=True):

        update_player_active_status(
            player["email"],
            new_status,
            effective_date=effective_date,
            end_date=end_date,
        )

        status_text = "active" if new_status else "inactive"

        if end_date:
            st.success(
                f"Scheduled {player_name} as {status_text} from {effective_date} to {end_date}."
            )
        else:
            st.success(
                f"Scheduled {player_name} as {status_text} starting {effective_date}."
            )

        st.session_state.active_page = None
        st.rerun()

# -----------------------------------------------------
# EDIT MATCH
# -----------------------------------------------------

elif st.session_state.active_page == "edit":

    st.header("Edit Match")

    matches = get_matches()

    if not matches:
        st.info("No matches available.")
        st.stop()

    matches_df = pd.DataFrame(matches)

    # -------------------------------------------------
    # MATCH SELECTION
    # -------------------------------------------------

    match_options = {
        f"{player_name_map[m['winner_id']]} def. "
        f"{player_name_map[m['opponent_id'] if m['winner_id']==m['player_id'] else m['player_id']]} "
        f"({m['match_date'][:10]})": m
        for _, m in matches_df.iterrows()
    }

    selected_label = st.selectbox(
        "Select Match",
        list(match_options.keys())
    )

    match = match_options[selected_label]
    match_id = match["match_id"]

    st.divider()

    # -------------------------------------------------
    # BASIC MATCH DATA
    # -------------------------------------------------

    player_id = match["player_id"]
    opponent_id = match["opponent_id"]

    player_name = player_name_map[player_id]
    opponent_name = player_name_map[opponent_id]

    st.subheader("Match Info")

    col1, col2 = st.columns(2)

    current_type = match["type"]

    if current_type not in MATCH_TYPES:
        match_type_index = 0
    else:
        match_type_index = MATCH_TYPES.index(current_type)

    with col1:
        new_type = st.selectbox(
            "Match Type",
            MATCH_TYPES,
            index=match_type_index
        )

    with col2:
        new_date = st.date_input(
            "Match Date",
            value=pd.to_datetime(match["match_date"])
        )

    # -------------------------------------------------
    # LOAD SETS
    # -------------------------------------------------

    sets = get_sets(match_id)

    if not sets:
        st.warning("No sets found for this match.")
        st.stop()

    sets_df = pd.DataFrame(sets).sort_values("set_number")

    st.subheader("Edit Sets")

    updated_sets = []

    for _, s in sets_df.iterrows():

        col1, col2 = st.columns(2)

        with col1:
            p_games = st.number_input(
                f"Player Games (Set {s['set_number']})",
                value=int(s["player_games"]),
                min_value=0,
                key=f"p_{s['set_id']}"
            )

        with col2:
            o_games = st.number_input(
                f"Opponent Games (Set {s['set_number']})",
                value=int(s["opponent_games"]),
                min_value=0,
                key=f"o_{s['set_id']}"
            )

        updated_sets.append({
            "set_id": s["set_id"],
            "player_games": p_games,
            "opponent_games": o_games,
            "is_tiebreak": p_games >= 10 or o_games >= 10
        })

    st.divider()

    # -------------------------------------------------
    # SAVE BUTTON
    # -------------------------------------------------

    if st.button("Save Changes", use_container_width=True):

        p_sets = 0
        o_sets = 0

        for s in updated_sets:

            if s["player_games"] > s["opponent_games"]:
                p_sets += 1
            else:
                o_sets += 1

        winner_id = player_id if p_sets > o_sets else opponent_id

        update_match(
            match_id,
            {
                "type": new_type,
                "match_date": str(new_date),
                "winner_id": winner_id
            }
        )

        for s in updated_sets:

            update_set(
                s["set_id"],
                {
                    "player_games": s["player_games"],
                    "opponent_games": s["opponent_games"],
                    "is_tiebreak": s["is_tiebreak"]
                }
            )

        st.success("Match updated successfully.")

        st.session_state.active_page = None
        st.rerun()