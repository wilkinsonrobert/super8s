import json
from pathlib import Path
from collections import defaultdict


INPUT_FILE = Path("gameweek_data.json")
OUTPUT_FILE = Path("report_data.json")


def load_data():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def get_matches(data):
    """
    Supports the current gameweek_data structure and extracts
    completed H2H matches.
    """
    if isinstance(data, list):
        return data

    if "matches" in data:
        return data["matches"]

    if "gameweeks" in data:
        matches = []
        for gw in data["gameweeks"]:
            matches.extend(gw.get("matches", []))
        return matches

    return []


def get_current_gameweek(data):
    if isinstance(data, dict):
        if "current_gameweek" in data:
            return safe_int(data["current_gameweek"])

        if "gameweek" in data:
            return safe_int(data["gameweek"])

        if "current_gameweek" in data.get("metadata", {}):
            return safe_int(data["metadata"]["current_gameweek"])

    matches = get_matches(data)
    completed = [
        safe_int(m.get("event"))
        for m in matches
        if safe_int(m.get("event")) > 0
    ]

    return max(completed) if completed else 0


def get_match_gameweek(match):
    return safe_int(match.get("event"))


def get_completed_matches(data):
    matches = get_matches(data)

    completed = []

    for match in matches:
        score_1 = match.get("entry_1_points")
        score_2 = match.get("entry_2_points")

        if score_1 is None or score_2 is None:
            continue

        event = get_match_gameweek(match)

        if event <= 0:
            continue

        # Ignore completely unplayed future fixtures.
        if safe_int(score_1) == 0 and safe_int(score_2) == 0:
            continue

        completed.append(match)

    return completed


def get_latest_completed_gameweek(data):
    matches = get_completed_matches(data)

    if not matches:
        return 0

    return max(get_match_gameweek(m) for m in matches)


def calculate_match_result(score_1, score_2):
    score_1 = safe_int(score_1)
    score_2 = safe_int(score_2)

    if score_1 > score_2:
        return "home_win"
    elif score_2 > score_1:
        return "away_win"
    else:
        return "draw"


def player_effective_points(player):
    return safe_int(player.get("effective_points"))


def player_actual_points(player):
    return safe_int(player.get("points"))


def analyse_players(players):
    """
    Produces useful facts for the eventual AI-written report.
    """

    selected = []
    bench = []
    captains = []
    vice_captains = []

    for player in players:
        multiplier = safe_int(player.get("multiplier"), 1)
        actual = player_actual_points(player)
        effective = player_effective_points(player)

        enriched = {
            "id": player.get("id"),
            "name": player.get("name"),
            "position": player.get("position"),
            "slot": player.get("slot"),
            "points": actual,
            "effective_points": effective,
            "multiplier": multiplier,
            "captain": bool(player.get("captain")),
            "vice_captain": bool(player.get("vice_captain")),
        }

        # multiplier 0 means the player was on the bench.
        if multiplier == 0:
            bench.append(enriched)
        else:
            selected.append(enriched)

        if player.get("captain"):
            captains.append(enriched)

        if player.get("vice_captain"):
            vice_captains.append(enriched)

    selected_sorted = sorted(
        selected,
        key=lambda p: p["effective_points"],
        reverse=True
    )

    bench_sorted = sorted(
        bench,
        key=lambda p: p["points"],
        reverse=True
    )

    captain = captains[0] if captains else None

    captain_analysis = None

    if captain:
        captain_analysis = {
            "name": captain["name"],
            "points": captain["points"],
            "effective_points": captain["effective_points"],
            "multiplier": captain["multiplier"],
        }

    return {
        "selected_players": selected_sorted,
        "bench_players": bench_sorted,
        "captain": captain_analysis,
        "vice_captain": (
            {
                "name": vice_captains[0]["name"],
                "points": vice_captains[0]["points"],
            }
            if vice_captains
            else None
        ),
        "highest_scorer": (
            selected_sorted[0]
            if selected_sorted
            else None
        ),
        "lowest_scorer": (
            selected_sorted[-1]
            if selected_sorted
            else None
        ),
        "bench_points": sum(p["points"] for p in bench),
        "selected_actual_points": sum(
            p["points"] for p in selected
        ),
        "selected_effective_points": sum(
            p["effective_points"] for p in selected
        ),
    }


