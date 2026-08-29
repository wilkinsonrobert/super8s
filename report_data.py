import json
import os
import requests
from pathlib import Path


DATA_FILE = Path("gameweek_data.json")
REPORT_FILE = Path("report_data.json")

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

OPENAI_URL = "https://api.openai.com/v1/responses"
OPENAI_MODEL = "gpt-5.6-luna"


def load_data():
    with DATA_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_existing_reports():
    if not REPORT_FILE.exists():
        return {}

    try:
        with REPORT_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def get_week_matches(data, gameweek):
    return [
        match
        for match in data.get("matches", [])
        if int(match["event"]) == int(gameweek)
    ]


def get_next_week_matches(data, gameweek):
    next_gameweek = int(gameweek) + 1

    return [
        match
        for match in data.get("matches", [])
        if int(match["event"]) == next_gameweek
    ]


def get_week_players(data, gameweek):
    weekly = data.get(
        "weekly_team_data",
        {}
    ).get(
        str(gameweek),
        {}
    )

    players = []

    for team_data in weekly.values():
        for player in team_data.get("players", []):
            players.append({
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "player": player["name"],
                "points": player["points"],
                "effective_points": player["effective_points"],
                "captain": player["captain"],
                "multiplier": player["multiplier"]
            })

    return players


def get_team_data(data, gameweek):
    return data.get(
        "weekly_team_data",
        {}
    ).get(
        str(gameweek),
        {}
    )


def calculate_weekly_statistics(matches):

    if not matches:
        return {
            "highest_score": None,
            "lowest_score": None,
            "biggest_margin": None,
            "narrowest_margin": None,
            "highest_scoring_match": None,
            "lowest_scoring_match": None,
            "biggest_match": None,
            "narrowest_match": None
        }

    scores = []
    match_summaries = []

    for match in matches:

        score_1 = int(match["entry_1_points"])
        score_2 = int(match["entry_2_points"])

        margin = abs(score_1 - score_2)

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        summary = {
            "match_id": match["id"],
            "gameweek": match["event"],
            "team_1": {
                "entry_id": match["entry_1_entry"],
                "team_name": match["entry_1_name"],
                "manager": match["entry_1_player_name"],
                "score": score_1,
                "result": (
                    "win"
                    if result == "home_win"
                    else "loss"
                    if result == "away_win"
                    else "draw"
                )
            },
            "team_2": {
                "entry_id": match["entry_2_entry"],
                "team_name": match["entry_2_name"],
                "manager": match["entry_2_player_name"],
                "score": score_2,
                "result": (
                    "win"
                    if result == "away_win"
                    else "loss"
                    if result == "home_win"
                    else "draw"
                )
            },
            "result": result,
            "margin": margin,
            "total_points": score_1 + score_2
        }

        match_summaries.append(summary)

        scores.append(score_1)
        scores.append(score_2)

    highest_score = max(scores)
    lowest_score = min(scores)

    biggest_margin = max(
        match["margin"]
        for match in match_summaries
    )

    narrowest_margin = min(
        match["margin"]
        for match in match_summaries
    )

    highest_scoring_match = max(
        match_summaries,
        key=lambda match: match["total_points"]
    )

    lowest_scoring_match = min(
        match_summaries,
        key=lambda match: match["total_points"]
    )

    biggest_match = max(
        match_summaries,
        key=lambda match: match["margin"]
    )

    narrowest_match = min(
        match_summaries,
        key=lambda match: match["margin"]
    )

    return {
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "biggest_margin": biggest_margin,
        "narrowest_margin": narrowest_margin,
        "highest_scoring_match": highest_scoring_match,
        "lowest_scoring_match": lowest_scoring_match,
        "biggest_match": biggest_match,
        "narrowest_match": narrowest_match
    }


