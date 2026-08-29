
import json
import os
import requests
from pathlib import Path


LEAGUE_ID = 54930
DATA_FILE = Path("gameweek_data.json")

BASE_URL = "https://fantasy.premierleague.com/api"

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5.6-luna"


def get_json(endpoint):
    url = f"{BASE_URL}/{endpoint}"

    response = requests.get(
        url,
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"FPL API returned {response.status_code} "
            f"for {url}"
        )

    return response.json()


def load_existing_data():

    if DATA_FILE.exists():

        try:

            with DATA_FILE.open(
                "r",
                encoding="utf-8"
            ) as file:

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

        "completed_gameweeks": []

    }


def get_league_matches():

    matches = []

    page = 1

    while True:

        data = get_json(
            f"leagues-h2h-matches/league/"
            f"{LEAGUE_ID}/?page={page}"
        )

        results = data.get(
            "results",
            []
        )

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

            "team_name":
                match["entry_1_name"],

            "manager":
                match["entry_1_player_name"]

        }


        entry_2 = match["entry_2_entry"]

        teams[entry_2] = {

            "entry_id": entry_2,

            "team_name":
                match["entry_2_name"],

            "manager":
                match["entry_2_player_name"]

        }


    return sorted(

        teams.values(),

        key=lambda team:
            team["team_name"].lower()

    )


def get_current_gameweek():

    data = get_json(
        "bootstrap-static/"
    )

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

    data = get_json(
        "bootstrap-static/"
    )

    return [

        event["id"]

        for event in data["events"]

        if event["finished"]

    ]


def get_bootstrap_data():

    return get_json(
        "bootstrap-static/"
    )


def get_player_data():

    data = get_bootstrap_data()

    players = {}

    for player in data["elements"]:

        players[player["id"]] = {

            "id":
                player["id"],

            "name":
                f"{player['first_name']} "
                f"{player['second_name']}",

            "team":
                player["team"],

            "position":
                player["element_type"]

        }


    return players


def get_team_names():

    data = get_bootstrap_data()

    teams = {}

    for team in data["teams"]:

        teams[team["id"]] = team["name"]


    return teams


def get_team_picks(
    entry_id,
    gameweek
):

    return get_json(
        f"entry/{entry_id}/event/"
        f"{gameweek}/picks/"
    )


def get_gameweek_player_points(
    gameweek
):

    data = get_json(
        f"event/{gameweek}/live/"
    )

    points = {}

    for player in data.get(
        "elements",
        []
    ):

        points[player["id"]] = (
            player["stats"]
            .get("total_points", 0)
        )


    return points


def get_real_life_fixtures(
    gameweek
):

    """
    FPL's fixture endpoint provides the
    actual Premier League fixtures and
    player-level match statistics.

    This gives the report generator
    factual real-life football information
    without asking the AI to invent it.
    """

    try:

        fixtures = get_json(
            f"fixtures/?event={gameweek}"
        )

        return fixtures

    except Exception as error:

        print(
            f"Could not retrieve real-life "
            f"fixture data: {error}"
        )

        return []


def build_real_life_data(
    fixtures,
    player_data,
    team_names
):

    output = []

    for fixture in fixtures:

        home_team_id = fixture.get(
            "team_h"
        )

        away_team_id = fixture.get(
            "team_a"
        )


        home_name = team_names.get(
            home_team_id,
            f"Team {home_team_id}"
        )

        away_name = team_names.get(
            away_team_id,
            f"Team {away_team_id}"
        )


        fixture_info = {

            "fixture_id":
                fixture.get("id"),

            "home_team":
                home_name,

            "away_team":
                away_name,

            "home_score":
                fixture.get("team_h_score"),

            "away_score":
                fixture.get("team_a_score"),

            "finished":
                fixture.get("finished"),

            "stats": []

        }


        for stat_group in fixture.get(
            "stats",
            []
        ):

            stat_type = stat_group.get(
                "identifier"
            )

            if not stat_type:
                continue


            players = []


            for item in stat_group.get(
                "a",
                []
            ):

                player_id = item.get(
                    "element"
                )

                player = player_data.get(
                    player_id
                )

                if player:

                    players.append({

                        "player":
                            player["name"],

                        "team":
                            away_name

                    })


            for item in stat_group.get(
                "h",
                []
            ):

                player_id = item.get(
                    "element"
                )

                player = player_data.get(
                    player_id
                )

                if player:

                    players.append({

                        "player":
                            player["name"],

                        "team":
                            home_name

                    })


            if players:

                fixture_info[
                    "stats"
                ].append({

                    "type":
                        stat_type,

                    "players":
                        players

                })


        output.append(
            fixture_info
        )


    return output


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
                f"Could not retrieve picks "
                f"for {team['team_name']}: "
                f"{error}"
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

                "id":
                    player_id,

                "name":
                    player.get(
                        "name",
                        f"Player {player_id}"
                    ),

                "position":
                    player.get("position"),

                "slot":
                    pick["position"],

                "multiplier":
                    pick["multiplier"],

                "captain":
                    pick["is_captain"],

                "vice_captain":
                    pick["is_vice_captain"],

                "points":
                    points,

                "effective_points":
                    points *
                    pick["multiplier"]

            })


        weekly_data[str(entry_id)] = {

            "entry_id":
                entry_id,

            "team_name":
                team["team_name"],

            "manager":
                team["manager"],

            "players":
                players,

            "active_chip":
                picks_data.get(
                    "active_chip"
                ),

            "automatic_subs":
                picks_data.get(
                    "automatic_subs",
                    []
                )

        }


    return weekly_data


