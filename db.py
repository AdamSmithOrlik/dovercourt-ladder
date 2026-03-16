import streamlit as st
from supabase import create_client, Client


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


def update_player_active_status(email: str, active: bool):
    supabase = get_supabase()
    response = (
        supabase.table("players")
        .update({"active": active})
        .eq("email", email)
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
