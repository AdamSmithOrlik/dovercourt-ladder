import re

def parse_score_flexible(score_text):

    if not score_text:
        return None

    cleaned = score_text.replace(",", " ")
    parts = [p.strip() for p in cleaned.split() if p.strip()]

    parsed_sets = []
    p_sets = 0
    o_sets = 0

    for i, part in enumerate(parts):

        m = re.match(r"^(\d+)-(\d+)$", part)

        if not m:
            return None

        p_games = int(m.group(1))
        o_games = int(m.group(2))

        if p_games > o_games:
            p_sets += 1
        elif o_games > p_games:
            o_sets += 1

        parsed_sets.append({
            "set_number": i + 1,
            "player_games": p_games,
            "opponent_games": o_games,
            "is_tiebreak": (
                (p_games >= 7 and o_games >= 6)
                or (o_games >= 7 and p_games >= 6)
                or (p_games >= 10 or o_games >= 10)
            )
        })

    return parsed_sets, p_sets, o_sets
