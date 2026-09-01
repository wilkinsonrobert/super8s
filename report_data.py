import json
import os
from pathlib import Path

from openai import OpenAI


DATA_FILE = Path("gameweek_data.json")


def load_data():
    if not DATA_FILE.exists():
        raise RuntimeError(
            "gameweek_data.json does not exist."
        )

    with DATA_FILE.open(
        "r",
        encoding="utf-8"
    ) as file:
        return json.load(file)


def save_data(data):
    with DATA_FILE.open(
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False
        )


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
where everyone knows exactly who is being mocked.

The overriding objective is ENTERTAINMENT and BANTER.

Write in natural British English. The humour should feel like a sharp,
observational British mate taking the piss out of his friends — not like
an American sports website, corporate newsletter or AI trying to sound
funny.

Be cheeky, sarcastic, irreverent and occasionally ruthless.

Use manager names and team names frequently enough that the report feels
specific to the Super 8s league.

MANAGER NAME RULES:

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

Use ONLY these preferred names when referring to managers.

Established league jokes may be used when genuinely relevant:

Andrew Crystal has a reputation for being promiscuous.

Ben Woolman is very wealthy and spends lots of money.

Patrick Walsh enjoys a martini at all hours of the day.

Tom Curtis loves Tottenham Hotspur. "Spursy" may be used when relevant.

Martyn Bradshaw is a Burnley fan and Burnley can be mocked when
relevant.

Ben Woolman, Andrew Crystal, Patrick Walsh, David Woolman and Rob
Wilkinson are big Leeds fans.

Kevin Walsh is constantly off playing golf.

Rami lives in Saudi Arabia, so the joke is that he is sports washing
the league with all his money.

Do not force these jokes into the report.

IMPORTANT FACTUAL RULES:

1. Only use information contained in the supplied data.
2. Never invent a score, player, fixture, result, league position or
   statistical record.
3. Never invent a real-life football event.
4. Do not claim a player scored, assisted, kept a clean sheet or did
   anything else unless that information is actually present in the
   supplied data.
5. Do not invent rivalries or history.
6. Do not make personal comments about managers unrelated to FPL.
7. Use British football terminology.
8. Do not use American sports terminology such as matchup, playoffs,
   standings, roster or MVP.
9. Do not use cheesy generic sports-writing language.
10. The humour must be based on the supplied facts.

REPORT STRUCTURE:

The report must contain:

- A strong funny weekly headline.
- A short introduction.
- A mini match report for EVERY match played that gameweek.
- Relevant weekly statistics.
- Four funny weekly awards.
- Commentary on the current league table.
- A preview of the following gameweek using ONLY supplied fixtures.
- A short closing paragraph.

MATCH REPORTS:

Every match must receive its own report.

Identify important players and captaincy decisions where useful.

Look for amusing details such as narrow wins, huge scores, poor
captaincy decisions, bench points, large points gaps and unexpected
results.

WEEKLY AWARDS:

Create four funny awards specific to the actual gameweek.

TABLE COMMENTARY:

Use H2H league points as the primary ranking criterion.

Use total FPL points scored as the official tie-breaker.

Do NOT use goal difference as a league-table tie-breaker.

PREVIEW:

Preview two or three interesting fixtures from the following gameweek.

Use ONLY fixtures supplied in the data.

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