def calculate_table(matches, gameweek):

    teams = {}

    for match in matches:

        if int(match["event"]) > int(gameweek):
            continue

        for side in [1, 2]:

            entry_id = match[
                f"entry_{side}_entry"
            ]

            if entry_id not in teams:

                teams[entry_id] = {
                    "entry_id": entry_id,
                    "team_name": match[
                        f"entry_{side}_name"
                    ],
                    "manager": match[
                        f"entry_{side}_player_name"
                    ],
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "points": 0,
                    "scored": 0,
                    "conceded": 0
                }

        home = teams[
            match["entry_1_entry"]
        ]

        away = teams[
            match["entry_2_entry"]
        ]

        home_score = int(
            match["entry_1_points"]
        )

        away_score = int(
            match["entry_2_points"]
        )

        home["played"] += 1
        away["played"] += 1

        home["scored"] += home_score
        home["conceded"] += away_score

        away["scored"] += away_score
        away["conceded"] += home_score

        if home_score > away_score:

            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1

        elif away_score > home_score:

            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1

        else:

            home["draws"] += 1
            away["draws"] += 1

            home["points"] += 1
            away["points"] += 1

    table = sorted(
        teams.values(),
        key=lambda team: (
            -team["points"],
            -(
                team["scored"] -
                team["conceded"]
            ),
            -team["scored"],
            team["team_name"].lower()
        )
    )

    for position, team in enumerate(
        table,
        start=1
    ):

        team["position"] = position

        team["goal_difference"] = (
            team["scored"] -
            team["conceded"]
        )

    return table


def calculate_movement(matches, gameweek):

    gameweek = int(gameweek)

    current = calculate_table(
        matches,
        gameweek
    )

    if gameweek <= 1:

        return {
            team["entry_id"]: {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }
            for team in current
        }

    previous = calculate_table(
        matches,
        gameweek - 1
    )

    previous_positions = {
        team["entry_id"]: team["position"]
        for team in previous
    }

    movement = {}

    for team in current:

        entry_id = team["entry_id"]

        current_position = team["position"]

        previous_position = previous_positions.get(
            entry_id
        )

        if previous_position is None:

            movement[entry_id] = {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }

        elif current_position < previous_position:

            movement[entry_id] = {
                "direction": "up",
                "amount": (
                    previous_position -
                    current_position
                ),
                "previous_position": previous_position
            }

        elif current_position > previous_position:

            movement[entry_id] = {
                "direction": "down",
                "amount": (
                    current_position -
                    previous_position
                ),
                "previous_position": previous_position
            }

        else:

            movement[entry_id] = {
                "direction": "same",
                "amount": 0,
                "previous_position": previous_position
            }

    return movement


def build_structured_report_data(data, gameweek):

    matches = data.get(
        "matches",
        []
    )

    week_matches = get_week_matches(
        data,
        gameweek
    )

    next_week_matches = get_next_week_matches(
        data,
        gameweek
    )

    players = get_week_players(
        data,
        gameweek
    )

    team_data = get_team_data(
        data,
        gameweek
    )

    table = calculate_table(
        matches,
        gameweek
    )

    movement = calculate_movement(
        matches,
        gameweek
    )

    statistics = calculate_weekly_statistics(
        week_matches
    )

    match_data = []

    for match in week_matches:

        score_1 = int(
            match["entry_1_points"]
        )

        score_2 = int(
            match["entry_2_points"]
        )

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        team_1_players = team_data.get(
            str(match["entry_1_entry"]),
            {}
        ).get(
            "players",
            []
        )

        team_2_players = team_data.get(
            str(match["entry_2_entry"]),
            {}
        ).get(
            "players",
            []
        )

        match_data.append({
            "match_id": match["id"],
            "team_1": {
                "entry_id": match["entry_1_entry"],
                "team_name": match["entry_1_name"],
                "manager": match["entry_1_player_name"],
                "score": score_1,
                "players": team_1_players
            },
            "team_2": {
                "entry_id": match["entry_2_entry"],
                "team_name": match["entry_2_name"],
                "manager": match["entry_2_player_name"],
                "score": score_2,
                "players": team_2_players
            },
            "result": result,
            "margin": abs(score_1 - score_2)
        })

    next_matches = []

    for match in next_week_matches:

        next_matches.append({
            "match_id": match["id"],
            "team_1": {
                "entry_id": match["entry_1_entry"],
                "team_name": match["entry_1_name"],
                "manager": match["entry_1_player_name"]
            },
            "team_2": {
                "entry_id": match["entry_2_entry"],
                "team_name": match["entry_2_name"],
                "manager": match["entry_2_player_name"]
            }
        })

    table_with_movement = []

    for team in table:

        team_copy = dict(team)

        team_copy["movement"] = movement.get(
            team["entry_id"],
            {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }
        )

        table_with_movement.append(
            team_copy
        )

    return {
        "gameweek": gameweek,
        "weekly_statistics": statistics,
        "matches": match_data,
        "players": players,
        "league_table": table_with_movement,
        "next_gameweek_matches": next_matches
    }


