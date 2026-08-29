```python
import json
import requests
from pathlib import Path


LEAGUE_ID = 54930
DATA_FILE = Path("gameweek_data.json")

BASE_URL = "https://fantasy.premierleague.com/api"


def get_json(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, timeout=30)

    if response.status_code != 200:
        raise RuntimeError(
            f"FPL API returned {response.status_code} for {url}"
        )

    return response.json()


def load_existing_data():
    if DATA_FILE.exists():
        try:
            with DATA_FILE.open("r", encoding="utf-8") as file:
                existing = json.load(file)

            # Make sure sections added by newer versions exist
            existing.setdefault("league_id", LEAGUE_ID)
            existing.setdefault("league_name", "Super 8s")
            existing.setdefault("teams", [])
            existing.setdefault("matches", [])
            existing.setdefault("weekly_team_data", {})
            existing.setdefault("weekly_reports", {})
            existing.setdefault("completed_gameweeks", [])

            return existing

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


def build_weekly_report(
    gameweek,
    matches,
    weekly_team_data
):

    week_matches = [
        match
        for match in matches
        if match["event"] == gameweek
    ]

    if not week_matches:
        return {
            "report_version": 3,
            "league": {
                "name": "Super 8s",
                "gameweek": gameweek,
                "matches_this_week": 0,
            },
            "weekly_summary": {},
            "player_analysis": [],
        }

    scores = []

    match_details = []

    for match in week_matches:

        score_1 = match["entry_1_points"]
        score_2 = match["entry_2_points"]

        scores.extend([score_1, score_2])

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        margin = abs(score_1 - score_2)
        total_points = score_1 + score_2

        match_details.append({
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
                    else "loss"
                    if score_1 < score_2
                    else "draw"
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
                    else "loss"
                    if score_2 < score_1
                    else "draw"
                ),
            },
            "result": result,
            "margin": margin,
            "total_points": total_points,
        })

    highest_score = max(scores)
    lowest_score = min(scores)

    highest_scoring_match = max(
        match_details,
        key=lambda match: match["total_points"]
    )

    lowest_scoring_match = min(
        match_details,
        key=lambda match: match["total_points"]
    )

    narrowest_match = min(
        match_details,
        key=lambda match: match["margin"]
    )

    biggest_match = max(
        match_details,
        key=lambda match: match["margin"]
    )

    player_analysis = []

    for team_data in weekly_team_data.values():

        for player in team_data["players"]:

            player_analysis.append({
                "id": player["id"],
                "name": player["name"],
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "position": player["position"],
                "slot": player["slot"],
                "multiplier": player["multiplier"],
                "captain": player["captain"],
                "vice_captain": player["vice_captain"],
                "points": player["points"],
                "effective_points": player["effective_points"],
            })

    return {
        "report_version": 3,

        "league": {
            "name": "Super 8s",
            "gameweek": gameweek,
            "matches_this_week": len(week_matches),
        },

        "weekly_summary": {
            "highest_score": highest_score,
            "lowest_score": lowest_score,
            "biggest_margin": biggest_match["margin"],
            "narrowest_margin": narrowest_match["margin"],

            "highest_scoring_match":
                highest_scoring_match,

            "lowest_scoring_match":
                lowest_scoring_match,

            "narrowest_match":
                narrowest_match,

            "biggest_match":
                biggest_match,
        },

        "player_analysis": player_analysis,
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

    # Make absolutely sure the new section exists
    if "weekly_reports" not in existing:
        existing["weekly_reports"] = {}

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

        weekly_report = build_weekly_report(
            gameweek,
            existing["matches"],
            weekly_team_data
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


if __name__ == "__main__":
    main()
```
