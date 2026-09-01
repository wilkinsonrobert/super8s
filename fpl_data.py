import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


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
                return json.load(file)
        except Exception:
            pass

    return {
        "league_id": LEAGUE_ID,
        "league_name": "Super 8s",
        "teams": [],
        "matches": [],
        "weekly_team_data": {},
        "completed_gameweeks": [],
        "weekly_reports": {},
        "processed_gameweeks": []
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
                "captain": pick["is_captain"],
                "vice_captain": pick["is_vice_captain"],
                "points": points,
                "effective_points": (
                    points * pick["multiplier"]
                ),
            })

        weekly_data[str(entry_id)] = {
            "entry_id": entry_id,
            "team_name": team["team_name"],
            "manager": team["manager"],
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

            "entry_1_entry": match["entry_1_entry"],
            "entry_1_name": match["entry_1_name"],
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

            "entry_2_entry": match["entry_2_entry"],
            "entry_2_name": match["entry_2_name"],
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


def get_gameweek_final_kickoffs(gameweek):
    """
    Get all Premier League fixture kick-off times for a gameweek.
    The gameweek is eligible for processing 12 hours after
    the latest kick-off time.
    """

    data = get_json(
        f"fixtures/?event={gameweek}"
    )

    kickoffs = []

    for fixture in data:
        kickoff = fixture.get("kickoff_time")

        if kickoff:
            try:
                kickoffs.append(
                    datetime.fromisoformat(
                        kickoff.replace("Z", "+00:00")
                    )
                )
            except ValueError:
                continue

    return kickoffs


def gameweek_is_eligible(gameweek):
    """
    A gameweek becomes eligible 12 hours after the
    final Premier League fixture kicks off.
    """

    kickoffs = get_gameweek_final_kickoffs(gameweek)

    if not kickoffs:
        print(
            f"No fixture kick-off data available for GW{gameweek}."
        )
        return False

    final_kickoff = max(kickoffs)
    available_from = (
        final_kickoff + timedelta(hours=12)
    )

    now = datetime.now(timezone.utc)

    print(
        f"GW{gameweek} final kick-off: "
        f"{final_kickoff.isoformat()}"
    )

    print(
        f"GW{gameweek} eligible from: "
        f"{available_from.isoformat()}"
    )

    print(
        f"Current time: "
        f"{now.isoformat()}"
    )

    return now >= available_from


def h2h_data_available(matches, gameweek, teams):
    """
    Confirm that every Super 8s manager has a completed
    H2H fixture for this gameweek.
    """

    gameweek_matches = [
        match
        for match in matches
        if int(match["event"]) == int(gameweek)
    ]

    expected_matches = len(teams) // 2

    if len(gameweek_matches) < expected_matches:
        print(
            f"GW{gameweek} H2H data incomplete: "
            f"found {len(gameweek_matches)} matches, "
            f"expected {expected_matches}."
        )
        return False

    for match in gameweek_matches:
        if (
            match.get("entry_1_points") is None
            or match.get("entry_2_points") is None
        ):
            print(
                f"GW{gameweek} H2H data is not fully populated."
            )
            return False

    print(
        f"GW{gameweek} H2H data is available."
    )

    return True


def build_league_table(matches, gameweek):
    teams = {}

    for match in matches:

        if int(match["event"]) > int(gameweek):
            continue

        entry_1 = match["entry_1_entry"]
        entry_2 = match["entry_2_entry"]

        if entry_1 not in teams:
            teams[entry_1] = {
                "entry_id": entry_1,
                "team_name": match["entry_1_name"],
                "manager": match["entry_1_player_name"],
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0,
                "scored": 0,
            }

        if entry_2 not in teams:
            teams[entry_2] = {
                "entry_id": entry_2,
                "team_name": match["entry_2_name"],
                "manager": match["entry_2_player_name"],
                "played": 0,
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "points": 0,
                "scored": 0,
            }

        home = teams[entry_1]
        away = teams[entry_2]

        home["played"] += 1
        away["played"] += 1

        home["scored"] += match["entry_1_points"]
        away["scored"] += match["entry_2_points"]

        home["points"] += match["entry_1_total"]
        away["points"] += match["entry_2_total"]

        if match["entry_1_win"]:
            home["wins"] += 1
            away["losses"] += 1

        elif match["entry_2_win"]:
            away["wins"] += 1
            home["losses"] += 1

        else:
            home["draws"] += 1
            away["draws"] += 1

    table = list(teams.values())

    table.sort(
        key=lambda team: (
            -team["points"],
            -team["scored"]
        )
    )

    return table


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

    current_gameweek = get_current_gameweek()

    print(
        f"Current gameweek: {current_gameweek}"
    )

    finished_gameweeks = get_finished_gameweeks()

    player_data = get_player_data()

    existing["teams"] = teams

    existing["matches"] = clean_match_data(
        matches
    )

    existing["completed_gameweeks"] = (
        finished_gameweeks
    )

    if "weekly_team_data" not in existing:
        existing["weekly_team_data"] = {}

    if "weekly_reports" not in existing:
        existing["weekly_reports"] = {}

    if "processed_gameweeks" not in existing:
        existing["processed_gameweeks"] = []

    for gameweek in finished_gameweeks:

        print(
            f"Collecting player data for "
            f"Gameweek {gameweek}..."
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
        "Checking whether any gameweek is ready "
        "for an AI report..."
    )

    for gameweek in finished_gameweeks:

        gameweek_key = str(gameweek)

        if gameweek_key in existing["processed_gameweeks"]:
            print(
                f"GW{gameweek} already processed. "
                f"No AI report required."
            )
            continue

        if not gameweek_is_eligible(gameweek):
            print(
                f"GW{gameweek} is not yet eligible "
                f"for processing."
            )
            continue

        if not h2h_data_available(
            matches,
            gameweek,
            teams
        ):
            print(
                f"GW{gameweek} is eligible by time, "
                f"but H2H data is not yet available."
            )
            continue

        print(
            f"GW{gameweek} is ready for AI report generation."
        )

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
        "FPL data collection complete."
    )


if __name__ == "__main__":
    main()