def generate_ai_report(
    structured_data,
    gameweek
):

    if not OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not available."
        )

    prompt = f"""
You are the writer of the weekly report for a private Fantasy Premier League
head-to-head league called Super 8s.

This is Gameweek {gameweek}.

Write a funny, sharp, slightly irreverent but intelligent weekly report.
It should feel like a sports website written for people who know each other,
rather than generic AI sports commentary.

IMPORTANT:
- Use ONLY the FPL data supplied below for league facts and player points.
- Do not invent scores, players, managers or fixtures.
- You may use web search to check real-life Premier League events involving
  players mentioned in the data.
- Where a real-life event genuinely explains an important fantasy result,
  mention it.
- Do not force a real-life reference into every match.
- Never claim a player scored, assisted, kept a clean sheet or did anything
  else in real life unless you can verify it.
- Make the individual match reports genuinely different from one another.
- Mention relevant weekly statistics naturally in the match reports.
- Identify the biggest win, closest match, highest score and/or lowest score
  where appropriate.
- Be amusing without becoming ridiculous.
- Do not use emojis.
- Do not use markdown.
- Keep each match report around 70-120 words.
- The introduction should be 2-4 sentences.
- Provide 3-5 funny awards.
- The preview should identify 2-3 interesting fixtures from the following
  gameweek, based on the current league position and/or recent results.
- If there are no following fixtures, say so rather than inventing them.

Return ONLY valid JSON matching this exact structure:

{{
  "headline": "string",
  "introduction": "string",
  "matches": [
    {{
      "title": "Team 1 00–00 Team 2",
      "text": "string"
    }}
  ],
  "awards": [
    {{
      "award": "string",
      "winner": "string",
      "text": "string"
    }}
  ],
  "table_commentary": "string",
  "preview": [
    {{
      "fixture": "Team 1 v Team 2",
      "text": "string"
    }}
  ],
  "closing": "string"
}}

Here is the structured Super 8s data:

{json.dumps(structured_data, ensure_ascii=False, indent=2)}
"""

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "tools": [
            {
                "type": "web_search"
            }
        ],
        "input": prompt
    }

    response = requests.post(
        OPENAI_URL,
        headers=headers,
        json=payload,
        timeout=180
    )

    if response.status_code != 200:

        raise RuntimeError(
            "OpenAI API returned "
            f"{response.status_code}: "
            f"{response.text[:1000]}"
        )

    result = response.json()

    text = extract_response_text(result)

    if not text:
        raise RuntimeError(
            "OpenAI returned no text output."
        )

    text = clean_json_text(text)

    try:
        report = json.loads(text)
    except json.JSONDecodeError as error:

        raise RuntimeError(
            "OpenAI returned invalid JSON: "
            f"{error}\n\n{text[:2000]}"
        )

    validate_ai_report(
        report,
        structured_data
    )

    return report


def extract_response_text(response):

    if response.get("output_text"):
        return response["output_text"]

    pieces = []

    for item in response.get("output", []):

        for content in item.get("content", []):

            if content.get("type") == "output_text":

                text = content.get("text")

                if text:
                    pieces.append(text)

    return "\n".join(pieces)


