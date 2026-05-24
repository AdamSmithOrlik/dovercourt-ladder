import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import date, timedelta
from utils.rounds import ROUND_WINDOWS_2026
import smtplib
from email.message import EmailMessage

@st.cache_resource
def get_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

def get_supabase_admin():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
    )

def get_players():
    supabase = get_supabase()
    response = supabase.table("players").select("*").order("name").execute()
    return response.data


def get_player_by_email(email: str):
    supabase = get_supabase()
    response = supabase.table("players").select("*").eq("email", email).execute()
    return response.data


def insert_player(player_data: dict):
    supabase = get_supabase_admin()
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
    supabase = get_supabase_admin()

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
    supabase = get_supabase_admin()
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
    supabase = get_supabase_admin()
    response = supabase.table("sets").insert(sets_data).execute()
    return response.data


def update_match(match_id: str, match_data: dict):
    supabase = get_supabase_admin()
    response = (
        supabase.table("matches").update(match_data).eq("match_id", match_id).execute()
    )
    return response.data


def update_set(set_id: str, set_data: dict):
    supabase = get_supabase_admin()
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
    supabase = get_supabase_admin()

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
        .gte("effective_date", today)
        .order("player_id")
        .order("effective_date")
        .order("created_at", desc=True)
        .execute()
    )

    data = response.data or []

    # -------------------------------------------------
    # Keep only the most recent row for the same
    # player + effective_date
    # -------------------------------------------------

    latest_by_player_date = {}

    for row in data:
        key = (
            row["player_id"],
            row["effective_date"],
        )

        existing = latest_by_player_date.get(key)

        if existing is None or row["created_at"] > existing["created_at"]:
            latest_by_player_date[key] = row

    deduped_rows = list(latest_by_player_date.values())

    deduped_rows.sort(
        key=lambda r: (
            r["player_id"],
            r["effective_date"],
            r["created_at"],
        )
    )

    # -------------------------------------------------
    # Group consecutive status changes together
    # Same player + same active status + touching dates
    # -------------------------------------------------

    grouped = []

    for row in deduped_rows:
        player = row.get("players") or {}

        current = {
            "player_id": row["player_id"],
            "name": player.get("name"),
            "email": player.get("email"),
            "active": row["active"],
            "effective_date": row["effective_date"],
            "end_date": row["end_date"],
            "created_at": row["created_at"],
        }

        if not grouped:
            grouped.append(current)
            continue

        previous = grouped[-1]

        same_player = previous["player_id"] == current["player_id"]
        same_status = previous["active"] == current["active"]

        previous_end = previous["end_date"]
        current_start = current["effective_date"]

        consecutive = False

        if previous_end is not None:
            previous_end_date = date.fromisoformat(previous_end)
            current_start_date = date.fromisoformat(current_start)

            consecutive = current_start_date <= previous_end_date + timedelta(days=1)

        if same_player and same_status and consecutive:
            previous["end_date"] = current["end_date"]
            previous["created_at"] = max(previous["created_at"], current["created_at"])
        else:
            grouped.append(current)

    grouped.sort(
        key=lambda r: (
            r["effective_date"],
            r["name"] or "",
        )
    )

    return grouped

def send_match_edit_email(subject: str, body: str):
    gmail_address = st.secrets["GMAIL_ADDRESS"]
    gmail_app_password = st.secrets["GMAIL_APP_PASSWORD"]

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = gmail_address
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(msg)

def insert_ladder_box_snapshot(rows: list[dict]):
    supabase = get_supabase()

    response = (
        supabase.table("ladder_box_snapshots")
        .insert(rows)
        .execute()
    )

    return response.data


def get_latest_ladder_box_snapshot(year: int):
    supabase = get_supabase()

    latest_response = (
        supabase.table("ladder_box_snapshots")
        .select("created_at")
        .eq("year", year)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )

    if not latest_response.data:
        return []

    latest_created_at = latest_response.data[0]["created_at"]

    response = (
        supabase.table("ladder_box_snapshots")
        .select("*")
        .eq("year", year)
        .eq("created_at", latest_created_at)
        .order("overall_rank")
        .execute()
    )

    return response.data