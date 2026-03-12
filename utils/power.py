# in progress...

import re
import pandas as pd
import datetime as dt


def parse_score_text(score_text: str) -> tuple[int, int]:
    """
    Parse tennis score text into total points for player1 and player2.

    Examples
    --------
    "6-4,4-6,6-2"         -> (16, 12)
    "7-6(10-8),4-6,6-3"   -> (18, 15)
    "6-7(8-10),6-4,1-0"   -> (13, 12)

    Rule for tiebreak sets
    ----------------------
    A set like 7-6(10-8) counts as:
        player1: 7 + 1
        player2: 6 + 0
    """
    if not score_text or not str(score_text).strip():
        return 0, 0

    p1_total = 0
    p2_total = 0

    sets = [s.strip() for s in str(score_text).split(",") if s.strip()]

    for set_score in sets:
        m = re.match(r"^(\d+)-(\d+)(?:\((\d+)-(\d+)\))?$", set_score)
        if not m:
            continue

        a = int(m.group(1))
        b = int(m.group(2))
        tb_a = m.group(3)
        tb_b = m.group(4)

        # add the base set score
        p1_total += a
        p2_total += b

        # if there is a tiebreak, add +1 to the tiebreak winner
        if tb_a is not None and tb_b is not None:
            tb_a = int(tb_a)
            tb_b = int(tb_b)

            if tb_a > tb_b:
                p1_total += 1
            elif tb_b > tb_a:
                p2_total += 1

    return p1_total, p2_total


def compute_power_ranking(players, matches):
    players_df = pd.DataFrame(players)

    if players_df.empty:
        return pd.DataFrame(
            columns=[
                "Player",
                "Wins",
                "Losses",
                "Record",
                "Matches Played",
                "Score Diff",
            ]
        )

    power = []
    match_df = pd.DataFrame(matches) if matches else pd.DataFrame()

    for _, player in players_df.iterrows():
        player_id = player["id"]
        player_name = player["name"]

        if match_df.empty:
            wins = 0
            losses = 0
            matches_played = 0
            score_diff = 0
        else:
            wins = (match_df["winner_id"] == player_id).sum()

            played_mask = (match_df["player1_id"] == player_id) | (
                match_df["player2_id"] == player_id
            )
            player_matches = match_df[played_mask]

            matches_played = len(player_matches)
            losses = matches_played - wins

            for _, match in player_matches.iterrows():
                p1_score, p2_score = parse_score_text(match.get("score_text", ""))

                if match["player1_id"] == player_id:
                    score_diff += p1_score - p2_score
                else:
                    score_diff += p2_score - p1_score

        record = f"{wins}-{losses}"

        power.append(
            {
                "Player": player_name,
                "Wins": wins,
                "Losses": losses,
                "Record": record,
                "Matches Played": matches_played,
                "Score Diff": score_diff,
            }
        )

    power_df = pd.DataFrame(power)

    power_df = power_df.sort_values(
        by=["Wins", "Score Diff"], ascending=[False, False]
    ).reset_index(drop=True)

    return power_df


# def power_algorithm(power_df):
#     """
#     Compute power ranking based on the power dataframe.

#     The algorithm assigns a power score to each player based on their wins, losses, and score difference.
#     The formula is:


#     """
#     date = dt.datetime.now().strftime("%Y-%m-%d")