def clean_json_text(text):

    text = text.strip()

    if text.startswith("```json"):
        text = text[7:]

    elif text.startswith("```"):
        text = text[3:]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def validate_ai_report(report, structured_data):

    required = [
        "headline",
        "introduction",
        "matches",
        "awards",
        "table_commentary",
        "preview",
        "closing"
    ]

    for key in required:

        if key not in report:
            raise RuntimeError(
                f"AI report missing required field: {key}"
            )

    expected_matches = len(
        structured_data["matches"]
    )

    if len(report["matches"]) != expected_matches:

        raise RuntimeError(
            "AI report contains "
            f"{len(report['matches'])} match reports "
            f"but there are {expected_matches} matches."
        )


def main():

    print("Reading Super 8s data...")

    data = load_data()

    completed_gameweeks = data.get(
        "completed_gameweeks",
        []
    )

    print(
        f"Found {len(completed_gameweeks)} "
        f"completed gameweeks"
    )

    existing = load_existing_reports()

    existing_ai_reports = existing.get(
        "weekly_reports",
        {}
    )

    structured_reports = {}

    ai_reports = {}

    for gameweek in completed_gameweeks:

        print(
            f"Building report data for "
            f"Gameweek {gameweek}..."
        )

        structured = build_structured_report_data(
            data,
            gameweek
        )

        structured_reports[str(gameweek)] = structured

        print(
            f"Generating AI report for "
            f"Gameweek {gameweek}..."
        )

        try:

            ai_report = generate_ai_report(
                structured,
                gameweek
            )

            ai_reports[str(gameweek)] = ai_report

            print(
                f"AI report generated for "
                f"Gameweek {gameweek}"
            )

        except Exception as error:

            print(
                f"WARNING: Could not generate AI "
                f"report for Gameweek {gameweek}: "
                f"{error}"
            )

            previous_report = existing_ai_reports.get(
                str(gameweek)
            )

            if previous_report:

                print(
                    f"Keeping existing AI report "
                    f"for Gameweek {gameweek}"
                )

                ai_reports[str(gameweek)] = (
                    previous_report
                )

    output = {
        "league": {
            "id": data.get("league_id"),
            "name": data.get(
                "league_name",
                "Super 8s"
            )
        },
        "gameweeks": structured_reports,
        "weekly_reports": ai_reports
    }

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Report data saved to {REPORT_FILE}"
    )

    print(
        f"AI reports available for: "
        f"{', '.join(ai_reports.keys())}"
    )


if __name__ == "__main__":
    main()        str(gameweek),
        {}
    )

    players = []

    for team_data in weekly.values():
        for player in team_data.get("players", []):
            players.append({
                "team_name": team_data["team_name"],
                "manager": team_data["manager"],
                "player": player["name"],
                "points": player["points"],
                "effective_points": player[
                    "effective_points"
                ],
                "captain": player["captain"],
                "multiplier": player["multiplier"]
            })

    return players


def get_team_data(data, gameweek):
    return data.get(
        "weekly_team_data",
        {}
    ).get(
        str(gameweek),
        {}
    )


