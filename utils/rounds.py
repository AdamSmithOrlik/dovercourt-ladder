from datetime import date, timedelta

BOX_SIZE = 5

# ---------------------------------------------------
# Hardcoded 2026 round schedule
# ---------------------------------------------------

ROUND_1_START = date(2026, 5, 1)
ROUND_1_END = date(2026, 5, 24)

# After round 1, each round starts every 18 days
SUBSEQUENT_ROUND_LENGTH_DAYS = 21
SEASON_END = date(2026, 9, 27)

SEASON_START_DATES = {
    2025: "2025-04-01",
    2026: "2026-04-01",
}


# ---------------------------------------------------
# Round schedule helpers
# ---------------------------------------------------

def build_round_windows_2026() -> list[dict]:
    rounds = [
        {
            "year": 2026,
            "round": 1,
            "start_date": ROUND_1_START,
            "end_date": ROUND_1_END,
        }
    ]

    round_number = 2
    current_start = date(2026, 5, 25)  # Monday after round 1 ends

    while current_start <= SEASON_END:
        current_end = current_start + timedelta(days=SUBSEQUENT_ROUND_LENGTH_DAYS - 1)
        if current_end > SEASON_END:
            current_end = SEASON_END

        rounds.append(
            {
                "year": 2026,
                "round": round_number,
                "start_date": current_start,
                "end_date": current_end,
            }
        )

        round_number += 1
        current_start = current_start + timedelta(days=SUBSEQUENT_ROUND_LENGTH_DAYS)

    return rounds


ROUND_WINDOWS_2026 = build_round_windows_2026()


def get_round_window(year: int, round_number: int) -> dict | None:
    if year != 2026:
        return None

    for round_info in ROUND_WINDOWS_2026:
        if round_info["year"] == year and round_info["round"] == round_number:
            return round_info

    return None


def get_current_round_from_date(today: date | None = None) -> tuple[int | None, int | None]:
    if today is None:
        today = date.today()

    for round_info in ROUND_WINDOWS_2026:
        if round_info["start_date"] <= today <= round_info["end_date"]:
            return round_info["year"], round_info["round"]

    return None, None


def get_last_completed_round_from_date(today: date | None = None) -> tuple[int | None, int | None]:
    if today is None:
        today = date.today()

    completed_rounds = [r for r in ROUND_WINDOWS_2026 if r["end_date"] < today]

    if not completed_rounds:
        return None, None

    latest = completed_rounds[-1]
    return latest["year"], latest["round"]


def get_default_round_for_year(year: int) -> int:
    if year == 2026:
        current_year, current_round = get_current_round_from_date()

        if current_year == 2026 and current_round is not None:
            return current_round

        today = date.today()
        if today < ROUND_1_START:
            return 1

        return ROUND_WINDOWS_2026[-1]["round"]

    # 2025 fallback
    return 1


def get_season_start_date(year: int) -> str | None:
    return SEASON_START_DATES.get(year)


def get_round_cutoff_exclusive(round_end_date: date) -> str:
    """
    utils.elo uses match_date < season_end_date,
    so to include the whole round end date we pass the next day.
    """
    return (round_end_date + timedelta(days=1)).isoformat()

if __name__ == "__main__":
    rounds = build_round_windows_2026()

    for r in rounds:
        print(r)