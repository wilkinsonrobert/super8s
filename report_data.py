import json
from collections import defaultdict
from pathlib import Path


DATA_FILE = Path("gameweek_data.json")


def load_data():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_gameweek_matches(data, gameweek):
    """Return completed H2H matches for a gameweek."""
    return [
        match
        for match in data["matches"]
        if match["event"] == gameweek
        and (
            match["entry_1_points"] > 0
            or match["entry_2_points"] > 0
        )
    ]


def build_league_table(data, gameweek):
    """Build the H2H league table after a given gameweek."""
    table = {}

    for team in data["teams"]:
        entry_id = team["entry_id"]

        table[entry_id] = {
            "entry_id": entry_id,
            "team_name": team["team_name"],
            "manager": team["manager"],
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points": 0,
            "fpl_points": 0,
            "points_for": 0,
            "points_against": 0,
        }

    for match in data["matches"]:
        if match["event"] > gameweek:
            continue

        entry_1 = match["entry_1_entry"]
        entry_2 = match["entry_2_entry"]

        if entry_1 not in table or entry_2 not in table:
            continue

        p1 = match["entry_1_points"]
        p2 = match["entry_2_points"]

        # Ignore future/unplayed fixtures
        if p1 == 0 and p2 == 0:
            continue

        table[entry_1]["played"] += 1
        table[entry_2]["played"] += 1

        table[entry_1]["fpl_points"] += p1
        table[entry_2]["fpl_points"] += p2

        table[entry_1]["points_for"] += p1
        table[entry_2]["points_for"] += p2

        table[entry_1]["points_against"] += p2
        table[entry_2]["points_against"] += p1

        if p1 > p2:
            table[entry_1]["wins"] += 1
            table[entry_1]["points"] += 3
            table[entry_2]["losses"] += 1

        elif p2 > p1:
            table[entry_2]["wins"] += 1
            table[entry_2]["points"] += 3
            table[entry_1]["losses"] += 1

        else:
            table[entry_1]["draws"] += 1
            table[entry_2]["draws"] += 1
            table[entry_1]["points"] += 1
            table[entry_2]["points"] += 1

    standings = sorted(
        table.values(),
        key=lambda team: (
            -team["points"],
            -team["points_for"],
            -team["wins"],
        ),
    )

    for position, team in enumerate(standings, start=1):
        team["position"] = position

    return standings


def analyse_gameweek(data, gameweek):
    """Produce the statistical facts needed by the AI report writer."""

    matches = get_gameweek_matches(data, gameweek)

    match_reports = []

    for match in matches:
        p1 = match["entry_1_points"]
        p2 = match["entry_2_points"]

        if p1 > p2:
            result = "home_win"
            margin = p1 - p2
        elif p2 > p1:
            result = "away_win"
            margin = p2 - p1
        else:
            result = "draw"
            margin = 0

        match_reports.append({
            "team_1": match["entry_1_name"],
            "manager_1": match["entry_1_player_name"],
            "score_1": p1,
            "team_2": match["entry_2_name"],
            "manager_2": match["entry_2_player_name"],
            "score_2": p2,
            "result": result,
            "margin": margin,
            "total_points": p1 + p2,
        })

    if not match_reports:
        return {
            "gameweek": gameweek,
            "matches": [],
        }

    highest_score = max(
        max(match["score_1"], match["score_2"])
        for match in match_reports
    )

    lowest_score = min(
        min(match["score_1"], match["score_2"])
        for match in match_reports
    )

    biggest_margin = max(
        match["margin"] for match in match_reports
    )

    narrowest_margin = min(
        match["margin"]
        for match in match_reports
        if match["margin"] > 0
    )

    highest_scoring_match = max(
        match_reports,
        key=lambda match: match["total_points"]
    )

    lowest_scoring_match = min(
        match_reports,
        key=lambda match: match["total_points"]
    )

    narrowest_match = min(
        [
            match
            for match in match_reports
            if match["margin"] > 0
        ],
        key=lambda match: match["margin"]
    )

    biggest_match = max(
        match_reports,
        key=lambda match: match["margin"]
    )

    return {
        "gameweek": gameweek,
        "matches": match_reports,
        "summary": {
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "biggest_margin": biggest_margin,
            "narrowest_margin": narrowest_margin,
            "highest_scoring_match": highest_scoring_match,
            "lowest_scoring_match": lowest_scoring_match,
            "narrowest_match": narrowest_match,
            "biggest_match": biggest_match,
        },
    }


def analyse_players(data, gameweek):
    """Analyse player performances across the Super 8s."""

    weekly_data = data["weekly_team_data"].get(str(gameweek), {})

    players = []

    for team_data in weekly_data.values():

        for player in team_data["players"]:

            players.append({
                "name": player["name"],
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "captain": player["captain"],
                "multiplier": player["multiplier"],
                "slot": player["slot"],
            })

    return players


def analyse_bench_and_captains(data, gameweek):
    """Identify captain and bench-related information."""

    weekly_data = data["weekly_team_data"].get(str(gameweek), {})

    results = []

    for team_data in weekly_data.values():

        captain = None
        vice_captain = None
        bench = []

        for player in team_data["players"]:

            if player["captain"]:
                captain = player

            if player["vice_captain"]:
                vice_captain = player

            if player["slot"] > 11:
                bench.append(player)

        results.append({
            "team_name": team_data["team_name"],
            "manager": team_data["manager"],
            "captain": captain,
            "vice_captain": vice_captain,
            "bench": bench,
            "active_chip": team_data["active_chip"],
            "automatic_subs": team_data["automatic_subs"],
        })

    return results


def build_report_data(data, gameweek):
    """Build the complete fact sheet for the AI."""

    league_table = build_league_table(data, gameweek)
    gameweek_analysis = analyse_gameweek(data, gameweek)
    player_analysis = analyse_players(data, gameweek)
    captain_bench_analysis = analyse_bench_and_captains(
        data,
        gameweek
    )

    return {
        "league_name": "Super 8s",
        "gameweek": gameweek,
        "league_table": league_table,
        "gameweek_analysis": gameweek_analysis,
        "player_analysis": player_analysis,
        "captain_bench_analysis": captain_bench_analysis,
    }


def main():

    print("Loading Super 8s data...")

    data = load_data()

    completed_gameweeks = data.get(
        "completed_gameweeks",
        []
    )

    if not completed_gameweeks:
        print("No completed gameweeks found.")
        return

    latest_gameweek = max(completed_gameweeks)

    print(
        f"Analysing Gameweek {latest_gameweek}..."
    )

    report_data = build_report_data(
        data,
        latest_gameweek
    )

    output_path = Path("report_data.json")

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report_data,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Report data saved to {output_path}"
    )


if __name__ == "__main__":
    main()