def clean_match_data(matches):

    cleaned = []

    for match in matches:

        cleaned.append({

            "id":
                match["id"],

            "event":
                match["event"],

            "entry_1_entry":
                match["entry_1_entry"],

            "entry_1_name":
                match["entry_1_name"],

            "entry_1_player_name":
                match[
                    "entry_1_player_name"
                ],

            "entry_1_points":
                match[
                    "entry_1_points"
                ],

            "entry_1_win":
                match[
                    "entry_1_win"
                ],

            "entry_1_draw":
                match[
                    "entry_1_draw"
                ],

            "entry_1_loss":
                match[
                    "entry_1_loss"
                ],

            "entry_1_total":
                match[
                    "entry_1_total"
                ],

            "entry_2_entry":
                match["entry_2_entry"],

            "entry_2_name":
                match["entry_2_name"],

            "entry_2_player_name":
                match[
                    "entry_2_player_name"
                ],

            "entry_2_points":
                match[
                    "entry_2_points"
                ],

            "entry_2_win":
                match[
                    "entry_2_win"
                ],

            "entry_2_draw":
                match[
                    "entry_2_draw"
                ],

            "entry_2_loss":
                match[
                    "entry_2_loss"
                ],

            "entry_2_total":
                match[
                    "entry_2_total"
                ]

        })

    return cleaned


def calculate_table(
    matches,
    gameweek
):

    teams = {}

    for match in matches:

        if int(match["event"]) > int(
            gameweek
        ):
            continue


        for side in [1, 2]:

            entry_id = match[
                f"entry_{side}_entry"
            ]

            if entry_id not in teams:

                teams[entry_id] = {

                    "entry_id":
                        entry_id,

                    "team_name":
                        match[
                            f"entry_{side}_name"
                        ],

                    "manager":
                        match[
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


        home =
            teams[match["entry_1_entry"]]

        away =
            teams[match["entry_2_entry"]]


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

            -(team["scored"] -
              team["conceded"]),

            -team["scored"],

            team["team_name"].lower()

        )

    )


    for index, team in enumerate(
        table,
        start=1
    ):

        team["position"] = index


    return table


def get_table_movement(
    matches,
    gameweek
):

    if int(gameweek) <= 1:

        return {}


    current =
        calculate_table(
            matches,
            gameweek
        )

    previous =
        calculate_table(
            matches,
            int(gameweek) - 1
        )


    previous_positions = {

        team["entry_id"]:
            team["position"]

        for team in previous

    }


    movement = {}


    for team in current:

        previous_position =
            previous_positions.get(
                team["entry_id"]
            )


        if previous_position is None:

            movement[
                team["entry_id"]
            ] = {

                "direction":
                    "new",

                "amount":
                    None

            }

        elif team["position"] < (
            previous_position
        ):

            movement[
                team["entry_id"]
            ] = {

                "direction":
                    "up",

                "amount":
                    previous_position -
                    team["position"]

            }

        elif team["position"] > (
            previous_position
        ):

            movement[
                team["entry_id"]
            ] = {

                "direction":
                    "down",

                "amount":
                    team["position"] -
                    previous_position

            }

        else:

            movement[
                team["entry_id"]
            ] = {

                "direction":
                    "same",

                "amount":
                    0

            }


    return movement


