import streamlit as st
import altair as alt
import pandas as pd

from utils.elo import (
    DEFAULT_INITIAL_RATING,
    build_elo_data_for_year,
)

SEASON_START_DATE_2025 = "2025-05-01"

st.set_page_config(page_title="Ladder", layout="wide")

st.title("🏆 Ladder")

st.info("The ladder rankings page is currently under construction.")

st.markdown(
    """
### Planned features

- Ladder standings
- Player movement tracking
- Match difficulty weighting
- ELO
"""
)

st.divider()

st.caption("Coming soon.")


@st.cache_data
def load_elo_test_data():
    return build_elo_data_for_year(
        year=2025,
        season_start_date=SEASON_START_DATE_2025,
    )


st.subheader("2025 Ladder Elo")

elo_time_series_df, elo_standings_df = load_elo_test_data()

if elo_standings_df.empty:
    st.info("No completed 2025 match data available for Elo testing yet.")
else:
    records_df = elo_time_series_df.groupby(
        ["player_id", "player_name"], as_index=False
    ).agg(
        wins=("elo_change", lambda s: int((s > 0).sum())),
        losses=("elo_change", lambda s: int((s < 0).sum())),
        matches=("elo_change", "size"),
    )
    records_df["Record"] = (
        records_df["wins"].astype(str) + "-" + records_df["losses"].astype(str)
    )

    player_options = elo_standings_df["player_name"].tolist()

    selected_player_name = st.selectbox(
        "Select player to inspect end-of-season Elo",
        options=player_options,
    )

    selected_row = elo_standings_df[
        elo_standings_df["player_name"] == selected_player_name
    ].iloc[0]

    selected_player_id = selected_row["player_id"]
    final_elo = float(selected_row["elo"])

    selected_record_row = records_df[records_df["player_id"] == selected_player_id]

    if not selected_record_row.empty:
        selected_record = selected_record_row.iloc[0]["Record"]
    else:
        selected_record = "0-0"

    player_history = elo_time_series_df[
        elo_time_series_df["player_id"] == selected_player_id
    ].sort_values(["date", "match_id"])

    matches_processed = int(len(player_history))
    elo_change_from_start = final_elo - float(DEFAULT_INITIAL_RATING)

    peak_elo = (
        float(player_history["elo"].max()) if not player_history.empty else final_elo
    )
    low_elo = (
        float(player_history["elo"].min()) if not player_history.empty else final_elo
    )

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Final 2025 Elo", f"{final_elo:.1f}")
    col2.metric("Change vs 1500", f"{elo_change_from_start:+.1f}")
    col3.metric("Matches Processed", matches_processed)
    col4.metric(
        "Current Rank",
        int(
            elo_standings_df.index[elo_standings_df["player_id"] == selected_player_id][
                0
            ]
        )
        + 1,
    )
    col5.metric("2025 Record", selected_record)

    col6, col7 = st.columns(2)
    col6.metric("Season Peak Elo", f"{peak_elo:.1f}")
    col7.metric("Season Low Elo", f"{low_elo:.1f}")

    st.markdown("Elo over time (all players)")

    chart_df = elo_time_series_df.copy().sort_values(["date", "match_id"])
    chart_df["date"] = pd.to_datetime(chart_df["date"])
    chart_df["elo"] = chart_df["elo"].round(2)

    first_match_date = chart_df["date"].min()
    last_match_date = chart_df["date"].max()

    final_points_df = (
        chart_df.sort_values(["date", "match_id"])
        .groupby("player_id", as_index=False)
        .tail(1)
    )

    base = alt.Chart(chart_df).encode(
        x=alt.X(
            "date:T",
            title="Date",
            scale=alt.Scale(domain=[first_match_date, last_match_date], nice=False),
        ),
        y=alt.Y("elo:Q", title="Elo"),
        color=alt.Color("player_name:N", title="Player"),
        tooltip=[
            alt.Tooltip("player_name:N", title="Player"),
            alt.Tooltip("date:T", title="Date"),
            alt.Tooltip("match_id:N", title="Match ID"),
            alt.Tooltip("elo:Q", title="Elo", format=".1f"),
            alt.Tooltip("elo_change:Q", title="Elo Change", format="+.2f"),
        ],
    )

    line_chart = base.mark_line(opacity=0.75)

    final_points_chart = (
        alt.Chart(final_points_df)
        .mark_circle(size=60)
        .encode(
            x=alt.X(
                "date:T",
                scale=alt.Scale(domain=[first_match_date, last_match_date], nice=False),
            ),
            y=alt.Y("elo:Q"),
            color=alt.Color("player_name:N", legend=None),
            tooltip=[
                alt.Tooltip("player_name:N", title="Player"),
                alt.Tooltip("elo:Q", title="Final Elo", format=".1f"),
                alt.Tooltip("date:T", title="Date"),
            ],
        )
    )

    chart = (line_chart + final_points_chart).properties(height=600).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.markdown("Latest 2025 Elo standings")
    standings_view = elo_standings_df.copy()
    standings_view = standings_view.merge(
        records_df[["player_id", "Record", "matches"]],
        on="player_id",
        how="left",
    )
    standings_view.index = standings_view.index + 1
    standings_view.index.name = "Rank"
    standings_view["elo"] = standings_view["elo"].round(1)
    standings_view["Record"] = standings_view["Record"].fillna("0-0")
    standings_view["matches"] = standings_view["matches"].fillna(0).astype(int)
    st.dataframe(
        standings_view[["player_name", "Record", "matches", "elo"]].rename(
            columns={"player_name": "Player", "matches": "Matches"}
        ),
        use_container_width=True,
    )