def build_match_analysis(match):
    score_1 = safe_int(match.get("entry_1_points"))
    score_2 = safe_int(match.get("entry_2_points"))

    result = calculate_match_result(score_1, score_2)

    team_1 = {
        "entry_id": match.get("entry_1_entry"),
        "team_name": match.get("entry_1_name"),
        "manager": match.get("entry_1_player_name"),
        "score": score_1,
        "result": (
            "win" if result == "home_win"
            else "draw" if result == "draw"
            else "loss"
        ),
    }

    team_2 = {
        "entry_id": match.get("entry_2_entry"),
        "team_name": match.get("entry_2_name"),
        "manager": match.get("entry_2_player_name"),
        "score": score_2,
        "result": (
            "win" if result == "away_win"
            else "draw" if result == "draw"
            else "loss"
        ),
    }

    return {
        "match_id": match.get("id"),
        "gameweek": get_match_gameweek(match),
        "team_1": team_1,
        "team_2": team_2,
        "result": result,
        "margin": abs(score_1 - score_2),
        "total_points": score_1 + score_2,
    }


def build_team_data(data, latest_gameweek):
    """
    Build a list of teams and their latest player information.
    """

    teams = {}

    # The player-analysis information produced by fpl_data.py
    # may be stored at the top level.
    player_analysis = []

    if isinstance(data, dict):
        player_analysis = data.get("player_analysis", [])

    for player in player_analysis:
        entry_id = player.get("entry_id")

        if entry_id is None:
            entry_id = player.get("team_entry")

        if entry_id is None:
            continue

        if entry_id not in teams:
            teams[entry_id] = {
                "entry_id": entry_id,
                "team_name": player.get("team_name"),
                "manager": player.get("manager"),
                "players": [],
            }

        teams[entry_id]["players"].append(player)

    return list(teams.values())


def calculate_week_summary(matches):
    if not matches:
        return {}

    highest_score = max(
        max(
            safe_int(m["entry_1_points"]),
            safe_int(m["entry_2_points"])
        )
        for m in matches
    )

    lowest_score = min(
        min(
            safe_int(m["entry_1_points"]),
            safe_int(m["entry_2_points"])
        )
        for m in matches
    )

    biggest_margin_match = max(
        matches,
        key=lambda m: abs(
            safe_int(m["entry_1_points"])
            - safe_int(m["entry_2_points"])
        )
    )

    narrowest_margin_match = min(
        matches,
        key=lambda m: abs(
            safe_int(m["entry_1_points"])
            - safe_int(m["entry_2_points"])
        )
    )

    highest_scoring_match = max(
        matches,
        key=lambda m:
        safe_int(m["entry_1_points"])
        + safe_int(m["entry_2_points"])
    )

    lowest_scoring_match = min(
        matches,
        key=lambda m:
        safe_int(m["entry_1_points"])
        + safe_int(m["entry_2_points"])
    )

    return {
        "highest_score": highest_score,
        "lowest_score": lowest_score,

        "biggest_margin": abs(
            safe_int(biggest_margin_match["entry_1_points"])
            - safe_int(biggest_margin_match["entry_2_points"])
        ),

        "narrowest_margin": abs(
            safe_int(narrowest_margin_match["entry_1_points"])
            - safe_int(narrowest_margin_match["entry_2_points"])
        ),

        "highest_scoring_match": build_match_analysis(
            highest_scoring_match
        ),

        "lowest_scoring_match": build_match_analysis(
            lowest_scoring_match
        ),

        "narrowest_match": build_match_analysis(
            narrowest_margin_match
        ),

        "biggest_match": build_match_analysis(
            biggest_margin_match
        ),
    }


def calculate_team_records(matches):
    records = defaultdict(
        lambda: {
            "team_name": "",
            "manager": "",
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points": 0,
            "fpl_points": 0,
            "for": 0,
            "against": 0,
        }
    )

    for match in matches:
        event = get_match_gameweek(match)

        if event <= 0:
            continue

        score_1 = safe_int(match.get("entry_1_points"))
        score_2 = safe_int(match.get("entry_2_points"))

        entry_1 = match.get("entry_1_entry")
        entry_2 = match.get("entry_2_entry")

        team_1 = records[entry_1]
        team_1["team_name"] = match.get("entry_1_name")
        team_1["manager"] = match.get("entry_1_player_name")

        team_2 = records[entry_2]
        team_2["team_name"] = match.get("entry_2_name")
        team_2["manager"] = match.get("entry_2_player_name")

        team_1["played"] += 1
        team_2["played"] += 1

        team_1["for"] += score_1
        team_1["against"] += score_2

        team_2["for"] += score_2
        team_2["against"] += score_1

        if score_1 > score_2:
            team_1["wins"] += 1
            team_1["points"] += 3
            team_2["losses"] += 1

        elif score_2 > score_1:
            team_2["wins"] += 1
            team_2["points"] += 3
            team_1["losses"] += 1

        else:
            team_1["draws"] += 1
            team_2["draws"] += 1
            team_1["points"] += 1
            team_2["points"] += 1

    # Sort by H2H league rules:
    # points first, then points difference, then points scored.
    table = list(records.values())

    for team in table:
        team["difference"] = (
            team["for"] - team["against"]
        )

        team["win_percentage"] = (
            round(
                (team["wins"] / team["played"]) * 100,
                1
            )
            if team["played"]
            else 0
        )

    table.sort(
        key=lambda t: (
            t["points"],
            t["difference"],
            t["for"]
        ),
        reverse=True
    )

    for position, team in enumerate(table, start=1):
        team["position"] = position

    return table


