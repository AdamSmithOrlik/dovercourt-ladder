# Dovercourt Tennis Ladder

A simple **Streamlit + Supabase** application for managing the Dovercourt tennis ladder.

The app allows players to:
- View the ladder
- Submit match results
- Track match history and set scores
- Activate or deactivate players

---

# Tech Stack

**Frontend**
- Streamlit

**Backend**
- Supabase (PostgreSQL)

**Language**
- Python

---

# Project Structure

---

# Database Schema

The database uses the **public schema** and currently contains three tables.

---

## players

Stores information about ladder participants.

| column | type |
|------|------|
| player_id | uuid |
| name | text |
| email | text |
| cell_phone | text |
| active | boolean |

---

## matches

Stores match metadata.

| column | type |
|------|------|
| match_id | uuid |
| type | text |
| player_id | uuid |
| opponent_id | uuid |
| winner_id | uuid |
| match_date | timestamptz |
| created_at | timestamptz |

---

## sets

Stores set-level scoring for each match.

| column | type |
|------|------|
| set_id | uuid |
| match_id | uuid |
| set_number | smallint |
| player_games | smallint |
| opponent_games | smallint |
| is_tiebreak | boolean |
| created_at | timestamptz |

---

# Environment Setup

## 1. Clone the repository

```bash
git clone <repo-url>
cd dovercourt-ladder