There must be one match object for every match supplied for the
gameweek.
"""

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
                "scored": 0
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
                "scored": 0
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

    league_table = list(teams.values())

    league_table.sort(
        key=lambda team: (
            -team["points"],
            -team["scored"]
        )
    )

    print(
        f"League table calculated for Gameweek {gameweek}:"
    )

    for position, team in enumerate(
        league_table,
        1
    ):
        print(
            f"{position}. "
            f"{team['team_name']} - "
            f"{team['points']} H2H points, "
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

Here are ALL available H2H fixtures:

{json.dumps(
    matches,
    indent=2,
    ensure_ascii=False
)}

Remember:

- Use only the supplied information.
- Do not invent real-life football events.
- Cover every match for Gameweek {gameweek}.
- Use actual supplied fixtures for the preview.
- Use H2H points and FPL points as the league-table ranking criteria.
- Keep the tone dry, witty and British.
- Return ONLY valid JSON.
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
        "Ben Foster": "Foz"
    }

    def replace_manager_names(value):

        if isinstance(value, str):
            for old, new in manager_name_replacements.items():
                value = value.replace(
                    old,
                    new
                )
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

    print(
        "Checking for completed, unprocessed gameweeks..."
    )

    data = load_data()

    completed_gameweeks = data.get(
        "completed_gameweeks",
        []
    )

    existing_reports = data.get(
        "weekly_reports",
        {}
    )

    matches = data.get(
        "matches",
        []
    )

    if not completed_gameweeks:
        print(
            "No completed gameweeks found."
        )
        return

    reports_created = 0

    for gameweek in completed_gameweeks:

        gameweek_key = str(gameweek)

        if gameweek_key in existing_reports:
            print(
                f"Gameweek {gameweek} already has "
                f"an AI report. Skipping."
            )
            continue

        gameweek_matches = [
            match
            for match in matches
            if int(match["event"]) == int(gameweek)
        ]

        expected_matches = 7

        if len(gameweek_matches) < expected_matches:
            print(
                f"Gameweek {gameweek} H2H data is incomplete. "
                f"Found {len(gameweek_matches)} matches; "
                f"expected {expected_matches}. Skipping."
            )
            continue

        if any(
            match.get("entry_1_points") is None
            or match.get("entry_2_points") is None
            for match in gameweek_matches
        ):
            print(
                f"Gameweek {gameweek} H2H scores are incomplete. "
                f"Skipping."
            )
            continue

        print(
            f"Gameweek {gameweek} has complete H2H data."
        )

        weekly_team_data = data.get(
            "weekly_team_data",
            {}
        ).get(
            gameweek_key,
            {}
        )

        if not weekly_team_data:
            print(
                f"No weekly player data available for "
                f"Gameweek {gameweek}. Skipping."
            )
            continue

        report_input = {
            "gameweek": gameweek,
            "matches": []
        }

        for match in gameweek_matches:

            entry_1 = str(match["entry_1_entry"])
            entry_2 = str(match["entry_2_entry"])

            report_input["matches"].append({
                "match_id": match["id"],
                "gameweek": gameweek,
                "team_1": {
                    "entry_id": match["entry_1_entry"],
                    "team_name": match["entry_1_name"],
                    "manager": match["entry_1_player_name"],
                    "score": match["entry_1_points"],
                    "result": (
                        "win"
                        if match["entry_1_win"]
                        else "draw"
                        if match["entry_1_draw"]
                        else "loss"
                    ),
                    "players": weekly_team_data.get(
                        entry_1,
                        {}
                    ).get(
                        "players",
                        []
                    )
                },
                "team_2": {
                    "entry_id": match["entry_2_entry"],
                    "team_name": match["entry_2_name"],
                    "manager": match["entry_2_player_name"],
                    "score": match["entry_2_points"],
                    "result": (
                        "win"
                        if match["entry_2_win"]
                        else "draw"
                        if match["entry_2_draw"]
                        else "loss"
                    ),
                    "players": weekly_team_data.get(
                        entry_2,
                        {}
                    ).get(
                        "players",
                        []
                    )
                }
            })

        report_input["weekly_statistics"] = {
            "highest_score": max(
                match["entry_1_points"]
                for match in gameweek_matches
                + [
                    {
                        "entry_1_points": match["entry_2_points"],
                        "entry_2_points": match["entry_2_points"]
                    }
                    for match in []
                ]
            )
        }

        all_scores = []

        for match in gameweek_matches:
            all_scores.append(
                match["entry_1_points"]
            )
            all_scores.append(
                match["entry_2_points"]
            )

        report_input["weekly_statistics"]["highest_score"] = max(
            all_scores
        )

        report_input["weekly_statistics"]["lowest_score"] = min(
            all_scores
        )

        print(
            f"Generating AI report for Gameweek {gameweek}..."
        )

        try:

            ai_report = generate_ai_report(
                gameweek,
                report_input,
                matches
            )

            existing_reports[
                gameweek_key
            ] = ai_report

            data[
                "weekly_reports"
            ] = existing_reports

            processed = data.get(
                "processed_gameweeks",
                []
            )

            if gameweek not in processed:
                processed.append(gameweek)

            data[
                "processed_gameweeks"
            ] = processed

            save_data(data)

            reports_created += 1

            print(
                f"AI report generated and permanently "
                f"saved for Gameweek {gameweek}."
            )

        except Exception as error:

            print(
                f"AI report failed for "
                f"Gameweek {gameweek}: {error}"
            )

            print(
                "The gameweek has NOT been marked as "
                "processed and will be retried later."
            )

    if reports_created == 0:

        print(
            "No new AI reports required."
        )

    else:

        print(
            f"Created {reports_created} new AI report(s)."
        )


if __name__ == "__main__":
    main()
