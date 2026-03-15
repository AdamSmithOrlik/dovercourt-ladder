import pandas as pd


def compute_rankings(players, matches):
    players_df = pd.DataFrame(players)

    if players_df.empty:
        return pd.DataFrame(columns=["Player", "Matches Played", "Wins", "Losses", "Record"])

    rankings = []
    match_df = pd.DataFrame(matches) if matches else pd.DataFrame()

    for _, player in players_df.iterrows():
        player_id = player["player_id"]
        player_name = player["name"]

        if match_df.empty:
            wins = 0
            losses = 0
            matches_played = 0
        else:
            wins = (match_df["winner_id"] == player_id).sum()

            played_mask = (
                (match_df["player_id"] == player_id) |
                (match_df["opponent_id"] == player_id)
            )

            matches_played = played_mask.sum()
            losses = matches_played - wins

        rankings.append(
            {
                "Player": player_name,
                "Matches Played": int(matches_played),
                "Wins": int(wins),
                "Losses": int(losses),
                "Record": f"{wins}-{losses}",
            }
        )

    rankings_df = pd.DataFrame(rankings)

    rankings_df = rankings_df.sort_values(
        by=["Wins", "Losses", "Player"],
        ascending=[False, True, True]
    ).reset_index(drop=True)

    rankings_df.index = rankings_df.index + 1
    rankings_df.index.name = "Rank"

    return rankings_df
