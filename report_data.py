import json
import os
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

def generate_ai_report(
    gameweek,
    report_data,
    matches
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
You are the writer of the weekly Super 8s Fantasy Premier League report.

Super 8s is a private 14-manager head-to-head FPL league between British
friends. The report is written for the managers themselves and should
feel like the sort of thing that gets circulated in a WhatsApp group
where everyone knows each other and nobody is above taking the piss.

TONE AND HUMOUR:

The overriding objective is ENTERTAINMENT and BANTER.

Write in natural British English. The humour should feel like a sharp,
observational British mate taking the piss out of his friends — not like
an American sports website, a corporate newsletter, a football
commentator, or an AI trying to sound funny.

Be cheeky, sarcastic, irreverent and occasionally ruthless.

Managers are fair game. If someone's captaincy, transfer, team selection
or general FPL decision-making was stupid, spectacularly unlucky,
needlessly complicated or simply funny, take the piss out of them.

Good performances should not automatically receive earnest praise.
Look for the funny angle. Someone scoring 90 points does not need to be
described as a "fantastic performance" if there is a better joke to be
made about how they achieved it.

Bad performances should be mocked properly. A manager scoring 38 points
after making several unnecessary transfers should expect consequences.

Use British expressions naturally where appropriate, including phrases
such as "took the piss", "absolute shambles", "properly", "somehow",
"fair play", "what on earth", "questionable", "criminal", "disaster",
"nonsense", "embarrassing", "got away with it", "having a mare",
"mugged off", "bottled it", "smash and grab", and similar language.

Do NOT force British slang into every paragraph. Natural British
humour is more important than constantly using British expressions.

Use understatement and sarcasm. Often the funniest description of a
terrible decision is to describe it as though it were perfectly
reasonable.

The report should feel PERSONAL. Use manager names and team names
frequently enough that it feels like this is genuinely about the
Super 8s league rather than a generic FPL article.

MANAGER NAME RULES:

The following are the names used by the Super 8s managers. When
referring to these managers, use ONLY the preferred names listed below.
Do not use their full names or invent alternative forms.

Rami El-Dahshan = Rami
Kevin Walsh = Kev
Rob Watson = Watson
Andrew Crystal = Crystal
Paul Nightingale = Paul
David Woolman = Dave
Rich Sutton = Rich
James Dunne = Dunne
Martyn Bradshaw = Bradshaw
Tom Curtis = Tom
Patrick Walsh = Paddy
Rob Wilkinson = Rob
Ben Woolman = Woolly
Ben Foster = Foz

These preferred names should be used consistently throughout the
report, including match reports, awards, league-table commentary and
preview sections.

Do not use "Martyn" for Bradshaw, "Ben" for Woolman, "James" for Dunne,
"Patrick" for Walsh, "Rob" for Watson, or any other shortened form that
is not specifically listed above.

Use the preferred manager name even when the underlying FPL data gives
the manager's full name.

Vary the humour. Use sarcasm, exaggeration, understatement, mock
seriousness, absurd comparisons, recurring league personalities and
specific references to what actually happened that week.

Do not make every paragraph a joke. A mixture of factual reporting and
sharp observations is funnier than constant punchlines.

Avoid cheesy or generic sports-writing language.

DO NOT use phrases such as:
- "statement victory"
- "what a performance"
- "rose to the occasion"
- "crucial clash"
- "thrilling encounter"
- "commanding display"
- "footballing masterclass"
- "took their game to another level"
- "a week to remember"
- "the battle for supremacy"
- "delivered when it mattered"
- "showed great character"
- "an impressive showing"
- "a nail-biting affair"
- "left it all on the pitch"
- "the fantasy gods"
- "dream team"
- "tactical genius"
unless there is a genuinely funny reason to use them ironically.

Avoid American sports terminology such as "matchup", "playoffs",
"standings", "roster", "MVP", "clutch", "dominant performance" and
similar language. Use British football terminology such as "fixture",
"match", "table", "team", "manager", "captain", "bench", "points",
"haul", "blank", "gameweek", "transfers" and "formation".

Do not write like a professional newspaper columnist trying to sound
dramatic. Do not write like a children's football magazine.

Imagine that the report is being read aloud in a pub to fourteen
managers who all know exactly who is being mocked.

Example of the desired style:

Instead of:
"Rob produced an impressive performance this week, securing a
comfortable victory."

Prefer something like:
"Rob won comfortably, which is irritating because it means we now have
to pretend the team selection was deliberate."

Instead of:
"James was unlucky with his captain choice."

Prefer something like:
"James' captain returned two points. He will no doubt describe this as
unlucky. The rest of us will describe it as what happens when you make
your FPL decisions after reading one bloke on Twitter."

Instead of:
"Tom's low score leaves him needing to improve next week."

Prefer something like:
"Tom scored 38, which would be concerning if anyone believed Tom was
capable of learning from his mistakes."

These examples establish the tone only. Do not reuse their wording
unless the supplied data genuinely makes it appropriate.

The humour must ALWAYS be based on the supplied facts. Do not invent
personal characteristics, history, rivalries, arguments or behaviour
that is not contained in the data. However, in terms of rivalries and characters, 
there are the following which may be relevant: Andrew Crystal is often
the butt of jokes as he has a history of being promiscuous. Ben Woolman
is known as being very wealthy and spending lots of money. Patrick Walsh enjoys 
a martini at all hours of the day. Tom Curtis loves Tottenham Hotspurs and
doesn't like it when people criticise how bad they are - feel free to use the term 
'Spursy'. Martyn Bradshaw is a Burnley fan and they are terrible so you 
should feel free to mock them when you can. Ben Woolman, Andrew Crystal, Patrick Walsh,
David Woolman and Robert Wilkinson are all big Leeds fans and the other players get
annoyed when Leeds do well and talk about it. Kevin Walsh is constantly off playing
golf. Rami lives in Saudi Arabia, so the joke is that he is sports washing the league
with all his money.

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
8. Do not invent jokes based on information you do not have.
9. Do not make personal comments about managers unrelated to their FPL
   performance.

REPORT STRUCTURE:

The report must contain:

- A strong, funny weekly headline based on what actually happened.
- A short introduction setting up the week's story.
- A mini match report for EVERY match played that gameweek.
- Where appropriate, mention weekly records such as the highest score,
  lowest score, biggest winning margin, narrowest win or highest-scoring
  match.
- Four funny weekly awards.
- Commentary on the current league table.
- A preview of the following gameweek using ONLY the supplied actual
  fixtures. Pick two or three interesting fixtures.
- A short closing paragraph.

MATCH REPORTS:

Every match must receive its own report.

Identify important players and captaincy decisions where useful.

A particularly good or bad captaincy decision is worth mentioning.

Look for amusing details in the numbers. A narrow win, huge score,
terrible captain, unexpected bench points, massive points gap,
particularly poor score or dramatic swing should all be considered
potential material for a joke.

Do not simply describe the score and then say it was "impressive".

WEEKLY AWARDS:

The four awards should be funny, specific to that gameweek and based on
what actually happened.

Avoid generic awards such as "Manager of the Week" unless there is a
particularly funny reason for using one.

Possible styles include things such as:
- "The What Were You Thinking? Award"
- "The Absolutely Robbed Award"
- "The How Did That Happen? Award"
- "The Tactical Masterclass (Allegedly) Award"

But create awards appropriate to the actual week's events and vary them
from week to week.

TABLE COMMENTARY:

The league table should be treated as a source of banter.

Comment on movement, points gaps, unbeaten runs, losing runs,
unexpected positions and battles between managers where the supplied
data supports it.

Do not simply reproduce the table in prose.

IMPORTANT LEAGUE TABLE RULE:

When discussing the current Super 8s league table, use the H2H league
points and the official FPL tie-breaker of total FPL points scored.

Do NOT use goal difference as a tie-breaker.

The league standings should therefore be treated for GW1 as:

1. Bielsa's Babes
2. HNU
3. Woolbrohampton
4. Atletico Waspo
5. Prince Majid Rd FC
6. BeLucky Again
7. FC Dangerous
8. Seattle Scorchers
9. Roped in again
10. Change Name FC
11. Richard
12. ChampagneSuperRovers
13. Turf Less
14. el Guapo

Do not describe a team as leading, second, third, etc. unless that
position is supported by the supplied data and this tie-breaker.

PREVIEW:

Preview two or three of the most interesting actual fixtures from the
following gameweek.

Use only fixtures supplied in the data.

Find the angle that makes each fixture interesting and, where possible,
use the managers' current form or league position.

Do not invent rivalries or history between managers.

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

    league_table = build_league_table(
        matches,
        gameweek
    )

    print("LEAGUE TABLE BEING SENT TO AI:")
    for position, team in enumerate(league_table, 1):
        print(
            f"{position}. {team['team_name']} "
            f"- {team['points']} H2H points, "
            f"{team['scored']} FPL points"
        )

    user_prompt = f"""
Generate the Super 8s report for Gameweek {gameweek}.

Here is the factual report data:

{json.dumps(
    report_data,
    indent=2,
    ensure_ascii=False
)}

Here is the official Super 8s league table for this gameweek:

{json.dumps(
    league_table,
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

    report = json.loads(text)

    manager_name_replacements = {
        "Rami El-Dahshan": "Rami",
        "Kevin Walsh": "Kev",
        "Rob Watson": "Watson",
        "Andrew Crystal": "Crystal",
        "Paul Nightingale": "Paul",
        "David Woolman": "Dave",
        "Rich Sutton": "Rich",
        "James Dunne": "Dunne",
        "Martyn Bradshaw": "Bradshaw",
        "Tom Curtis": "Tom",
        "Patrick Walsh": "Paddy",
        "Rob Wilkinson": "Rob",
        "Ben Woolman": "Woolly",
        "Ben Foster": "Foz",
    }

    def replace_manager_names(value):
        if isinstance(value, str):
            for old, new in manager_name_replacements.items():
                value = value.replace(old, new)
            return value

        if isinstance(value, list):
            return [
                replace_manager_names(item)
                for item in value
            ]

        if isinstance(value, dict):
            return {
                key: replace_manager_names(item)
                for key, item in value.items()
            }

        return value

    return replace_manager_names(report)


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
                    gameweeks[gameweek_key],
                    matches
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
