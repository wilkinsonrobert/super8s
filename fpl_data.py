import json
import urllib.request
from pathlib import Path

LEAGUE_ID = 54930
API_BASE = "https://fantasy.premierleague.com/api"


def get_json(url):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Super8s-FPL/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_all_h2h_matches(league_id):
    """Retrieve every H2H match in the league."""
    all_matches = []
    page = 1

    while True:
        url = f"{API_BASE}/leagues-h2h-matches/league/{league_id}/?page={page}"
        data = get_json(url)

        all_matches.extend(data.get("results", []))

        if not data.get("has_next"):
            break

        page += 1

    return all_matches


def get_bootstrap():
    return get_json(f"{API_BASE}/bootstrap-static/")


def get_manager_history(entry_id):
    """Retrieve a manager's gameweek history."""
    return get_json(f"{API_BASE}/entry/{entry_id}/history/")


def get_manager_picks(entry_id, gameweek):
    """Retrieve a manager's team for a particular gameweek."""
    return get_json(
        f"{API_BASE}/entry/{entry_id}/event/{gameweek}/picks/"
    )


def build_player_lookup(bootstrap):
    """Convert player IDs into useful player information."""
    return {
        player["id"]: {
            "name": f"{player['first_name']} {player['second_name']}",
            "team_id": player["team"],
            "position": player["element_type"],
        }
        for player in bootstrap["elements"]
    }


def get_current_gameweek(bootstrap):
    """Find the current or next FPL gameweek."""
    for event in bootstrap["events"]:
        if event["is_current"]:
            return event["id"]

    for event in bootstrap["events"]:
        if event["is_next"]:
            return event["id"]

    return None


def build_team_list(matches):
    """Build the list of Super 8s managers."""
    teams = {}

    for match in matches:
        for side in ("entry_1", "entry_2"):
            entry_id = match[f"{side}_entry"]

            if entry_id not in teams:
                teams[entry_id] = {
                    "entry_id": entry_id,
                    "team_name": match[f"{side}_name"],
                    "manager": match[f"{side}_player_name"],
                }

    return list(teams.values())


def get_completed_gameweeks(bootstrap):
    """Return gameweeks that have finished."""
    completed = []

    for event in bootstrap["events"]:
        if event["finished"]:
            completed.append(event["id"])

    return completed


def build_weekly_team_data(teams, completed_gameweeks, player_lookup):
    """Retrieve every manager's team for every completed gameweek."""
    weekly_data = {}

    for gameweek in completed_gameweeks:
        print(f"Collecting teams for Gameweek {gameweek}...")

        weekly_data[str(gameweek)] = {}

        for team in teams:
            entry_id = team["entry_id"]

            try:
                picks_data = get_manager_picks(entry_id, gameweek)
            except Exception as error:
                print(
                    f"Could not retrieve {team['team_name']} "
                    f"GW{gameweek}: {error}"
                )
                continue

            players = []

            for pick in picks_data.get("picks", []):
                player_id = pick["element"]
                player = player_lookup.get(player_id, {})

                players.append({
                    "player_id": player_id,
                    "name": player.get("name", f"Player {player_id}"),
                    "position": player.get("position"),
                    "slot": pick["position"],
                    "multiplier": pick["multiplier"],
                    "captain": pick["is_captain"],
                    "vice_captain": pick["is_vice_captain"],
                })

            weekly_data[str(gameweek)][str(entry_id)] = {
                "team_name": team["team_name"],
                "manager": team["manager"],
                "players": players,
                "active_chip": picks_data.get("active_chip"),
                "automatic_subs": picks_data.get("automatic_subs", []),
            }

    return weekly_data


def main():
    print("===================================")
    print("SUPER 8s FPL DATA COLLECTION")
    print("===================================")

    bootstrap = get_bootstrap()
    matches = get_all_h2h_matches(LEAGUE_ID)

    current_gameweek = get_current_gameweek(bootstrap)
    completed_gameweeks = get_completed_gameweeks(bootstrap)

    player_lookup = build_player_lookup(bootstrap)
    teams = build_team_list(matches)

    print(f"Found {len(teams)} Super 8s teams")
    print(f"Found {len(matches)} H2H matches")
    print(f"Current gameweek: {current_gameweek}")
    print(f"Completed gameweeks: {completed_gameweeks}")

    weekly_team_data = build_weekly_team_data(
        teams,
        completed_gameweeks,
        player_lookup
    )

    output = {
        "league_id": LEAGUE_ID,
        "league_name": "Super 8s",
        "current_gameweek": current_gameweek,
        "completed_gameweeks": completed_gameweeks,
        "number_of_teams": len(teams),
        "teams": teams,
        "matches": matches,
        "weekly_team_data": weekly_team_data,
    }

    output_path = Path("gameweek_data.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print("===================================")
    print("DATA COLLECTION COMPLETE")
    print(f"Saved to {output_path}")
    print("===================================")


if __name__ == "__main__":
    main()
