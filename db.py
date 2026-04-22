import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_players():
    supabase = get_supabase()
    response = supabase.table("players").select("*").order("name").execute()
    return response.data


def get_player_by_email(email: str):
    supabase = get_supabase()
    response = supabase.table("players").select("*").eq("email", email).execute()
    return response.data


def insert_player(player_data: dict):
    supabase = get_supabase()
    response = supabase.table("players").insert(player_data).execute()
    return response.data

def get_current_player_statuses():
    supabase = get_supabase()

    response = (
        supabase.table("current_player_status")
        .select("*")
        .order("name")
        .execute()
    )

    return response.data

def update_player_active_status(
    email: str,
    active: bool,
    effective_date: str | None = None,
    end_date: str | None = None,
):
    supabase = get_supabase()

    player_resp = (
        supabase.table("players")
        .select("player_id")
        .eq("email", email)
        .single()
        .execute()
    )

    player_id = player_resp.data["player_id"]

    response = (
        supabase.table("player_status_changes")
        .insert({
            "player_id": player_id,
            "active": active,
            "effective_date": effective_date or date.today().isoformat(),
            "end_date": end_date,
        })
        .execute()
    )
    return response.data

def get_active_players():
    supabase = get_supabase()
    response = (
        supabase.table("current_player_status")
        .select("*")
        .eq("active", True)
        .order("name")
        .execute()
    )
    return response.data

def insert_match(match_data: dict):
    supabase = get_supabase()
    response = supabase.table("matches").insert(match_data).execute()
    return response.data[0]


def get_matches():
    supabase = get_supabase()
    response = (
        supabase.table("matches").select("*").order("match_date", desc=True).execute()
    )
    return response.data


def get_completed_matches_for_year(year: int = 2025):
    """Return completed matches for a calendar year sorted by date then match_id."""
    supabase = get_supabase()

    start_date = f"{year}-01-01"
    end_date = f"{year + 1}-01-01"

    response = (
        supabase.table("matches")
        .select("*")
        .gte("match_date", start_date)
        .lt("match_date", end_date)
        .order("match_date")
        .order("match_id")
        .execute()
    )

    completed_matches = []

    for match in response.data:
        if not match.get("match_id"):
            continue
        if not match.get("player_id"):
            continue
        if not match.get("opponent_id"):
            continue
        if not match.get("winner_id"):
            continue
        completed_matches.append(match)

    return completed_matches


def get_sets_for_match_ids(match_ids: list):
    """Return all sets for the given match IDs sorted by match_id and set_number."""
    if not match_ids:
        return []

    unique_match_ids = list(dict.fromkeys(match_ids))

    supabase = get_supabase()
    response = (
        supabase.table("sets")
        .select("*")
        .in_("match_id", unique_match_ids)
        .order("match_id")
        .order("set_number")
        .execute()
    )
    return response.data


def get_players_by_ids(player_ids: list):
    """Return player rows for the given player IDs sorted by name."""
    if not player_ids:
        return []

    unique_player_ids = list(dict.fromkeys(player_ids))

    supabase = get_supabase()
    response = (
        supabase.table("players")
        .select("*")
        .in_("player_id", unique_player_ids)
        .order("name")
        .execute()
    )
    return response.data


def get_sets(match_id: str):
    supabase = get_supabase()
    response = (
        supabase.table("sets")
        .select("*")
        .eq("match_id", match_id)
        .order("set_number")
        .execute()
    )
    return response.data


def get_all_sets():
    supabase = get_supabase()
    response = (
        supabase.table("sets")
        .select("*")
        .order("match_id")
        .order("set_number")
        .execute()
    )
    return response.data


def insert_sets(sets_data: list):
    supabase = get_supabase()
    response = supabase.table("sets").insert(sets_data).execute()
    return response.data


def update_match(match_id: str, match_data: dict):
    supabase = get_supabase()
    response = (
        supabase.table("matches").update(match_data).eq("match_id", match_id).execute()
    )
    return response.data


def update_set(set_id: str, set_data: dict):
    supabase = get_supabase()
    response = supabase.table("sets").update(set_data).eq("set_id", set_id).execute()
    return response.data

def get_matches_for_year(year: int):
    supabase = get_supabase()
    start_date = f"{year}-01-01"
    end_date = f"{year + 1}-01-01"

    response = (
        supabase.table("matches")
        .select("*")
        .gte("match_date", start_date)
        .lt("match_date", end_date)
        .order("match_date")
        .order("match_id")
        .execute()
    )
    return response.data


def get_matches_for_year_and_round(year: int, round_number: int):
    supabase = get_supabase()
    start_date = f"{year}-01-01"
    end_date = f"{year + 1}-01-01"

    response = (
        supabase.table("matches")
        .select("*")
        .gte("match_date", start_date)
        .lt("match_date", end_date)
        .eq("round", round_number)
        .order("match_date")
        .order("match_id")
        .execute()
    )
    return response.data

def get_latest_match_year_and_round():
    """
    Returns:
        tuple[int | None, int | None]
        (latest_year, latest_round)
    """
    supabase = get_supabase()

    response = (
        supabase.table("matches")
        .select("match_date, round")
        .order("match_date", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None, None

    latest_match = response.data[0]

    match_date = latest_match.get("match_date")
    round_value = latest_match.get("round")

    if not match_date:
        return None, None

    latest_year = pd.to_datetime(match_date).year

    try:
        latest_round = int(round_value) if round_value is not None else None
    except Exception:
        latest_round = None

    return latest_year, latest_round

def add_initial_player_status_for_next_round(email: str):
    supabase = get_supabase()

    clean_email = email.strip().lower()

    player_resp = (
        supabase.table("players")
        .select("player_id")
        .eq("email", clean_email)
        .single()
        .execute()
    )

    if not player_resp.data:
        raise ValueError(f"No player found for email: {clean_email}")

    player_id = player_resp.data["player_id"]

    today = date.today()

    next_round = next(
        (r for r in ROUND_WINDOWS_2026 if r["start_date"] > today),
        None
    )

    if next_round is None:
        raise ValueError("No upcoming round start date found.")

    status_resp = (
        supabase.table("player_status_changes")
        .insert({
            "player_id": player_id,
            "active": True,
            "effective_date": next_round["start_date"].isoformat(),
            "end_date": None,
        })
        .execute()
    )

    return status_resp.data

def get_upcoming_player_status_changes():
    supabase = get_supabase()
    today = date.today().isoformat()

    response = (
        supabase.table("player_status_changes")
        .select("""
            id,
            player_id,
            active,
            effective_date,
            end_date,
            created_at,
            players (
                name,
                email
            )
        """)
        .gt("effective_date", today)
        .order("effective_date")
        .execute()
    )

    data = response.data or []

    formatted = []
    for row in data:
        player = row.get("players") or {}

        formatted.append({
            "player_id": row["player_id"],
            "name": player.get("name"),
            "email": player.get("email"),
            "active": row["active"],
            "effective_date": row["effective_date"],
            "end_date": row["end_date"],
            "created_at": row["created_at"],
        })

    return formatted