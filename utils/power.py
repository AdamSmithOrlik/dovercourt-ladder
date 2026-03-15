# in progress...

import pandas as pd


def compute_power_ranking(players, matches, sets):
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

    match_df = pd.DataFrame(matches) if matches else pd.DataFrame()
    sets_df = pd.DataFrame(sets) if sets else pd.DataFrame()

    power = []

    for _, player in players_df.iterrows():
        player_id = player["player_id"]
        player_name = player["name"]

        wins = 0
        losses = 0
        matches_played = 0
        score_diff = 0

        if not match_df.empty:

            wins = (match_df["winner_id"] == player_id).sum()

            played_mask = (
                (match_df["player_id"] == player_id)
                | (match_df["opponent_id"] == player_id)
            )

            player_matches = match_df[played_mask]
            matches_played = len(player_matches)
            losses = matches_played - wins

            if not sets_df.empty:
                for _, match in player_matches.iterrows():
                    match_id = match["match_id"]

                    match_sets = sets_df[sets_df["match_id"] == match_id]

                    p_games = match_sets["player_games"].sum()
                    o_games = match_sets["opponent_games"].sum()

                    if match["player_id"] == player_id:
                        score_diff += p_games - o_games
                    else:
                        score_diff += o_games - p_games

        record = f"{wins}-{losses}"

        power.append(
            {
                "Player": player_name,
                "Wins": int(wins),
                "Losses": int(losses),
                "Record": record,
                "Matches Played": int(matches_played),
                "Score Diff": int(score_diff),
            }
        )

    power_df = pd.DataFrame(power)

    power_df = power_df.sort_values(
        by=["Wins", "Score Diff"],
        ascending=[False, False],
    ).reset_index(drop=True)

    return power_df


# def power_algorithm(power_df):
#     """
#     Compute power ranking based on the power dataframe.

#     The algorithm assigns a power score to each player based on their wins, losses, and score difference.
#     The formula is:


#     """
#     date = dt.datetime.now().strftime("%Y-%m-%d")
