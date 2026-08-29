import json
import requests
from pathlib import Path


LEAGUE_ID = 54930
DATA_FILE = Path("gameweek_data.json")

BASE_URL = "https://fantasy.premierleague.com/api"


def get_json(endpoint):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
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
    }


def get_league_teams():
    data = get_json(f"leagues-classic/{LEAGUE_ID}/standings/")

    teams = []

    for result in data["standings"]["results"]:
        teams.append({
            "entry_id": result["entry"],
            "team_name": result["entry_name"],
            "manager": result["player_name"],
        })

    return teams


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


def get_current_gameweek():
    data = get_json("bootstrap-static/")

    current_event = None

    for event in data["events"]:
        if event["is_current"]:
            current_event = event["id"]
            break

    if current_event is None:
        for event in data["events"]:
            if event["finished"]:
                current_event = event["id"]

    return current_event


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
    """
    Get individual player points for a gameweek.

    The live endpoint gives us the actual points scored
    by every player in that gameweek.
    """

    data = get_json(
        f"event/{gameweek}/live/"
    )

    points = {}

    for player in data.get("elements", []):
        points[player["id"]] = player["stats"]["total_points"]

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
                "vice_captain": pick[
                    "is_vice_captain"
                ],
                "points": player_points.get(
                    player_id,
                    0
                ),
                "effective_points": (
                    player_points.get(
                        player_id,
                        0
                    ) * pick["multiplier"]
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


def main():

    print("Retrieving FPL data...")

    existing = load_existing_data()

    teams = get_league_teams()

    print(
        f"Found {len(teams)} teams"
    )

    matches = get_league_matches()

    print(
        f"Found {len(matches)} H2H matches"
    )

    current_gameweek = get_current_gameweek()

    finished_gameweeks = get_finished_gameweeks()

    print(
        f"Current gameweek: {current_gameweek}"
    )

    player_data = get_player_data()

    existing["teams"] = teams
    existing["matches"] = clean_match_data(
        matches
    )
    existing["completed_gameweeks"] = (
        finished_gameweeks
    )

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

        existing["weekly_team_data"][
            str(gameweek)
        ] = weekly_team_data

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
