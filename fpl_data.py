import json
import requests
from pathlib import Path
from collections import defaultdict


LEAGUE_ID = 54930
DATA_FILE = Path("gameweek_data.json")

BASE_URL = "https://fantasy.premierleague.com/api"


def get_json(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"FPL API returned {response.status_code} "
            f"for {url}"
        )

    return response.json()


def load_existing_data():
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            pass

    return {
        "league_id": LEAGUE_ID,
        "league_name": "Super 8s",
        "teams": [],
        "matches": [],
        "weekly_team_data": {},
        "weekly_reports": {},
        "completed_gameweeks": [],
        "report_version": 4,
    }


def get_league_matches():
    matches = []
    page = 1

    while True:
        data = get_json(
            f"leagues-h2h-matches/league/{LEAGUE_ID}/?page={page}"
        )

        results = data.get("results", [])
        matches.extend(results)

        if not data.get("has_next"):
            break

        page += 1

    return matches


def get_teams_from_matches(matches):
    """
    Build the Super 8s team list from the H2H matches.

    This avoids relying on the classic-league endpoint.
    """

    teams = {}

    for match in matches:

        entry_1 = match["entry_1_entry"]

        teams[entry_1] = {
            "entry_id": entry_1,
            "team_name": match["entry_1_name"],
            "manager": match["entry_1_player_name"],
        }

        entry_2 = match["entry_2_entry"]

        teams[entry_2] = {
            "entry_id": entry_2,
            "team_name": match["entry_2_name"],
            "manager": match["entry_2_player_name"],
        }

    return sorted(
        teams.values(),
        key=lambda team: team["team_name"].lower()
    )


def get_current_gameweek():
    data = get_json("bootstrap-static/")

    for event in data["events"]:
        if event["is_current"]:
            return event["id"]

    finished = [
        event["id"]
        for event in data["events"]
        if event["finished"]
    ]

    if finished:
        return max(finished)

    return None


def get_finished_gameweeks():
    data = get_json("bootstrap-static/")

    return [
        event["id"]
        for event in data["events"]
        if event["finished"]
    ]


def get_player_data():
    data = get_json("bootstrap-static/")

    players = {}

    for player in data["elements"]:

        players[player["id"]] = {
            "id": player["id"],
            "name": (
                f"{player['first_name']} "
                f"{player['second_name']}"
            ),
            "team": player["team"],
            "position": player["element_type"],
        }

    return players


def get_team_picks(entry_id, gameweek):
    return get_json(
        f"entry/{entry_id}/event/{gameweek}/picks/"
    )


def get_gameweek_player_points(gameweek):

    data = get_json(
        f"event/{gameweek}/live/"
    )

    points = {}

    for player in data.get("elements", []):

        points[player["id"]] = (
            player["stats"]["total_points"]
        )

    return points


def build_weekly_team_data(
    teams,
    gameweek,
    player_data,
    player_points
):

    weekly_data = {}

    for team in teams:

        entry_id = team["entry_id"]

        try:

            picks_data = get_team_picks(
                entry_id,
                gameweek
            )

        except Exception as error:

            print(
                f"Could not retrieve picks for "
                f"{team['team_name']}: {error}"
            )

            continue

        players = []

        for pick in picks_data["picks"]:

            player_id = pick["element"]

            player = player_data.get(
                player_id,
                {}
            )

            points = player_points.get(
                player_id,
                0
            )

            players.append({

                "id": player_id,

                "name": player.get(
                    "name",
                    f"Player {player_id}"
                ),

                "position": player.get(
                    "position"
                ),

                "slot": pick["position"],

                "multiplier": pick["multiplier"],

                "captain": pick[
                    "is_captain"
                ],

                "vice_captain": pick[
                    "is_vice_captain"
                ],

                "points": points,

                "effective_points": (
                    points * pick["multiplier"]
                ),
            })

        weekly_data[str(entry_id)] = {

            "entry_id": entry_id,

            "team_name": team[
                "team_name"
            ],

            "manager": team[
                "manager"
            ],

            "players": players,

            "active_chip": picks_data.get(
                "active_chip"
            ),

            "automatic_subs": picks_data.get(
                "automatic_subs",
                []
            ),
        }

    return weekly_data


