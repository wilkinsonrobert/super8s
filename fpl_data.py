import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from openai import OpenAI


LEAGUE_ID = 54930
DATA_FILE = Path("gameweek_data.json")
REPORT_FILE = Path("report_data.json")

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
        "weekly_reports": {}
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

    finished = get_finished_gameweeks()

    if finished:
        return max(finished)

    return None


def get_finished_gameweeks():
    data = get_json("bootstrap-static/")

    now = datetime.now(timezone.utc)

    completed = []

    for event in data["events"]:

        gameweek = event["id"]

        matches = [
            fixture
            for fixture in get_json(
                f"fixtures/?event={gameweek}"
            )
            if fixture.get("kickoff_time")
        ]

        if not matches:
            continue

        final_kickoff = max(
            datetime.fromisoformat(
                fixture["kickoff_time"].replace(
                    "Z",
                    "+00:00"
                )
            )
            for fixture in matches
        )

        available_from = (
            final_kickoff + timedelta(hours=12)
        )

        if now >= available_from:
            completed.append(gameweek)

    return completed


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


def generate_ai_report(
    gameweek,
    report_data
):
    api_key = os.environ.get(
        "OPENAI_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not available."
        )

    client = OpenAI(
        api_key=api_key
    )

    system_prompt = """
You are the writer of the weekly Super 8s Fantasy Premier League
report.

Super 8s is a private 14-manager head-to-head FPL league.

Write in a dry, witty, slightly irreverent British sports-journalism
style. The humour should be understated and intelligent rather than
forced.

You are writing about fantasy football managers, not professional
footballers. Team names and manager names should be used naturally.

IMPORTANT FACTUAL RULES:

1. Only use information contained in the supplied data.
2. Never invent a score, player, fixture, result, league position or
   statistical record.
3. Never invent a real-life football event.
4. Do not claim that a player scored, assisted, kept a clean sheet or
   did anything else in a real-life match unless that information is
   actually present in the supplied data.
5. If there is insufficient information to make a real-life football
   reference, simply don't make one.
6. Do not repeat the same joke excessively.
7. Avoid generic filler.

The report must contain:

- A strong weekly headline based on what actually happened.
- A short introduction.
- A mini match report for EVERY match played that gameweek.
- Where appropriate, mention weekly records such as the highest score,
  lowest score, biggest winning margin, narrowest win or highest-scoring
  match.
- Four funny weekly awards.
- Commentary on the current league table.
- A preview of the following gameweek using ONLY the supplied actual
  fixtures. Pick two or three interesting fixtures.
- A short closing paragraph.

For match reports, identify important players and captaincy decisions
where useful. A particularly good or bad captaincy decision is worth
mentioning.

The weekly awards should be different where possible and should feel
specific to what happened that week.

Return ONLY valid JSON with exactly this structure:

{
  "headline": "...",
  "introduction": "...",
  "matches": [
    {
      "title": "...",
      "text": "..."
    }
  ],
  "awards": [
    {
      "award": "...",
      "winner": "...",
      "text": "..."
    }
  ],
  "table_commentary": "...",
  "preview": [
    {
      "fixture": "...",
      "text": "..."
    }
  ],
  "closing": "..."
}

There must be one match object for every match supplied.
"""


    user_prompt = f"""
Generate the Super 8s report for Gameweek {gameweek}.

Here is the factual report data:

{json.dumps(
    report_data,
    indent=2,
    ensure_ascii=False
)}

Remember:
- Use only the supplied information.
- Do not invent real-life football events.
- Cover every match.
- Use the actual next-gameweek fixtures for the preview.
- Keep the tone dry, witty and sports-journalistic.
"""

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=system_prompt,
        input=user_prompt
    )

    text = response.output_text.strip()

    if text.startswith("```"):
        text = text.replace(
            "```json",
            ""
        ).replace(
            "```",
            ""
        ).strip()

    return json.loads(text)


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

    if REPORT_FILE.exists():

        print(
            "Generating AI reports..."
        )

        with REPORT_FILE.open(
            "r",
            encoding="utf-8"
        ) as file:
            report_data = json.load(file)

        gameweeks = report_data.get(
            "gameweeks",
            {}
        )

        for gameweek in finished_gameweeks:

            gameweek_key = str(gameweek)

            if gameweek_key not in gameweeks:
                continue

            print(
                f"Generating AI report for "
                f"Gameweek {gameweek}..."
            )

            try:

                ai_report = generate_ai_report(
                    gameweek,
                    gameweeks[gameweek_key]
                )

                existing[
                    "weekly_reports"
                ][gameweek_key] = ai_report

                print(
                    f"AI report generated for "
                    f"Gameweek {gameweek}"
                )

            except Exception as error:

                print(
                    f"AI report failed for "
                    f"Gameweek {gameweek}: {error}"
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
        "Data collection and report generation "
        "complete."
    )


if __name__ == "__main__":
    main()
