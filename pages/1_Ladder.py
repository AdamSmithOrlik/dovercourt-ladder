import streamlit as st
import pandas as pd

from db import (
    get_active_players,
    get_players,
    get_matches_for_year,
    get_matches,
    get_sets,
    get_matches_for_year_and_round,
    get_ladder_snapshot,
    delete_ladder_snapshot,
    insert_ladder_snapshot,
    get_latest_match_year_and_round,
)

from utils.elo import get_latest_elo_standings

st.set_page_config(page_title="Ladder", layout="wide")
st.title("Ladder")

BOX_SIZE = 5


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def get_default_year_and_round() -> tuple[int, int]:
    """
    Default behavior:
    - Start from latest round that has matches.
    - If the *next* round already has a snapshot, use that as the default instead.
      Example:
        latest matches = round 7
        snapshot exists for round 8
        => default round is 8
    """
    default_year, default_round = get_latest_match_year_and_round()

    next_round_snapshot = get_ladder_snapshot(default_year, default_round + 1)
    if next_round_snapshot:
        return default_year, default_round + 1

    current_round_snapshot = get_ladder_snapshot(default_year, default_round)
    if current_round_snapshot:
        return default_year, default_round

    return default_year, default_round


def get_year_options(matches_df: pd.DataFrame, default_year: int) -> list[int]:
    if matches_df.empty:
        return [default_year]

    year_options = sorted(matches_df["year"].dropna().unique().tolist())
    if default_year not in year_options:
        year_options.append(default_year)
        year_options = sorted(year_options)

    return year_options


def get_round_options_for_year(matches_df: pd.DataFrame, selected_year: int, default_round: int) -> list[int]:
    """
    Include:
    - all rounds that have matches
    - the default round
    - the next round if it already has a snapshot
    """
    round_options = set()

    if not matches_df.empty:
        year_match_rounds = matches_df.loc[
            matches_df["year"] == selected_year, "round"
        ].dropna().astype(int).tolist()
        round_options.update(year_match_rounds)

    round_options.add(default_round)

    # Also include default_round + 1 if that snapshot exists
    next_snapshot = get_ladder_snapshot(selected_year, default_round + 1)
    if next_snapshot:
        round_options.add(default_round + 1)

    return sorted(round_options)