def clean_match_data(matches):

    cleaned = []

    for match in matches:

        cleaned.append({

            "id": match["id"],

            "event": match["event"],

            "entry_1_entry": match[
                "entry_1_entry"
            ],

            "entry_1_name": match[
                "entry_1_name"
            ],

            "entry_1_player_name": match[
                "entry_1_player_name"
            ],

            "entry_1_points": match[
                "entry_1_points"
            ],

            "entry_1_win": match[
                "entry_1_win"
            ],

            "entry_1_draw": match[
                "entry_1_draw"
            ],

            "entry_1_loss": match[
                "entry_1_loss"
            ],

            "entry_1_total": match[
                "entry_1_total"
            ],

            "entry_2_entry": match[
                "entry_2_entry"
            ],

            "entry_2_name": match[
                "entry_2_name"
            ],

            "entry_2_player_name": match[
                "entry_2_player_name"
            ],

            "entry_2_points": match[
                "entry_2_points"
            ],

            "entry_2_win": match[
                "entry_2_win"
            ],

            "entry_2_draw": match[
                "entry_2_draw"
            ],

            "entry_2_loss": match[
                "entry_2_loss"
            ],

            "entry_2_total": match[
                "entry_2_total"
            ],
        })

    return cleaned


def get_week_matches(matches, gameweek):
    """Return the seven matches belonging to a Gameweek."""

    return [
        match
        for match in matches
        if match["event"] == gameweek
    ]


def build_weekly_summary(matches, gameweek):
    """Create useful statistical information about a Gameweek."""

    week_matches = get_week_matches(matches, gameweek)

    if not week_matches:
        return {
            "gameweek": gameweek,
            "matches_this_week": 0,
        }

    scores = []

    for match in week_matches:
        scores.append(match["entry_1_points"])
        scores.append(match["entry_2_points"])

    highest_score = max(scores)
    lowest_score = min(scores)

    match_records = []

    for match in week_matches:

        score_1 = match["entry_1_points"]
        score_2 = match["entry_2_points"]

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        match_records.append({
            "match_id": match["id"],
            "gameweek": gameweek,

            "team_1": {
                "entry_id": match["entry_1_entry"],
                "team_name": match["entry_1_name"],
                "manager": match["entry_1_player_name"],
                "score": score_1,
                "result": (
                    "win"
                    if score_1 > score_2
                    else "draw"
                    if score_1 == score_2
                    else "loss"
                ),
            },

            "team_2": {
                "entry_id": match["entry_2_entry"],
                "team_name": match["entry_2_name"],
                "manager": match["entry_2_player_name"],
                "score": score_2,
                "result": (
                    "win"
                    if score_2 > score_1
                    else "draw"
                    if score_1 == score_2
                    else "loss"
                ),
            },

            "result": result,
            "margin": abs(score_1 - score_2),
            "total_points": score_1 + score_2,
        })

    highest_scoring_match = max(
        match_records,
        key=lambda match: match["total_points"]
    )

    lowest_scoring_match = min(
        match_records,
        key=lambda match: match["total_points"]
    )

    narrowest_match = min(
        match_records,
        key=lambda match: match["margin"]
    )

    biggest_match = max(
        match_records,
        key=lambda match: match["margin"]
    )

    return {
        "gameweek": gameweek,
        "matches_this_week": len(week_matches),

        "highest_score": highest_score,
        "lowest_score": lowest_score,

        "biggest_margin": biggest_match["margin"],
        "narrowest_margin": narrowest_match["margin"],

        "highest_scoring_match": highest_scoring_match,
        "lowest_scoring_match": lowest_scoring_match,
        "narrowest_match": narrowest_match,
        "biggest_match": biggest_match,
    }


def build_player_analysis(weekly_team_data):
    """
    Create a simplified player-level dataset for the AI report.

    This makes it easy to identify:
    - top performers
    - captain successes
    - captain failures
    - zero-point players
    - bench disasters
    """

    players = []

    for team_data in weekly_team_data.values():

        for player in team_data["players"]:

            players.append({
                "name": player["name"],
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "captain": player["captain"],
                "multiplier": player["multiplier"],
                "slot": player["slot"],
                "points": player["points"],
                "effective_points": player[
                    "effective_points"
                ],
            })

    return players


def build_team_analysis(
    weekly_team_data,
    matches,
    gameweek
):
    """
    Combine match results with player information for each team.
    """

    week_matches = get_week_matches(
        matches,
        gameweek
    )

    analysis = []

    for match in week_matches:

        for side in [1, 2]:

            entry_id = str(
                match[f"entry_{side}_entry"]
            )

            team_data = weekly_team_data.get(
                entry_id
            )

            if not team_data:
                continue

            players = team_data["players"]

            starting_players = [
                player
                for player in players
                if player["slot"] <= 11
            ]

            bench_players = [
                player
                for player in players
                if player["slot"] > 11
            ]

            sorted_players = sorted(
                starting_players,
                key=lambda player:
                player["effective_points"],
                reverse=True
            )

            top_players = sorted_players[:3]

            captain = next(
                (
                    player
                    for player in players
                    if player["captain"]
                ),
                None
            )

            bench_points = sum(
                player["points"]
                for player in bench_players
            )

            starting_points = sum(
                player["effective_points"]
                for player in starting_players
            )

            analysis.append({

                "entry_id": team_data[
                    "entry_id"
                ],

                "team_name": team_data[
                    "team_name"
                ],

                "manager": team_data[
                    "manager"
                ],

                "gameweek": gameweek,

                "score": match[
                    f"entry_{side}_points"
                ],

                "result": (
                    "win"
                    if match[
                        f"entry_{side}_points"
                    ] > match[
                        f"entry_{3 - side}_points"
                    ]
                    else "draw"
                    if match[
                        f"entry_{side}_points"
                    ] == match[
                        f"entry_{3 - side}_points"
                    ]
                    else "loss"
                ),

                "opponent": match[
                    f"entry_{3 - side}_name"
                ],

                "opponent_manager": match[
                    f"entry_{3 - side}_player_name"
                ],

                "opponent_score": match[
                    f"entry_{3 - side}_points"
                ],

                "margin": abs(
                    match[
                        f"entry_{side}_points"
                    ]
                    -
                    match[
                        f"entry_{3 - side}_points"
                    ]
                ),

                "top_players": top_players,

                "captain": captain,

                "bench_points": bench_points,

                "starting_points": starting_points,

                "active_chip": team_data[
                    "active_chip"
                ],

                "automatic_subs": team_data[
                    "automatic_subs"
                ],
            })

    return analysis


