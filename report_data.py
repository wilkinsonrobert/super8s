import json
from pathlib import Path

DATA_FILE = Path("gameweek_data.json")
REPORT_FILE = Path("report_data.json")

def load_data():
with DATA_FILE.open("r", encoding="utf-8") as file:
return json.load(file)

def get_week_matches(data, gameweek):
return [
match
for match in data.get("matches", [])
if int(match["event"]) == int(gameweek)
]

def get_next_week_matches(data, gameweek):
next_gameweek = int(gameweek) + 1

```
return [
    match
    for match in data.get("matches", [])
    if int(match["event"]) == next_gameweek
]
```

def get_team_data(data, gameweek):
return data.get("weekly_team_data", {}).get(
str(gameweek), {}
)

def get_week_players(data, gameweek):
weekly = get_team_data(data, gameweek)

```
players = []

for team_data in weekly.values():
    for player in team_data.get("players", []):
        players.append({
            "team_name": team_data.get("team_name"),
            "manager": team_data.get("manager"),
            "player": player.get("name"),
            "points": player.get("points", 0),
            "effective_points": player.get(
                "effective_points", 0
            ),
            "captain": player.get(
                "captain", False
            ),
            "multiplier": player.get(
                "multiplier", 1
            )
        })

return players
```

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

```
match_summaries = []
scores = []

for match in matches:
    score_1 = int(match.get("entry_1_points", 0))
    score_2 = int(match.get("entry_2_points", 0))

    margin = abs(score_1 - score_2)

    if score_1 > score_2:
        result = "home_win"
        result_text_1 = "win"
        result_text_2 = "loss"
    elif score_2 > score_1:
        result = "away_win"
        result_text_1 = "loss"
        result_text_2 = "win"
    else:
        result = "draw"
        result_text_1 = "draw"
        result_text_2 = "draw"

    summary = {
        "match_id": match.get("id"),
        "gameweek": match.get("event"),
        "team_1": {
            "entry_id": match.get("entry_1_entry"),
            "team_name": match.get("entry_1_name"),
            "manager": match.get(
                "entry_1_player_name"
            ),
            "score": score_1,
            "result": result_text_1
        },
        "team_2": {
            "entry_id": match.get("entry_2_entry"),
            "team_name": match.get("entry_2_name"),
            "manager": match.get(
                "entry_2_player_name"
            ),
            "score": score_2,
            "result": result_text_2
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
```

def calculate_table(matches, gameweek):
teams = {}

```
for match in matches:
    if int(match["event"]) > int(gameweek):
        continue

    for side in (1, 2):
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
        -(team["scored"] - team["conceded"]),
        -team["scored"],
        team["team_name"].lower()
    )
)

for position, team in enumerate(table, start=1):
    team["position"] = position
    team["goal_difference"] = (
        team["scored"] - team["conceded"]
    )

return table
```

def calculate_movement(matches, gameweek):
gameweek = int(gameweek)

```
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
```

def build_match_data(data, gameweek):
week_matches = get_week_matches(
data,
gameweek
)

```
team_data = get_team_data(
    data,
    gameweek
)

matches = []

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
    ).get("players", [])

    team_2_players = team_data.get(
        str(match["entry_2_entry"]),
        {}
    ).get("players", [])

    matches.append({
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

return matches
```

def build_next_matches(data, gameweek):
next_matches = get_next_week_matches(
data,
gameweek
)

```
results = []

for match in next_matches:
    results.append({
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

return results
```

def build_report_data(data, gameweek):
matches = data.get("matches", [])

```
week_matches = get_week_matches(
    data,
    gameweek
)

statistics = calculate_weekly_statistics(
    week_matches
)

table = calculate_table(
    matches,
    gameweek
)

movement = calculate_movement(
    matches,
    gameweek
)

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
    "gameweek": int(gameweek),
    "weekly_statistics": statistics,
    "matches": build_match_data(
        data,
        gameweek
    ),
    "players": get_week_players(
        data,
        gameweek
    ),
    "league_table": table_with_movement,
    "next_gameweek_matches": build_next_matches(
        data,
        gameweek
    )
}
```

def main():
print("Reading Super 8s data...")

```
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

    reports[str(gameweek)] = build_report_data(
        data,
        gameweek
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
```

if **name** == "**main**":
main()
