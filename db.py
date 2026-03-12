import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def get_players():
    supabase = get_supabase()
    response = supabase.table("players").select("*").order("id").execute()
    return response.data


def get_player_by_email(email: str):
    supabase = get_supabase()
    response = supabase.table("players").select("*").eq("email", email).execute()
    return response.data


def insert_player(player_data: dict):
    supabase = get_supabase()
    response = supabase.table("players").insert(player_data).execute()
    return response.data


def insert_match(match_data: dict):
    supabase = get_supabase()
    response = supabase.table("matches").insert(match_data).execute()
    return response.data


def get_matches():
    supabase = get_supabase()
    response = (
        supabase.table("matches").select("*").order("match_date", desc=True).execute()
    )
    return response.data


def get_player_by_email_ex(email: str):
    supabase = get_supabase()
    response = supabase.table("players").select("*").eq("email", email).execute()
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