def build_player_stats(year: int, round_number: int) -> pd.DataFrame:
    active_players = get_active_players()
    active_df = pd.DataFrame(active_players) if active_players else pd.DataFrame()

    if active_df.empty:
        return pd.DataFrame(
            columns=[
                "player_id",
                "player_name",
                "elo",
                "wins",
                "losses",
                "round_wins",
                "round_losses",
            ]
        )

    standings_df = get_latest_elo_standings(year=year)
    standings_df = (
        standings_df.copy()
        if standings_df is not None and not standings_df.empty
        else pd.DataFrame(columns=["player_id", "player_name", "elo"])
    )

    all_matches = get_matches_for_year(year)
    round_matches = get_matches_for_year_and_round(year, round_number)

    all_matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()
    round_matches_df = pd.DataFrame(round_matches) if round_matches else pd.DataFrame()

    if "player_id" not in active_df.columns:
        raise ValueError("get_active_players() must return a 'player_id' field.")

    player_base = active_df[["player_id", "name"]].copy()
    player_base = player_base.rename(columns={"name": "player_name"})

    if not standings_df.empty:
        player_base = player_base.merge(
            standings_df[["player_id", "elo"]],
            on="player_id",
            how="left",
        )
    else:
        player_base["elo"] = None

    # Overall wins / losses
    if not all_matches_df.empty:
        wins_df = (
            all_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="wins")
            .rename(columns={"winner_id": "player_id"})
        )

        player_side = all_matches_df[["player_id", "winner_id"]].copy()

        opponent_side = all_matches_df[["opponent_id", "winner_id"]].copy()
        opponent_side = opponent_side.rename(columns={"opponent_id": "player_id"})

        participant_rows = pd.concat(
            [player_side, opponent_side],
            ignore_index=True,
        )

        losses_df = (
            participant_rows[
                participant_rows["player_id"] != participant_rows["winner_id"]
            ]
            .groupby("player_id")
            .size()
            .reset_index(name="losses")
        )
    else:
        wins_df = pd.DataFrame(columns=["player_id", "wins"])
        losses_df = pd.DataFrame(columns=["player_id", "losses"])

    # Round wins / losses
    if not round_matches_df.empty:
        round_wins_df = (
            round_matches_df.groupby("winner_id")
            .size()
            .reset_index(name="round_wins")
            .rename(columns={"winner_id": "player_id"})
        )

        round_player_side = round_matches_df[["player_id", "winner_id"]].copy()

        round_opponent_side = round_matches_df[["opponent_id", "winner_id"]].copy()
        round_opponent_side = round_opponent_side.rename(
            columns={"opponent_id": "player_id"}
        )

        round_participant_rows = pd.concat(
            [round_player_side, round_opponent_side],
            ignore_index=True,
        )

        round_losses_df = (
            round_participant_rows[
                round_participant_rows["player_id"] != round_participant_rows["winner_id"]
            ]
            .groupby("player_id")
            .size()
            .reset_index(name="round_losses")
        )
    else:
        round_wins_df = pd.DataFrame(columns=["player_id", "round_wins"])
        round_losses_df = pd.DataFrame(columns=["player_id", "round_losses"])

    player_base = player_base.merge(wins_df, on="player_id", how="left")
    player_base = player_base.merge(losses_df, on="player_id", how="left")
    player_base = player_base.merge(round_wins_df, on="player_id", how="left")
    player_base = player_base.merge(round_losses_df, on="player_id", how="left")

    player_base["wins"] = player_base["wins"].fillna(0).astype(int)
    player_base["losses"] = player_base["losses"].fillna(0).astype(int)
    player_base["round_wins"] = player_base["round_wins"].fillna(0).astype(int)
    player_base["round_losses"] = player_base["round_losses"].fillna(0).astype(int)
    player_base["elo"] = pd.to_numeric(player_base["elo"], errors="coerce").fillna(1500.0)

    return player_base