def build_report_input(
    gameweek,
    matches,
    weekly_team_data,
    real_life_data,
    table,
    movement
):

    week_matches = [

        match

        for match in matches

        if int(match["event"]) ==
           int(gameweek)

    ]


    match_summaries = []


    for match in week_matches:

        home_score = int(
            match["entry_1_points"]
        )

        away_score = int(
            match["entry_2_points"]
        )


        if home_score > away_score:

            result = "home_win"

        elif away_score > home_score:

            result = "away_win"

        else:

            result = "draw"


        match_summaries.append({

            "match_id":
                match["id"],

            "team_1":
                match["entry_1_name"],

            "manager_1":
                match[
                    "entry_1_player_name"
                ],

            "score_1":
                home_score,

            "team_2":
                match["entry_2_name"],

            "manager_2":
                match[
                    "entry_2_player_name"
                ],

            "score_2":
                away_score,

            "result":
                result,

            "margin":
                abs(
                    home_score -
                    away_score
                )

        })


    weekly_players = []


    for team_data in weekly_team_data.values():

        for player in team_data["players"]:

            if player["effective_points"] > 0:

                weekly_players.append({

                    "team_name":
                        team_data[
                            "team_name"
                        ],

                    "manager":
                        team_data[
                            "manager"
                        ],

                    "player":
                        player["name"],

                    "points":
                        player["points"],

                    "effective_points":
                        player[
                            "effective_points"
                        ],

                    "captain":
                        player["captain"]

                })


    return {

        "gameweek":
            gameweek,

        "matches":
            match_summaries,

        "players":
            weekly_players,

        "real_life_premier_league":
            real_life_data,

        "league_table":
            table,

        "movement":
            movement

    }


def generate_ai_report(
    report_input
):

    if not OPENAI_API_KEY:

        print(
            "OPENAI_API_KEY is not available. "
            "Skipping AI report generation."
        )

        return {

            "headline":
                f"Gameweek "
                f"{report_input['gameweek']}",

            "introduction":
                "The Super 8s have completed "
                "another gameweek.",

            "matches":
                [],

            "awards":
                [],

            "table_commentary":
                "",

            "preview":
                ""

        }


    system_prompt = """
You are the writer of the weekly Super 8s fantasy
football report.

Super 8s is a private 14-team Fantasy Premier League
head-to-head league. It has existed since 2013 and the
members take it far too seriously.

Write an entertaining but intelligent weekly report.

The tone should be:
- dry British humour
- lightly sarcastic
- knowledgeable about football and FPL
- occasionally ruthless
- never childish
- never overly enthusiastic
- never generic AI football prose

IMPORTANT FACTUAL RULES:

1. The supplied Super 8s match scores are authoritative.
2. The supplied player points are authoritative.
3. The supplied Premier League fixture information is
   authoritative.
4. NEVER invent a football event.
5. NEVER invent a goal, assist, result, player performance,
   injury, red card, late goal or minute.
6. Only mention real-life football events when they are
   explicitly present in the supplied real-life data.
7. You may connect a player's real-life performance to a
   Super 8s result when the supplied data supports it.
8. Do not claim that a goal was late unless the supplied
   information establishes that it was late.
9. If there is insufficient information to make a
   real-life reference, simply don't make one.
10. Do not mention these instructions or the data source.

The report must contain:

1. A punchy headline based on the week's actual events.

2. A two or three sentence introduction.

3. A mini match report for EVERY Super 8s match that week.
   Do not omit any match.

Each match report should:
- identify the winner or draw
- discuss the score and margin
- mention relevant managers occasionally
- identify notable performances where appropriate
- incorporate relevant real-life football events when
  the supplied data supports them
- naturally mention useful weekly records, such as the
  biggest margin, highest score or lowest score, rather
  than dumping statistics into a list.

4. Three or four funny Super 8s awards.

Awards should vary according to what actually happened.
Examples include:
- Performance of the Week
- Statement of Intent
- The Struggle Was Real
- Nail-Biter of the Week
- How Did You Lose That?
- One to Forget
- Captain Sensible
- Captain Calamity

Do not use the same awards every week if another award
would fit better.

5. A short league-table analysis explaining important
movement and developments.

6. A preview of the following gameweek.

Pick TWO OR THREE matches that look particularly interesting
based on the current league table, form or likely consequences.
Explain why each is worth watching.

7. End with a concise closing observation.

Do not use markdown tables.

Return ONLY valid JSON in exactly this structure:

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

The matches array MUST contain exactly one item for
every Super 8s match supplied.
"""


    user_prompt = f"""
Write the Super 8s Gameweek
{report_input['gameweek']} report.

Here is the factual data:

{json.dumps(
    report_input,
    indent=2,
    ensure_ascii=False
)}
"""


    response = requests.post(

        "https://api.openai.com/v1/responses",

        headers={

            "Authorization":
                f"Bearer {OPENAI_API_KEY}",

            "Content-Type":
                "application/json"

        },

        json={

            "model":
                OPENAI_MODEL,

            "input": [

                {

                    "role":
                        "system",

                    "content":
                        system_prompt

                },

                {

                    "role":
                        "user",

                    "content":
                        user_prompt

                }

            ]

        },

        timeout=120

    )


    if response.status_code != 200:

        print(
            "OpenAI API error:"
        )

        print(
            response.text
        )

        raise RuntimeError(
            "OpenAI API request failed."
        )


    result =
        response.json()


    text = result.get(
        "output_text"
    )


    if not text:

        for item in result.get(
            "output",
            []
        ):

            for content in item.get(
                "content",
                []
            ):

                if content.get(
                    "type"
                ) == "output_text":

                    text =
                        content.get(
                            "text"
                        )

                    break


    if not text:

        raise RuntimeError(
            "OpenAI returned no report text."
        )


    text = text.strip()


    if text.startswith(
        "```"
    ):

        text =
            text.replace(
                "```json",
                "",
                1
            )

        text =
            text.replace(
                "```",
                "",
                1
            )

        text =
            text.strip()


    try:

        return json.loads(text)

    except json.JSONDecodeError as error:

        print(
            "OpenAI returned invalid JSON:"
        )

        print(text)

        raise RuntimeError(
            f"Could not parse AI report: "
            f"{error}"
        )