def build_player_week_summary(
    weekly_team_data
):
    """
    Produce league-wide player statistics.
    """

    all_players = []

    for team_data in weekly_team_data.values():

        for player in team_data["players"]:

            all_players.append({
                "name": player["name"],
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "points": player["points"],
                "effective_points": player[
                    "effective_points"
                ],
                "captain": player["captain"],
                "slot": player["slot"],
            })

    starting_players = [
        player
        for player in all_players
        if player["slot"] <= 11
    ]

    if starting_players:
        highest_player = max(
            starting_players,
            key=lambda player:
            player["effective_points"]
        )
    else:
        highest_player = None

    captains = [
        player
        for player in all_players
        if player["captain"]
    ]

    best_captain = (
        max(
            captains,
            key=lambda player:
            player["effective_points"]
        )
        if captains
        else None
    )

    worst_captain = (
        min(
            captains,
            key=lambda player:
            player["effective_points"]
        )
        if captains
        else None
    )

    return {
        "highest_starting_player": highest_player,
        "best_captain": best_captain,
        "worst_captain": worst_captain,
    }


def build_weekly_report_data(
    matches,
    weekly_team_data,
    gameweek
):
    """
    Create the complete structured dataset which will eventually
    be handed to the AI report writer.
    """

    summary = build_weekly_summary(
        matches,
        gameweek
    )

    team_analysis = build_team_analysis(
        weekly_team_data,
        matches,
        gameweek
    )

    player_analysis = build_player_analysis(
        weekly_team_data
    )

    player_summary = build_player_week_summary(
        weekly_team_data
    )

    return {
        "report_version": 4,

        "league": {
            "name": "Super 8s",
            "gameweek": gameweek,
            "matches_this_week": len(
                get_week_matches(
                    matches,
                    gameweek
                )
            ),
        },

        "weekly_summary": summary,

        "team_analysis": team_analysis,

        "player_analysis": player_analysis,

        "player_summary": player_summary,
    }


def main():

    print("Retrieving FPL data...")

    existing = load_existing_data()

    matches = get_league_matches()

    print(
        f"Found {len(matches)} H2H matches"
    )

    teams = get_teams_from_matches(
        matches
    )

    print(
        f"Found {len(teams)} teams"
    )

    current_gameweek = (
        get_current_gameweek()
    )

    print(
        f"Current gameweek: "
        f"{current_gameweek}"
    )

    finished_gameweeks = (
        get_finished_gameweeks()
    )

    player_data = get_player_data()

    existing["teams"] = teams

    existing["matches"] = (
        clean_match_data(matches)
    )

    existing["completed_gameweeks"] = (
        finished_gameweeks
    )

    existing["report_version"] = 4

    for gameweek in finished_gameweeks:

        print(
            f"Collecting player data "
            f"for Gameweek {gameweek}..."
        )

        player_points = (
            get_gameweek_player_points(
                gameweek
            )
        )

        weekly_team_data = (
            build_weekly_team_data(
                teams,
                gameweek,
                player_data,
                player_points
            )
        )

        existing[
            "weekly_team_data"
        ][str(gameweek)] = weekly_team_data

        print(
            f"Building report data "
            f"for Gameweek {gameweek}..."
        )

        weekly_report = (
            build_weekly_report_data(
                matches,
                weekly_team_data,
                gameweek
            )
        )

        existing[
            "weekly_reports"
        ][str(gameweek)] = weekly_report

    with DATA_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            existing,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        "Data collection complete and "
        f"saved to {DATA_FILE}"
    )

    print(
        f"Completed gameweeks: "
        f"{len(finished_gameweeks)}"
    )


if __name__ == "__main__":
    main()
