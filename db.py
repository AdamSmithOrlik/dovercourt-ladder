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
        supabase.table("matches")
        .select("*")
        .order("match_date", desc=True)
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
        supabase.table("matches")
        .update(match_data)
        .eq("match_id", match_id)
        .execute()
    )
    return response.data


def update_set(set_id: str, set_data: dict):
    supabase = get_supabase()
    response = (
        supabase.table("sets")
        .update(set_data)
        .eq("set_id", set_id)
        .execute()
    )
    return response.data