def compute_live_ranking(stats_df: pd.DataFrame) -> pd.DataFrame:
    if stats_df.empty:
        return stats_df.copy()

    ranked = stats_df.sort_values(
        ["elo", "player_name"],
        ascending=[False, True],
    ).reset_index(drop=True)

    ranked["rank"] = range(1, len(ranked) + 1)
    ranked["box"] = ((ranked["rank"] - 1) // BOX_SIZE) + 1

    return ranked


def load_display_ladder(year: int, round_number: int) -> tuple[pd.DataFrame, bool]:
    """
    Returns:
        df: ladder to display
        is_snapshot: True if using frozen snapshot, False if using live ranking
    """
    stats_df = build_player_stats(year, round_number)
    if stats_df.empty:
        return stats_df, False

    snapshot_rows = get_ladder_snapshot(year, round_number)
    snapshot_df = pd.DataFrame(snapshot_rows) if snapshot_rows else pd.DataFrame()

    if snapshot_df.empty:
        live_df = compute_live_ranking(stats_df)
        return live_df, False

    display_df = snapshot_df.merge(
        stats_df[["player_id", "player_name", "wins", "losses", "round_wins", "round_losses", "elo"]],
        on="player_id",
        how="left",
        suffixes=("_snapshot", ""),
    )

    # keep frozen order, but display current stats
    display_df = display_df.sort_values("rank").reset_index(drop=True)
    display_df["box"] = display_df["box"].astype(int)
    display_df["rank"] = display_df["rank"].astype(int)
    display_df["wins"] = display_df["wins"].fillna(0).astype(int)
    display_df["losses"] = display_df["losses"].fillna(0).astype(int)
    display_df["round_wins"] = display_df["round_wins"].fillna(0).astype(int)
    display_df["round_losses"] = display_df["round_losses"].fillna(0).astype(int)
    display_df["elo"] = pd.to_numeric(display_df["elo"], errors="coerce").fillna(1500.0)

    return display_df, True


def save_snapshot(year: int, round_number: int, ranked_df: pd.DataFrame):
    if ranked_df.empty:
        return

    existing_snapshot = get_ladder_snapshot(year, round_number)
    if existing_snapshot:
        raise ValueError(f"Snapshot already exists for round {round_number} in {year}.")

    rows = []
    for _, row in ranked_df.iterrows():
        rows.append(
            {
                "year": year,
                "round": round_number,
                "player_id": row["player_id"],
                "rank": int(row["rank"]),
                "box": int(row["box"]),
                "elo": float(row["elo"]),
                "wins": int(row["wins"]),
                "losses": int(row["losses"]),
            }
        )

    insert_ladder_snapshot(rows)


def begin_new_round(year: int, closed_round_number: int):
    """
    Create the next round snapshot from current live Elo order.
    Example:
      closed_round_number = 7
      writes snapshot for round 8
    """
    next_round = closed_round_number + 1

    next_round_existing = get_ladder_snapshot(year, next_round)
    if next_round_existing:
        raise ValueError(f"Round {next_round} already has a snapshot.")

    final_stats_df = build_player_stats(year, closed_round_number)
    if final_stats_df.empty:
        raise ValueError("No active players found. Cannot begin a new round.")

    next_round_rank_df = compute_live_ranking(final_stats_df)
    save_snapshot(year, next_round, next_round_rank_df)


def get_player_round_matches(year: int, round_number: int, player_id) -> pd.DataFrame:
    round_matches = get_matches_for_year_and_round(year, round_number)
    round_matches_df = pd.DataFrame(round_matches) if round_matches else pd.DataFrame()

    if round_matches_df.empty:
        return pd.DataFrame(
            columns=["match_date", "opponent_name", "result", "score"]
        )

    player_matches = round_matches_df[
        (round_matches_df["player_id"] == player_id)
        | (round_matches_df["opponent_id"] == player_id)
    ].copy()

    if player_matches.empty:
        return pd.DataFrame(
            columns=["match_date", "opponent_name", "result", "score"]
        )

    all_players = get_players()
    players_df = pd.DataFrame(all_players) if all_players else pd.DataFrame()
    name_map = {}
    if (
        not players_df.empty
        and "player_id" in players_df.columns
        and "name" in players_df.columns
    ):
        name_map = dict(zip(players_df["player_id"], players_df["name"]))

    def opponent_for_row(row):
        return row["opponent_id"] if row["player_id"] == player_id else row["player_id"]

    def result_for_row(row):
        if row["winner_id"] == player_id:
            return "W"
        if pd.isna(row["winner_id"]):
            return "-"
        return "L"

    def score_for_match(row):
        sets = get_sets(row["match_id"])
        sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

        if sets_df.empty:
            return ""

        sets_df["set_number"] = pd.to_numeric(sets_df["set_number"], errors="coerce")
        sets_df["player_games"] = pd.to_numeric(sets_df["player_games"], errors="coerce")
        sets_df["opponent_games"] = pd.to_numeric(sets_df["opponent_games"], errors="coerce")
        sets_df = sets_df.dropna(subset=["set_number", "player_games", "opponent_games"])
        sets_df = sets_df.sort_values("set_number")

        score_parts = []

        for _, set_row in sets_df.iterrows():
            if row["player_id"] == player_id:
                my_games = int(set_row["player_games"])
                opp_games = int(set_row["opponent_games"])
            else:
                my_games = int(set_row["opponent_games"])
                opp_games = int(set_row["player_games"])

            score_parts.append(f"{my_games}-{opp_games}")

        return ", ".join(score_parts)

    player_matches["match_date"] = pd.to_datetime(
        player_matches["match_date"], errors="coerce"
    )
    player_matches["opponent_id_display"] = player_matches.apply(opponent_for_row, axis=1)
    player_matches["opponent_name"] = player_matches["opponent_id_display"].map(name_map)
    player_matches["opponent_name"] = player_matches["opponent_name"].fillna(
        player_matches["opponent_id_display"].astype(str)
    )
    player_matches["result"] = player_matches.apply(result_for_row, axis=1)
    player_matches["score"] = player_matches.apply(score_for_match, axis=1)

    player_matches = player_matches.sort_values(["match_date", "match_id"]).copy()

    return player_matches[["match_date", "opponent_name", "result", "score"]]


# ---------------------------------------------------
# Load matches for selector building
# ---------------------------------------------------

DEFAULT_YEAR, DEFAULT_ROUND = get_default_year_and_round()

matches_df = pd.DataFrame(get_matches()) if get_matches() else pd.DataFrame()

if not matches_df.empty:
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")
    matches_df = matches_df.dropna(subset=["match_date", "round"])
    matches_df["year"] = matches_df["match_date"].dt.year
    matches_df["round"] = pd.to_numeric(matches_df["round"], errors="coerce")
    matches_df = matches_df.dropna(subset=["round"])
    matches_df["round"] = matches_df["round"].astype(int)

year_options = get_year_options(matches_df, DEFAULT_YEAR)

if "selected_year" not in st.session_state:
    st.session_state["selected_year"] = DEFAULT_YEAR

if "selected_round" not in st.session_state:
    st.session_state["selected_round"] = DEFAULT_ROUND

if st.session_state["selected_year"] not in year_options:
    st.session_state["selected_year"] = DEFAULT_YEAR

round_options = get_round_options_for_year(
    matches_df=matches_df,
    selected_year=st.session_state["selected_year"],
    default_round=DEFAULT_ROUND,
)

if st.session_state["selected_round"] not in round_options:
    st.session_state["selected_round"] = DEFAULT_ROUND


# ---------------------------------------------------
# Selectors
# ---------------------------------------------------

col1, col2 = st.columns([1, 1])

with col1:
    selected_year = st.selectbox(
        "Year",
        options=year_options,
        key="selected_year",
    )

round_options = get_round_options_for_year(
    matches_df=matches_df,
    selected_year=selected_year,
    default_round=DEFAULT_ROUND if selected_year == DEFAULT_YEAR else 1,
)

if st.session_state["selected_round"] not in round_options:
    st.session_state["selected_round"] = round_options[-1]

with col2:
    selected_round = st.selectbox(
        "Round",
        options=round_options,
        key="selected_round",
    )


# ---------------------------------------------------
# Main ladder data
# ---------------------------------------------------

stats_df = build_player_stats(selected_year, selected_round)

if stats_df.empty:
    st.info("No active players found.")
    st.stop()

display_df, using_snapshot = load_display_ladder(selected_year, selected_round)

status_text = "Frozen round order" if using_snapshot else "Live ladder preview"
st.caption(status_text)


# ---------------------------------------------------
# Admin controls
# ---------------------------------------------------

with st.expander("Admin: Round Controls"):
    password_input = st.text_input("Password", type="password")

    admin_col1, admin_col2 = st.columns(2)

    with admin_col1:
        if st.button("End Round", type="primary"):
            admin_password = st.secrets.get("ADMIN_PASSWORD")

            if not admin_password:
                st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
            elif password_input != admin_password:
                st.error("Incorrect password.")
            else:
                final_rank_df = compute_live_ranking(stats_df)
                save_snapshot(selected_year, selected_round, final_rank_df)
                st.success(f"Round {selected_round} for {selected_year} has been closed.")
                st.rerun()

    with admin_col2:
        if st.button("Begin New Round"):
            admin_password = st.secrets.get("ADMIN_PASSWORD")

            if not admin_password:
                st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
            elif password_input != admin_password:
                st.error("Incorrect password.")
            else:
                try:
                    # Optional guard: require current round snapshot to exist first
                    existing_current_snapshot = get_ladder_snapshot(selected_year, selected_round)
                    if not existing_current_snapshot:
                        st.error(
                            f"Please close round {selected_round} first before beginning round {selected_round + 1}."
                        )
                    else:
                        begin_new_round(selected_year, selected_round)
                        st.session_state["selected_year"] = selected_year
                        st.session_state["selected_round"] = selected_round + 1
                        st.success(f"Round {selected_round + 1} has started.")
                        st.rerun()
                except Exception as e:
                    st.error(str(e))


# ---------------------------------------------------
# Render ladder
# ---------------------------------------------------

st.subheader(f"{selected_year} Ladder — Round {selected_round}")
st.caption("Select a player row to view their matches for this round.")

st.markdown(
    """
    <style>
    div[data-testid="stDataFrame"] {
        border: 1px solid rgba(128,128,128,0.18);
        border-radius: 12px;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

display_table = display_df.copy()

display_table["wins"] = display_table["wins"].fillna(0).astype(int)
display_table["losses"] = display_table["losses"].fillna(0).astype(int)
display_table["round_wins"] = display_table["round_wins"].fillna(0).astype(int)
display_table["round_losses"] = display_table["round_losses"].fillna(0).astype(int)
display_table["elo"] = pd.to_numeric(display_table["elo"], errors="coerce").fillna(1500.0)

display_table["Round Record"] = (
    display_table["round_wins"].astype(str)
    + "-"
    + display_table["round_losses"].astype(str)
)
display_table["Record"] = (
    display_table["wins"].astype(str)
    + "-"
    + display_table["losses"].astype(str)
)
display_table["Elo"] = display_table["elo"].round(1)

display_table = display_table.rename(
    columns={
        "box": "Box",
        "rank": "Rank",
        "player_name": "Player",
    }
)

display_table = display_table[
    ["player_id", "Box", "Rank", "Player", "Round Record", "Record", "Elo"]
].sort_values(["Box", "Rank"], ascending=[True, True]).reset_index(drop=True)

# spacer rows between boxes
table_rows = []
for idx, row in display_table.iterrows():
    if idx > 0:
        prev_box = int(display_table.iloc[idx - 1]["Box"])
        curr_box = int(row["Box"])
        if curr_box != prev_box:
            table_rows.append(
                {
                    "player_id": None,
                    "Box": "",
                    "Rank": "",
                    "Player": "",
                    "Round Record": "",
                    "Record": "",
                    "Elo": None,
                }
            )

    table_rows.append(row.to_dict())

interactive_table = pd.DataFrame(table_rows)

event = st.dataframe(
    interactive_table[["Box", "Rank", "Player", "Round Record", "Record", "Elo"]],
    use_container_width=True,
    hide_index=True,
    on_select="rerun",
    selection_mode="single-row",
    key="ladder_table",
    column_config={
        "Box": st.column_config.TextColumn("Box", width="small"),
        "Rank": st.column_config.TextColumn("Rank", width="small"),
        "Player": st.column_config.TextColumn("Player", width="large"),
        "Round Record": st.column_config.TextColumn("Round Record", width="small"),
        "Record": st.column_config.TextColumn("Record", width="small"),
        "Elo": st.column_config.NumberColumn("Elo", format="%.1f", width="small"),
    },
)

selected_rows = event.selection.rows if event and event.selection else []

if selected_rows:
    selected_idx = selected_rows[0]
    selected_row = interactive_table.iloc[selected_idx]

    if pd.notna(selected_row["player_id"]):
        selected_player_id = selected_row["player_id"]
        selected_player_name = selected_row["Player"]

        st.markdown(f"### {selected_player_name} — Round {selected_round} Matches")

        player_round_matches_df = get_player_round_matches(
            selected_year,
            selected_round,
            selected_player_id,
        )

        if player_round_matches_df.empty:
            st.caption("No matches found for this player in the selected round.")
        else:
            player_round_matches_df = player_round_matches_df.copy()
            player_round_matches_df["match_date"] = pd.to_datetime(
                player_round_matches_df["match_date"], errors="coerce"
            )
            player_round_matches_df["Date"] = player_round_matches_df["match_date"].dt.strftime(
                "%Y-%m-%d"
            )
            player_round_matches_df = player_round_matches_df.rename(
                columns={
                    "opponent_name": "Opponent",
                    "result": "Result",
                    "score": "Score",
                }
            )

            st.dataframe(
                player_round_matches_df[["Date", "Opponent", "Result", "Score"]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Opponent": st.column_config.TextColumn("Opponent", width="large"),
                    "Result": st.column_config.TextColumn("Result", width="small"),
                    "Score": st.column_config.TextColumn("Score", width="medium"),
                },
            )