def build_player_highlights(data, latest_gameweek):
    """
    Look for standout individual player performances across
    the teams appearing in the latest completed gameweek.
    """

    player_analysis = []

    if isinstance(data, dict):
        player_analysis = data.get("player_analysis", [])

    latest_players = []

    for player in player_analysis:
        # If gameweek information is available, respect it.
        player_gw = player.get("gameweek")

        if player_gw is None or safe_int(player_gw) == latest_gameweek:
            latest_players.append(player)

    if not latest_players:
        latest_players = player_analysis

    enriched = []

    for player in latest_players:
        actual = player_actual_points(player)
        multiplier = safe_int(player.get("multiplier"), 1)
        effective = player_effective_points(player)

        enriched.append({
            "name": player.get("name"),
            "team_name": player.get("team_name"),
            "manager": player.get("manager"),
            "points": actual,
            "effective_points": effective,
            "multiplier": multiplier,
            "captain": bool(player.get("captain")),
            "bench": multiplier == 0,
        })

    selected = [
        p for p in enriched
        if not p["bench"]
    ]

    bench = [
        p for p in enriched
        if p["bench"]
    ]

    selected.sort(
        key=lambda p: p["effective_points"],
        reverse=True
    )

    bench.sort(
        key=lambda p: p["points"],
        reverse=True
    )

    captains = [
        p for p in enriched
        if p["captain"]
    ]

    captains.sort(
        key=lambda p: p["points"],
        reverse=True
    )

    worst_captains = sorted(
        captains,
        key=lambda p: p["points"]
    )

    return {
        "highest_player_scores": selected[:10],
        "biggest_bench_points": bench[:10],
        "best_captains": captains[:10],
        "worst_captains": worst_captains[:10],
    }


def build_report_data(data):
    latest_gameweek = get_latest_completed_gameweek(data)

    all_matches = get_completed_matches(data)

    week_matches = [
        m for m in all_matches
        if get_match_gameweek(m) == latest_gameweek
    ]

    week_analysis = [
        build_match_analysis(m)
        for m in week_matches
    ]

    week_analysis.sort(
        key=lambda m: m["match_id"]
        if m["match_id"] is not None
        else 0
    )

    league_table = calculate_team_records(all_matches)

    report = {
        "report_version": 3,

        "league": {
            "name": "Super 8s",
            "gameweek": latest_gameweek,
            "matches_this_week": len(week_analysis),
        },

        "weekly_summary": calculate_week_summary(
            week_matches
        ),

        "matches": week_analysis,

        "league_table": league_table,

        "player_highlights": build_player_highlights(
            data,
            latest_gameweek
        ),

        "reporting_notes": {
            "match_count": len(week_analysis),
            "all_matches_should_be_reported": True,
            "british_tone": True,
            "include_team_names": True,
            "occasionally_reference_managers": True,
            "use_banter": True,
        },
    }

    return report


def main():
    print("Reading Super 8s data...")

    if not INPUT_FILE.exists():
        raise FileNotFoundError(
            "gameweek_data.json was not found."
        )

    data = load_data()

    print("Building report analysis...")

    report = build_report_data(data)

    save_data(report)

    gameweek = report["league"]["gameweek"]
    match_count = report["league"]["matches_this_week"]

    print(
        f"Report analysis complete for Gameweek {gameweek}"
    )

    print(
        f"Matches analysed: {match_count}"
    )

    print(
        f"League table teams: "
        f"{len(report['league_table'])}"
    )

    print(
        f"Saved analysis to {OUTPUT_FILE}"
    )


if __name__ == "__main__":
    main()