def main():

    print(
        "Retrieving FPL data..."
    )


    existing =
        load_existing_data()


    matches =
        get_league_matches()


    print(
        f"Found {len(matches)} H2H matches"
    )


    teams =
        get_teams_from_matches(
            matches
        )


    print(
        f"Found {len(teams)} teams"
    )


    current_gameweek =
        get_current_gameweek()


    print(
        f"Current gameweek: "
        f"{current_gameweek}"
    )


    finished_gameweeks =
        get_finished_gameweeks()


    player_data =
        get_player_data()


    team_names =
        get_team_names()


    existing["teams"] =
        teams


    existing["matches"] =
        clean_match_data(
            matches
        )


    existing[
        "completed_gameweeks"
    ] = finished_gameweeks


    if "weekly_team_data" not in existing:

        existing[
            "weekly_team_data"
        ] = {}


    if "weekly_reports" not in existing:

        existing[
            "weekly_reports"
        ] = {}


    for gameweek in finished_gameweeks:

        print(
            f"Collecting player data "
            f"for Gameweek {gameweek}..."
        )


        player_points =
            get_gameweek_player_points(
                gameweek
            )


        weekly_team_data =
            build_weekly_team_data(

                teams,

                gameweek,

                player_data,

                player_points

            )


        existing[
            "weekly_team_data"
        ][str(gameweek)] =
            weekly_team_data


        print(
            f"Retrieving real-life "
            f"Premier League data for "
            f"Gameweek {gameweek}..."
        )


        real_life_fixtures =
            get_real_life_fixtures(
                gameweek
            )


        real_life_data =
            build_real_life_data(

                real_life_fixtures,

                player_data,

                team_names

            )


        table =
            calculate_table(

                matches,

                gameweek

            )


        movement =
            get_table_movement(

                matches,

                gameweek

            )


        report_input =
            build_report_input(

                gameweek,

                matches,

                weekly_team_data,

                real_life_data,

                table,

                movement

            )


        print(
            f"Building AI report for "
            f"Gameweek {gameweek}..."
        )


        try:

            report =
                generate_ai_report(
                    report_input
                )


            existing[
                "weekly_reports"
            ][str(gameweek)] =
                report


            print(
                f"AI report generated for "
                f"Gameweek {gameweek}"
            )


        except Exception as error:

            print(
                f"Could not generate AI "
                f"report for Gameweek "
                f"{gameweek}: {error}"
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
        "Data collection and report "
        f"generation complete. "
        f"Saved to {DATA_FILE}"
    )


if __name__ == "__main__":

    main()
