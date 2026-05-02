import streamlit as st
import pandas as pd
import altair as alt

from db import (
    get_active_players,
    get_players,
    get_matches_for_year,
    get_sets,
)
from utils.elo import get_elo_time_series

st.set_page_config(page_title="Player Details", layout="wide")
st.title("Player Details")

SEASON_START_DATES = {
    2025: "2025-04-01",
    2026: "2026-04-01",
}


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def get_season_start_date(year: int) -> str | None:
    return SEASON_START_DATES.get(year)


def get_active_player_lookup() -> pd.DataFrame:
    active_players = get_active_players()
    active_df = pd.DataFrame(active_players) if active_players else pd.DataFrame()

    if active_df.empty:
        return pd.DataFrame(columns=["player_id", "player_name"])

    if "player_id" not in active_df.columns or "name" not in active_df.columns:
        return pd.DataFrame(columns=["player_id", "player_name"])

    active_df = active_df[["player_id", "name"]].copy()
    active_df = active_df.rename(columns={"name": "player_name"})
    active_df = active_df.sort_values("player_name").reset_index(drop=True)
    return active_df


def get_player_season_match_history(year: int, player_id) -> pd.DataFrame:
    """
    Season-long completed match history for one player, including:
    - date
    - opponent
    - result
    - score
    - Elo after match
    - Elo change from match
    """
    season_start_date = get_season_start_date(year)

    elo_history_df = get_elo_time_series(
        year=year,
        season_start_date=season_start_date,
    )

    if elo_history_df is None or elo_history_df.empty:
        return pd.DataFrame(
            columns=[
                "match_id",
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    elo_history_df = elo_history_df.copy()
    elo_history_df = elo_history_df[elo_history_df["player_id"] == player_id].copy()

    if elo_history_df.empty:
        return pd.DataFrame(
            columns=[
                "match_id",
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

    all_matches = get_matches_for_year(year)
    matches_df = pd.DataFrame(all_matches) if all_matches else pd.DataFrame()

    if matches_df.empty:
        return pd.DataFrame(
            columns=[
                "match_id",
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
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

    matches_df = matches_df.copy()
    matches_df["match_date"] = pd.to_datetime(matches_df["match_date"], errors="coerce")

    player_matches = matches_df[
        (matches_df["player_id"] == player_id) | (matches_df["opponent_id"] == player_id)
    ].copy()

    if player_matches.empty:
        return pd.DataFrame(
            columns=[
                "match_id",
                "match_date",
                "opponent_name",
                "result",
                "score",
                "elo",
                "elo_change",
            ]
        )

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

    player_matches["opponent_id_display"] = player_matches.apply(opponent_for_row, axis=1)
    player_matches["opponent_name"] = player_matches["opponent_id_display"].map(name_map)
    player_matches["opponent_name"] = player_matches["opponent_name"].fillna(
        player_matches["opponent_id_display"].astype(str)
    )
    player_matches["result"] = player_matches.apply(result_for_row, axis=1)
    player_matches["score"] = player_matches.apply(score_for_match, axis=1)

    player_matches = player_matches[
        ["match_id", "match_date", "opponent_name", "result", "score"]
    ].copy()

    history_df = elo_history_df.merge(
        player_matches,
        on="match_id",
        how="left",
    )

    history_df["match_date"] = pd.to_datetime(history_df["date"], errors="coerce")
    history_df["elo"] = pd.to_numeric(history_df["elo"], errors="coerce")
    history_df["elo_change"] = pd.to_numeric(history_df["elo_change"], errors="coerce")

    history_df = history_df.sort_values(["match_date", "match_id"]).reset_index(drop=True)

    return history_df[
        ["match_id", "match_date", "opponent_name", "result", "score", "elo", "elo_change"]
    ]


def _format_form(results: list[str], limit: int = 5) -> str:
    if not results:
        return "-"
    return " · ".join(results[:limit])


def _longest_streak(results: list[str], target: str) -> int:
    longest = 0
    current = 0
    for r in results:
        if r == target:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def build_player_story_stats(history_df: pd.DataFrame) -> dict:
    if history_df.empty:
        return {
            "current_elo": 1500.0,
            "peak_elo": 1500.0,
            "low_elo": 1500.0,
            "net_elo_change": 0.0,
            "wins": 0,
            "losses": 0,
            "matches": 0,
            "win_pct": 0.0,
            "form": "-",
            "biggest_gain": 0.0,
            "biggest_drop": 0.0,
            "avg_change": 0.0,
            "longest_win_streak": 0,
            "longest_loss_streak": 0,
        }

    hist = history_df.copy()
    hist["elo"] = pd.to_numeric(hist["elo"], errors="coerce")
    hist["elo_change"] = pd.to_numeric(hist["elo_change"], errors="coerce")
    hist = hist.sort_values(["match_date", "match_id"]).reset_index(drop=True)

    results = hist["result"].fillna("-").tolist()
    wins = int((hist["result"] == "W").sum())
    losses = int((hist["result"] == "L").sum())
    matches = wins + losses

    current_elo = float(hist["elo"].dropna().iloc[-1]) if hist["elo"].notna().any() else 1500.0
    peak_elo = float(hist["elo"].dropna().max()) if hist["elo"].notna().any() else 1500.0
    low_elo = float(hist["elo"].dropna().min()) if hist["elo"].notna().any() else 1500.0
    biggest_gain = float(hist["elo_change"].dropna().max()) if hist["elo_change"].notna().any() else 0.0
    biggest_drop = float(hist["elo_change"].dropna().min()) if hist["elo_change"].notna().any() else 0.0
    net_elo_change = float(hist["elo_change"].dropna().sum()) if hist["elo_change"].notna().any() else 0.0
    avg_change = float(hist["elo_change"].dropna().mean()) if hist["elo_change"].notna().any() else 0.0
    win_pct = (wins / matches) if matches > 0 else 0.0

    recent_results = hist["result"].fillna("-").tolist()[::-1]
    form = _format_form(recent_results, limit=5)

    return {
        "current_elo": current_elo,
        "peak_elo": peak_elo,
        "low_elo": low_elo,
        "net_elo_change": net_elo_change,
        "wins": wins,
        "losses": losses,
        "matches": matches,
        "win_pct": win_pct,
        "form": form,
        "biggest_gain": biggest_gain,
        "biggest_drop": biggest_drop,
        "avg_change": avg_change,
        "longest_win_streak": _longest_streak(results, "W"),
        "longest_loss_streak": _longest_streak(results, "L"),
    }


def build_waterfall_chart(history_df: pd.DataFrame) -> alt.Chart:
    wf = history_df.copy()
    wf["match_date"] = pd.to_datetime(wf["match_date"], errors="coerce")
    wf["elo"] = pd.to_numeric(wf["elo"], errors="coerce")
    wf["elo_change"] = pd.to_numeric(wf["elo_change"], errors="coerce")
    wf = wf.dropna(subset=["match_date", "elo", "elo_change"]).copy()
    wf = wf.sort_values(["match_date", "match_id"]).reset_index(drop=True)

    if wf.empty:
        return alt.Chart(pd.DataFrame({"x": [], "y": []})).mark_bar()

    wf["match_number"] = range(1, len(wf) + 1)
    wf["elo_before"] = wf["elo"] - wf["elo_change"]
    wf["start"] = wf[["elo_before", "elo"]].min(axis=1)
    wf["end"] = wf[["elo_before", "elo"]].max(axis=1)
    wf["delta_sign"] = wf["elo_change"].apply(lambda x: "Gain" if x >= 0 else "Loss")
    wf["label"] = wf["match_date"].dt.strftime("%m/%d").fillna("Unknown")

    bars = alt.Chart(wf).mark_bar(size=16, cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X(
            "label:N",
            sort=list(wf["label"]),
            axis=alt.Axis(
                title=None,
                labelAngle=-25,
                labelLimit=120,
                labelFontSize=10,
            ),
        ),
        y=alt.Y(
            "start:Q",
            title="Elo",
            scale=alt.Scale(
                zero=False,
                nice=False,
                domain=[
                    max(1200, float(wf["start"].min()) - 15),
                    min(1800, float(wf["end"].max()) + 15),
                ],
            ),
        ),
        y2="end:Q",
        color=alt.Color(
            "delta_sign:N",
            scale=alt.Scale(domain=["Gain", "Loss"], range=["#2E8B57", "#C0392B"]),
            legend=None,
        ),
        tooltip=[
            alt.Tooltip("match_date:T", title="Date"),
            alt.Tooltip("opponent_name:N", title="Opponent"),
            alt.Tooltip("result:N", title="Result"),
            alt.Tooltip("score:N", title="Score"),
            alt.Tooltip("elo_before:Q", title="Elo Before", format=".1f"),
            alt.Tooltip("elo_change:Q", title="Elo +/-", format="+.1f"),
            alt.Tooltip("elo:Q", title="Elo After", format=".1f"),
        ],
    )

    connectors_df = wf.iloc[:-1].copy()
    connectors_df["next_label"] = wf["label"].shift(-1).iloc[:-1].values
    connectors_df["connector_y"] = connectors_df["elo"]

    connectors = alt.Chart(connectors_df).mark_rule(color="#B0B0B0", strokeDash=[4, 4]).encode(
        x=alt.X("label:N", sort=list(wf["label"])),
        x2=alt.X2("next_label:N"),
        y="connector_y:Q",
        tooltip=[
            alt.Tooltip("elo:Q", title="Elo After Match", format=".1f")
        ],
    )

    text = alt.Chart(wf).mark_text(
        fontSize=11,
        fontWeight="bold",
        color="white",
    ).encode(
        x=alt.X("label:N", sort=list(wf["label"])),
        y=alt.Y("start:Q"),
        y2="end:Q",
        text=alt.Text("elo_change:Q", format="+.1f"),
    )

    chart = (connectors + bars + text).properties(
        height=300
    )

    return chart.interactive()


def render_story_cards(history_df: pd.DataFrame) -> None:
    story = build_player_story_stats(history_df)

    row1 = st.columns(4)
    row2 = st.columns(4)
    row3 = st.columns(4)

    with row1[0]:
        st.metric(
            "Current Elo",
            f"{story['current_elo']:.1f}",
            delta=f"{story['net_elo_change']:+.1f} season",
        )

    with row1[1]:
        st.metric(
            "Record",
            f"{story['wins']}-{story['losses']}",
            delta=f"{story['win_pct']:.0%} win rate",
        )

    with row1[2]:
        st.metric(
            "Peak Elo",
            f"{story['peak_elo']:.1f}",
            delta=f"{story['peak_elo'] - story['current_elo']:+.1f} vs now",
        )

    with row1[3]:
        st.metric(
            "Current Form",
            story["form"],
            delta=f"{story['matches']} completed matches",
        )

    with row2[0]:
        st.metric(
            "Biggest Gain",
            f"{story['biggest_gain']:+.1f}",
        )

    with row2[1]:
        st.metric(
            "Biggest Drop",
            f"{story['biggest_drop']:+.1f}",
        )

    with row2[2]:
        st.metric(
            "Avg Elo Change",
            f"{story['avg_change']:+.1f}",
            delta="per completed match",
        )

    with row2[3]:
        st.metric(
            "Lowest Elo",
            f"{story['low_elo']:.1f}",
            delta=f"{story['current_elo'] - story['low_elo']:+.1f} above low",
        )

    with row3[0]:
        st.metric(
            "Longest Win Streak",
            str(story["longest_win_streak"]),
        )

    with row3[1]:
        st.metric(
            "Longest Loss Streak",
            str(story["longest_loss_streak"]),
        )

    with row3[2]:
        recent = history_df.sort_values(["match_date", "match_id"], ascending=[False, False]).head(3)
        recent_delta = pd.to_numeric(recent["elo_change"], errors="coerce").sum() if not recent.empty else 0.0
        st.metric(
            "Last 3 Match Elo",
            f"{recent_delta:+.1f}",
        )

    with row3[3]:
        positive = int((pd.to_numeric(history_df["elo_change"], errors="coerce") > 0).sum())
        negative = int((pd.to_numeric(history_df["elo_change"], errors="coerce") < 0).sum())
        st.metric(
            "Positive / Negative",
            f"{positive} / {negative}",
        )


def render_player_details(year: int, player_id, player_name: str) -> None:
    st.subheader(player_name)

    season_history_df = get_player_season_match_history(year, player_id)

    if season_history_df.empty:
        st.caption("No completed match history found for this player in the selected year.")
        return

    render_story_cards(season_history_df)

    st.markdown("#### Elo Waterfall")
    waterfall_chart = build_waterfall_chart(season_history_df)
    st.altair_chart(waterfall_chart, use_container_width=True)

    st.markdown("#### Season Match History")

    display_history = season_history_df.copy()
    display_history["match_date"] = pd.to_datetime(display_history["match_date"], errors="coerce")
    display_history["elo"] = pd.to_numeric(display_history["elo"], errors="coerce")
    display_history["elo_change"] = pd.to_numeric(display_history["elo_change"], errors="coerce")

    display_history = display_history.sort_values(
        ["match_date", "match_id"],
        ascending=[False, False],
    ).reset_index(drop=True)

    display_history["Date"] = display_history["match_date"].dt.strftime("%Y-%m-%d")
    display_history["Elo After"] = display_history["elo"].round(1)
    display_history["Elo +/-"] = display_history["elo_change"].round(1)

    st.dataframe(
        display_history[
            ["Date", "opponent_name", "result", "score", "Elo +/-", "Elo After"]
        ].rename(
            columns={
                "opponent_name": "Opponent",
                "result": "Result",
                "score": "Score",
            }
        ),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Date": st.column_config.TextColumn("Date", width="small"),
            "Opponent": st.column_config.TextColumn("Opponent", width="large"),
            "Result": st.column_config.TextColumn("Result", width="small"),
            "Score": st.column_config.TextColumn("Score", width="medium"),
            "Elo +/-": st.column_config.NumberColumn("Elo +/-", format="%.1f", width="small"),
            "Elo After": st.column_config.NumberColumn("Elo After", format="%.1f", width="small"),
        },
    )


# ---------------------------------------------------
# Page controls
# ---------------------------------------------------

top_col1, top_col2 = st.columns([1, 2])

with top_col1:
    selected_year = st.selectbox(
        "Year",
        options=[2026, 2025],
        index=0,
    )

players_list = get_players()
player_lookup_df = pd.DataFrame(players_list)



if player_lookup_df.empty:
    st.info("No active players found.")
    st.stop()

player_options = player_lookup_df["name"].tolist()

with top_col2:
    selected_player_name = st.selectbox(
        "Player",
        options=player_options,
        index=0 if player_options else None,
    )

selected_player_row = player_lookup_df[
    player_lookup_df["name"] == selected_player_name
].iloc[0]

selected_player_id = selected_player_row["player_id"]

render_player_details(
    year=selected_year,
    player_id=selected_player_id,
    player_name=selected_player_name,
)