def calculate_weekly_statistics(matches):
    if not matches:
        return {
            "highest_score": None,
            "lowest_score": None,
            "biggest_margin": None,
            "narrowest_margin": None,
            "highest_scoring_match": None,
            "lowest_scoring_match": None,
            "biggest_match": None,
            "narrowest_match": None
        }

    scores = []

    match_summaries = []

    for match in matches:
        score_1 = int(match["entry_1_points"])
        score_2 = int(match["entry_2_points"])

        margin = abs(score_1 - score_2)

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        summary = {
            "match_id": match["id"],
            "gameweek": match["event"],
            "team_1": {
                "entry_id": match["entry_1_entry"],
                "team_name": match["entry_1_name"],
                "manager": match[
                    "entry_1_player_name"
                ],
                "score": score_1,
                "result": (
                    "win"
                    if result == "home_win"
                    else "loss"
                    if result == "away_win"
                    else "draw"
                )
            },
            "team_2": {
                "entry_id": match["entry_2_entry"],
                "team_name": match["entry_2_name"],
                "manager": match[
                    "entry_2_player_name"
                ],
                "score": score_2,
                "result": (
                    "win"
                    if result == "away_win"
                    else "loss"
                    if result == "home_win"
                    else "draw"
                )
            },
            "result": result,
            "margin": margin,
            "total_points": score_1 + score_2
        }

        match_summaries.append(summary)

        scores.append(score_1)
        scores.append(score_2)

    highest_score = max(scores)
    lowest_score = min(scores)

    biggest_margin = max(
        match["margin"]
        for match in match_summaries
    )

    narrowest_margin = min(
        match["margin"]
        for match in match_summaries
    )

    highest_scoring_match = max(
        match_summaries,
        key=lambda match: match["total_points"]
    )

    lowest_scoring_match = min(
        match_summaries,
        key=lambda match: match["total_points"]
    )

    biggest_match = max(
        match_summaries,
        key=lambda match: match["margin"]
    )

    narrowest_match = min(
        match_summaries,
        key=lambda match: match["margin"]
    )

    return {
        "highest_score": highest_score,
        "lowest_score": lowest_score,
        "biggest_margin": biggest_margin,
        "narrowest_margin": narrowest_margin,
        "highest_scoring_match": highest_scoring_match,
        "lowest_scoring_match": lowest_scoring_match,
        "biggest_match": biggest_match,
        "narrowest_match": narrowest_match
    }


def calculate_table(matches, gameweek):
    teams = {}

    for match in matches:
        if int(match["event"]) > int(gameweek):
            continue

        for side in [1, 2]:
            entry_id = match[
                f"entry_{side}_entry"
            ]

            if entry_id not in teams:
                teams[entry_id] = {
                    "entry_id": entry_id,
                    "team_name": match[
                        f"entry_{side}_name"
                    ],
                    "manager": match[
                        f"entry_{side}_player_name"
                    ],
                    "played": 0,
                    "wins": 0,
                    "draws": 0,
                    "losses": 0,
                    "points": 0,
                    "scored": 0,
                    "conceded": 0
                }

        home = teams[
            match["entry_1_entry"]
        ]

        away = teams[
            match["entry_2_entry"]
        ]

        home_score = int(
            match["entry_1_points"]
        )

        away_score = int(
            match["entry_2_points"]
        )

        home["played"] += 1
        away["played"] += 1

        home["scored"] += home_score
        home["conceded"] += away_score

        away["scored"] += away_score
        away["conceded"] += home_score

        if home_score > away_score:
            home["wins"] += 1
            home["points"] += 3
            away["losses"] += 1

        elif away_score > home_score:
            away["wins"] += 1
            away["points"] += 3
            home["losses"] += 1

        else:
            home["draws"] += 1
            away["draws"] += 1
            home["points"] += 1
            away["points"] += 1

    table = sorted(
        teams.values(),
        key=lambda team: (
            -team["points"],
            -(
                team["scored"] -
                team["conceded"]
            ),
            -team["scored"],
            team["team_name"].lower()
        )
    )

    for position, team in enumerate(
        table,
        start=1
    ):
        team["position"] = position
        team["goal_difference"] = (
            team["scored"] -
            team["conceded"]
        )

    return table


def calculate_movement(
    matches,
    gameweek
):
    gameweek = int(gameweek)

    current = calculate_table(
        matches,
        gameweek
    )

    if gameweek <= 1:
        return {
            team["entry_id"]: {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }
            for team in current
        }

    previous = calculate_table(
        matches,
        gameweek - 1
    )

    previous_positions = {
        team["entry_id"]: team["position"]
        for team in previous
    }

    movement = {}

    for team in current:
        entry_id = team["entry_id"]
        current_position = team["position"]
        previous_position = previous_positions.get(
            entry_id
        )

        if previous_position is None:
            movement[entry_id] = {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }

        elif current_position < previous_position:
            movement[entry_id] = {
                "direction": "up",
                "amount": (
                    previous_position -
                    current_position
                ),
                "previous_position": previous_position
            }

        elif current_position > previous_position:
            movement[entry_id] = {
                "direction": "down",
                "amount": (
                    current_position -
                    previous_position
                ),
                "previous_position": previous_position
            }

        else:
            movement[entry_id] = {
                "direction": "same",
                "amount": 0,
                "previous_position": previous_position
            }

    return movement


