import pandas as pd

BOX_SIZE = 5


def assign_boxes(df: pd.DataFrame, box_size: int = BOX_SIZE) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    df = df.copy()
    df["box"] = ((df["rank"] - 1) // box_size) + 1

    last_box = int(df["box"].max())
    last_box_count = int((df["box"] == last_box).sum())

    if last_box > 1 and last_box_count < box_size:
        df.loc[df["box"] == last_box, "box"] = last_box - 1

    return df


def compute_live_ranking(stats_df: pd.DataFrame) -> pd.DataFrame:
    if stats_df.empty:
        return stats_df.copy()

    ranked = stats_df.sort_values(
        ["elo", "player_name"],
        ascending=[False, True],
    ).reset_index(drop=True)

    ranked["rank"] = range(1, len(ranked) + 1)

    return assign_boxes(ranked)