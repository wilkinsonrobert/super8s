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


def get_bootstrap():
    return get_json(f"{API_BASE}/bootstrap-static/")


def get_h2h_matches(league_id):
    url = f"{API_BASE}/leagues-h2h-matches/league/{league_id}/?page=1"
    return get_json(url)


def get_all_h2h_matches(league_id):
    """Retrieve all pages of H2H matches."""
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


def build_player_lookup(bootstrap):
    return {
        player["id"]: {
            "name": f"{player['first_name']} {player['second_name']}",
            "team": player["team"],
            "position": player["element_type"],
        }
        for player in bootstrap["elements"]
    }


def main():
    print("Retrieving FPL data...")

    bootstrap = get_bootstrap()
    matches = get_all_h2h_matches(LEAGUE_ID)

    current_gameweek = None

    for event in bootstrap["events"]:
        if event["is_current"]:
            current_gameweek = event["id"]
            break

    if current_gameweek is None:
        for event in bootstrap["events"]:
            if event["is_next"]:
                current_gameweek = event["id"]
                break

    player_lookup = build_player_lookup(bootstrap)

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

    output = {
        "league_id": LEAGUE_ID,
        "current_gameweek": current_gameweek,
        "number_of_teams": len(teams),
        "teams": list(teams.values()),
        "matches": matches,
        "player_count": len(player_lookup),
    }

    output_path = Path("gameweek_data.json")

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"Found {len(teams)} teams")
    print(f"Found {len(matches)} H2H matches")
    print(f"Current gameweek: {current_gameweek}")
    print(f"Saved data to {output_path}")


if __name__ == "__main__":
    main()