def build_report_data(
    data,
    gameweek
):
    matches = data.get(
        "matches",
        []
    )

    week_matches = get_week_matches(
        data,
        gameweek
    )

    next_week_matches = get_next_week_matches(
        data,
        gameweek
    )

    players = get_week_players(
        data,
        gameweek
    )

    team_data = get_team_data(
        data,
        gameweek
    )

    table = calculate_table(
        matches,
        gameweek
    )

    movement = calculate_movement(
        matches,
        gameweek
    )

    statistics = calculate_weekly_statistics(
        week_matches
    )

    match_data = []

    for match in week_matches:
        score_1 = int(
            match["entry_1_points"]
        )

        score_2 = int(
            match["entry_2_points"]
        )

        if score_1 > score_2:
            result = "home_win"
        elif score_2 > score_1:
            result = "away_win"
        else:
            result = "draw"

        team_1_players = team_data.get(
            str(match["entry_1_entry"]),
            {}
        ).get(
            "players",
            []
        )

        team_2_players = team_data.get(
            str(match["entry_2_entry"]),
            {}
        ).get(
            "players",
            []
        )

        match_data.append({
            "match_id": match["id"],
            "team_1": {
                "entry_id": match[
                    "entry_1_entry"
                ],
                "team_name": match[
                    "entry_1_name"
                ],
                "manager": match[
                    "entry_1_player_name"
                ],
                "score": score_1,
                "players": team_1_players
            },
            "team_2": {
                "entry_id": match[
                    "entry_2_entry"
                ],
                "team_name": match[
                    "entry_2_name"
                ],
                "manager": match[
                    "entry_2_player_name"
                ],
                "score": score_2,
                "players": team_2_players
            },
            "result": result,
            "margin": abs(
                score_1 - score_2
            )
        })

    next_matches = []

    for match in next_week_matches:
        next_matches.append({
            "match_id": match["id"],
            "team_1": {
                "entry_id": match[
                    "entry_1_entry"
                ],
                "team_name": match[
                    "entry_1_name"
                ],
                "manager": match[
                    "entry_1_player_name"
                ]
            },
            "team_2": {
                "entry_id": match[
                    "entry_2_entry"
                ],
                "team_name": match[
                    "entry_2_name"
                ],
                "manager": match[
                    "entry_2_player_name"
                ]
            }
        })

    table_with_movement = []

    for team in table:
        team_copy = dict(team)

        team_copy["movement"] = movement.get(
            team["entry_id"],
            {
                "direction": "new",
                "amount": None,
                "previous_position": None
            }
        )

        table_with_movement.append(
            team_copy
        )

    return {
        "gameweek": gameweek,
        "weekly_statistics": statistics,
        "matches": match_data,
        "players": players,
        "league_table": table_with_movement,
        "next_gameweek_matches": next_matches
    }


def main():
    print("Reading Super 8s data...")

    data = load_data()

    completed_gameweeks = data.get(
        "completed_gameweeks",
        []
    )

    print(
        f"Found {len(completed_gameweeks)} "
        f"completed gameweeks"
    )

    reports = {}

    for gameweek in completed_gameweeks:
        print(
            f"Building report data for "
            f"Gameweek {gameweek}..."
        )

        reports[str(gameweek)] = (
            build_report_data(
                data,
                gameweek
            )
        )

    output = {
        "league": {
            "id": data.get("league_id"),
            "name": data.get(
                "league_name",
                "Super 8s"
            )
        },
        "gameweeks": reports
    }

    with REPORT_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            output,
            file,
            indent=2,
            ensure_ascii=False
        )

    print(
        f"Report data saved to {REPORT_FILE}"
    )


if __name__ == "__main__":
    main()
