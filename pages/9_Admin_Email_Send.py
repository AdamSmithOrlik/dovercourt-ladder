import streamlit as st
import pandas as pd
import smtplib

from email.message import EmailMessage

from db import get_active_players
from utils.elo import get_latest_elo_standings

st.set_page_config(page_title="Admin — Box Emails", layout="wide")
st.title("Admin — Box Emails")

BOX_SIZE = 5

SEASON_START_DATES = {
    2025: "2025-04-01",
    2026: "2026-04-01",
}


# ---------------------------------------------------
# Helpers
# ---------------------------------------------------

def get_season_start_date(year: int) -> str | None:
    return SEASON_START_DATES.get(year)


def assign_boxes(df: pd.DataFrame, box_size: int = 5) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df["box"] = ((df["rank"] - 1) // box_size) + 1

    last_box = int(df["box"].max())
    last_box_count = int((df["box"] == last_box).sum())

    if last_box > 1 and last_box_count < box_size:
        df.loc[df["box"] == last_box, "box"] = last_box - 1

    return df


def get_active_player_lookup() -> pd.DataFrame:
    players = get_active_players()
    players_df = pd.DataFrame(players) if players else pd.DataFrame()

    if players_df.empty:
        return pd.DataFrame(columns=["player_id", "player_name", "email"])

    if "player_id" not in players_df.columns:
        raise ValueError("get_active_players() must return 'player_id'.")

    if "name" not in players_df.columns:
        raise ValueError("get_active_players() must return 'name'.")

    if "email" not in players_df.columns:
        players_df["email"] = ""

    players_df = players_df[["player_id", "name", "email"]].copy()
    players_df = players_df.rename(columns={"name": "player_name"})
    players_df["email"] = players_df["email"].fillna("").astype(str)

    return players_df


def build_live_box_standings(year: int) -> pd.DataFrame:
    active_df = get_active_player_lookup()

    if active_df.empty:
        return pd.DataFrame(
            columns=["player_id", "player_name", "email", "elo", "rank", "box"]
        )

    season_start_date = get_season_start_date(year)

    standings_df = get_latest_elo_standings(
        year=year,
        season_start_date=season_start_date,
    )

    standings_df = (
        standings_df.copy()
        if standings_df is not None and not standings_df.empty
        else pd.DataFrame(columns=["player_id", "player_name", "elo"])
    )

    merged = active_df.merge(
        standings_df[["player_id", "elo"]] if "elo" in standings_df.columns else standings_df,
        on="player_id",
        how="left",
    )

    merged["elo"] = pd.to_numeric(merged["elo"], errors="coerce").fillna(1500.0)

    merged = merged.sort_values(
        ["elo", "player_name"],
        ascending=[False, True],
    ).reset_index(drop=True)

    merged["rank"] = range(1, len(merged) + 1)
    merged = assign_boxes(merged, BOX_SIZE)

    return merged


def build_box_members_text(box_df: pd.DataFrame) -> str:
    if box_df.empty:
        return ""

    lines = []
    box_number = int(box_df["box"].iloc[0])
    lines.append(f"Box {box_number}")
    lines.append("")

    for _, row in box_df.sort_values("rank").iterrows():
        name = row["player_name"]
        email = row["email"]
        elo = row["elo"]

        if email:
            lines.append(f"{int(row['rank'])}. {name} — {email} — Elo {elo:.1f}")
        else:
            lines.append(f"{int(row['rank'])}. {name} — Elo {elo:.1f}")

    return "\n".join(lines)


def default_email_subject(year: int, box_number: int) -> str:
    return f"{year} Tennis Ladder — Your Box {box_number}"


def default_email_body(recipient_name: str, year: int, box_number: int, box_df: pd.DataFrame) -> str:
    members_text = build_box_members_text(box_df)

    return f"""Hi {recipient_name},

Here is your current ladder box for {year}.

{members_text}

Feel free to coordinate matches directly with the players in your box to complete the matches in the next 3 weeks.

Best,
Karim
"""


def send_gmail_email(to_email: str, subject: str, body: str) -> None:
    gmail_address = st.secrets.get("GMAIL_ADDRESS")
    gmail_app_password = st.secrets.get("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_app_password:
        raise ValueError(
            "Missing GMAIL_ADDRESS or GMAIL_APP_PASSWORD in Streamlit secrets."
        )

    msg = EmailMessage()
    msg["From"] = gmail_address
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_address, gmail_app_password)
        smtp.send_message(msg)


# ---------------------------------------------------
# Load standings
# ---------------------------------------------------

top_col1, top_col2 = st.columns([1, 1])

with top_col1:
    selected_year = st.selectbox(
        "Year",
        options=[2026, 2025],
        index=0,
    )

standings_df = build_live_box_standings(selected_year)

if standings_df.empty:
    st.info("No active players found.")
    st.stop()

with top_col2:
    selected_box_filter = st.selectbox(
        "Filter to box",
        options=["All"] + sorted(standings_df["box"].dropna().astype(int).unique().tolist()),
        index=0,
    )

display_df = standings_df.copy()
if selected_box_filter != "All":
    display_df = display_df[display_df["box"] == int(selected_box_filter)].copy()

st.subheader("Current Elo + Boxes")

show_df = display_df.copy()
show_df["elo"] = pd.to_numeric(show_df["elo"], errors="coerce").round(1)

st.dataframe(
    show_df[["box", "rank", "player_name", "email", "elo"]].rename(
        columns={
            "box": "Box",
            "rank": "Rank",
            "player_name": "Player",
            "email": "Email",
            "elo": "Elo",
        }
    ),
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------
# Recipient selection
# ---------------------------------------------------

st.markdown("---")
st.subheader("Recipients")

recipient_options_df = display_df.copy().sort_values(["box", "rank"]).reset_index(drop=True)
recipient_labels = [
    f"Box {int(row.box)} — {row.player_name} ({row.email if row.email else 'no email'})"
    for row in recipient_options_df.itertuples()
]

label_to_player_id = {
    label: recipient_options_df.iloc[idx]["player_id"]
    for idx, label in enumerate(recipient_labels)
}

button_col1, button_col2 = st.columns([1, 1])

if "selected_recipient_labels" not in st.session_state:
    st.session_state["selected_recipient_labels"] = []

with button_col1:
    if st.button("Select All"):
        st.session_state["selected_recipient_labels"] = recipient_labels

with button_col2:
    if st.button("Clear All"):
        st.session_state["selected_recipient_labels"] = []

selected_recipient_labels = st.multiselect(
    "Choose participants to email",
    options=recipient_labels,
    key="selected_recipient_labels",
)

selected_player_ids = [
    label_to_player_id[label]
    for label in selected_recipient_labels
    if label in label_to_player_id
]

selected_recipients_df = standings_df[
    standings_df["player_id"].isin(selected_player_ids)
].copy()

if selected_recipients_df.empty:
    st.caption("Select one or more recipients to generate email drafts.")
    st.stop()

# ---------------------------------------------------
# Preview selected recipients + their boxes
# ---------------------------------------------------

st.markdown("---")
st.subheader("Selected Recipients + Box Preview")

preview_rows = []
for _, recipient in selected_recipients_df.sort_values(["box", "rank"]).iterrows():
    box_df = standings_df[standings_df["box"] == recipient["box"]].copy()

    preview_rows.append(
        {
            "Recipient": recipient["player_name"],
            "Recipient Email": recipient["email"],
            "Box": int(recipient["box"]),
            "Box Players": ", ".join(box_df.sort_values("rank")["player_name"].tolist()),
        }
    )

preview_df = pd.DataFrame(preview_rows)

st.dataframe(
    preview_df,
    use_container_width=True,
    hide_index=True,
)

# ---------------------------------------------------
# Draft builder
# ---------------------------------------------------

st.markdown("---")
st.subheader("Email Draft")

st.markdown("---")
st.subheader("Send Confirmation")

admin_password_input = st.text_input(
    "Admin password",
    type="password",
    key="admin_email_password_input",
)

admin_password_expected = st.secrets.get("ADMIN_PASSWORD")

draft_mode = st.radio(
    "Draft mode",
    options=["One shared draft for all selected recipients", "Per-recipient draft preview"],
    index=0,
)

admin_password_expected = st.secrets.get("ADMIN_PASSWORD")

if draft_mode == "One shared draft for all selected recipients":
    unique_boxes = sorted(selected_recipients_df["box"].dropna().astype(int).unique().tolist())

    shared_lines = [
        f"Hi everyone,",
        "",
        f"Here are the current ladder box groupings for {selected_year}.",
        "",
    ]

    for box_number in unique_boxes:
        box_df = standings_df[standings_df["box"] == box_number].copy()
        shared_lines.append(build_box_members_text(box_df))
        shared_lines.append("")

    shared_lines.append("Feel free to coordinate matches directly with the players in your box.")
    shared_lines.append("")
    shared_lines.append("Best,")
    shared_lines.append("Karim")

    shared_subject = st.text_input(
        "Email subject",
        value=f"{selected_year} Tennis Ladder — Current Box Groups",
    )

    shared_body = st.text_area(
        "Email body",
        value="\n".join(shared_lines),
        height=420,
    )

    valid_recipients_df = selected_recipients_df[
        selected_recipients_df["email"].fillna("").str.strip() != ""
    ].copy()

    st.caption(f"Will send to {len(valid_recipients_df)} recipient(s) with valid email addresses.")

    if st.button("Send Shared Email", type="primary"):
        if not admin_password_expected:
            st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        elif admin_password_input != admin_password_expected:
            st.error("Incorrect admin password.")
        elif valid_recipients_df.empty:
            st.error("No selected recipients have valid email addresses.")
        else:
            sent = 0
            failed = []

            for _, row in valid_recipients_df.iterrows():
                try:
                    send_gmail_email(
                        to_email=row["email"],
                        subject=shared_subject,
                        body=shared_body,
                    )
                    sent += 1
                except Exception as e:
                    failed.append(f"{row['player_name']} ({row['email']}): {e}")

            if sent:
                st.success(f"Sent {sent} email(s).")

            if failed:
                st.error("Some emails failed:")
                for item in failed:
                    st.write(f"- {item}")

else:
    st.caption("Preview each email below, customize the shared template fields, then send all.")

    intro_text = st.text_area(
        "Intro / shared body text",
        value="Here is your current ladder box.",
        height=100,
    )

    closing_text = st.text_area(
        "Closing",
        value="Feel free to coordinate matches directly with the players in your box.\n\nBest,\nKarim",
        height=120,
    )

    draft_payloads = []

    for _, recipient in selected_recipients_df.sort_values(["box", "rank"]).iterrows():
        box_df = standings_df[standings_df["box"] == recipient["box"]].copy()
        subject = default_email_subject(selected_year, int(recipient["box"]))
        body = (
            f"Hi {recipient['player_name']},\n\n"
            f"{intro_text}\n\n"
            f"{build_box_members_text(box_df)}\n\n"
            f"{closing_text}"
        )

        draft_payloads.append(
            {
                "name": recipient["player_name"],
                "email": recipient["email"],
                "subject": subject,
                "body": body,
            }
        )

    for draft in draft_payloads:
        with st.expander(f"{draft['name']} — {draft['email'] if draft['email'] else 'no email'}", expanded=False):
            st.text_input(
                f"Subject — {draft['name']}",
                value=draft["subject"],
                key=f"subject_{draft['email']}_{draft['name']}",
            )
            st.text_area(
                f"Body — {draft['name']}",
                value=draft["body"],
                height=260,
                key=f"body_{draft['email']}_{draft['name']}",
            )

    if st.button("Send All Per-Recipient Emails", type="primary"):
        if not admin_password_expected:
            st.error("ADMIN_PASSWORD is not set in Streamlit secrets.")
        elif admin_password_input != admin_password_expected:
            st.error("Incorrect admin password.")
        else:
            sent = 0
            failed = []

        for draft in draft_payloads:
            email = draft["email"]
            if not email or not str(email).strip():
                failed.append(f"{draft['name']}: no email address")
                continue

            subject_value = st.session_state.get(
                f"subject_{draft['email']}_{draft['name']}",
                draft["subject"],
            )
            body_value = st.session_state.get(
                f"body_{draft['email']}_{draft['name']}",
                draft["body"],
            )

            try:
                send_gmail_email(
                    to_email=email,
                    subject=subject_value,
                    body=body_value,
                )
                sent += 1
            except Exception as e:
                failed.append(f"{draft['name']} ({email}): {e}")

        if sent:
            st.success(f"Sent {sent} email(s).")

        if failed:
            st.error("Some emails failed:")
            for item in failed:
                st.write(f"- {item}")