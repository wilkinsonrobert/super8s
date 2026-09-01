import json
import os
from pathlib import Path

from openai import OpenAI


DATA_FILE = Path("gameweek_data.json")
REPORT_FILE = Path("report_data.json")


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


def load_report_data():
    if not REPORT_FILE.exists():
        raise RuntimeError(
            "report_data.json does not exist."
        )

    with REPORT_FILE.open(
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
Look for the funny angle.

Bad performances should be mocked properly.

Use British expressions naturally where appropriate, including phrases
such as "took the piss", "absolute shambles", "properly", "somehow",
"fair play", "what on earth", "questionable", "criminal", "disaster",
"nonsense", "embarrassing", "got away with it", "having a mare",
"mugged off", "bottled it", "smash and grab", and similar language.

Do NOT force British slang into every paragraph.

Use understatement and sarcasm.

The report should feel PERSONAL. Use manager names and team names
frequently enough that it feels like this is genuinely about the
Super 8s league rather than a generic FPL article.

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

Do not use full names or invent alternative forms.

The following established league jokes may be used when genuinely
relevant to the week's FPL events:

Andrew Crystal is often the butt of jokes as he has a history of being
promiscuous.

Ben Woolman is known as being very wealthy and spending lots of money.

Patrick Walsh enjoys a martini at all hours of the day.

Tom Curtis loves Tottenham Hotspur and doesn't like criticism of Spurs.
The term "Spursy" may be used when relevant.

Martyn Bradshaw is a Burnley fan and Burnley can be mocked when relevant.

Ben Woolman, Andrew Crystal, Patrick Walsh, David Woolman and Rob
Wilkinson are big Leeds fans. The others get annoyed when Leeds do well
and talk about it.

Kevin Walsh is constantly off playing golf.

Rami lives in Saudi Arabia, so the joke is that he is sports washing
the league with all his money.

Do not force these jokes into the report. Use them only where they fit.

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
- A preview of the following gameweek using ONLY supplied actual
  fixtures.
- A short closing paragraph.

MATCH REPORTS:

Every match must receive its own report.

Identify important players and captaincy decisions where useful.

A particularly good or bad captaincy decision is worth mentioning.

Look for amusing details in the numbers.

Do not simply describe the score and then say it was impressive.

WEEKLY AWARDS:

The four awards should be funny, specific to that gameweek and based on
what actually happened.

Avoid generic awards unless there is a particularly funny reason for
using one.

TABLE COMMENTARY:

Treat the league table as a source of banter.

Comment on movement, points gaps, unbeaten runs, losing runs,
unexpected positions and battles between managers where the supplied
data supports it.

Use H2H league points as the primary ranking criterion.

Use total FPL points scored as the official tie-breaker.

Do NOT use goal difference as a tie-breaker.

PREVIEW:

Preview two or three of the most interesting actual fixtures from the
following gameweek.

Use only fixtures supplied in the data.

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

There must be one match object for every match supplied for the
gameweek.
"""

    league_table = []

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

Here are the available H2H fixtures:

{json.dumps(
    matches,
    indent=2,
    ensure_ascii=False
)}

Remember:

- Use only the supplied information.
- Do not invent real-life football events.
- Cover every match for this gameweek.
- Use actual supplied fixtures for the preview.
- Use the official H2H points and FPL points tie-breaker.
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
    report_data = load_report_data()

    completed_gameweeks = data.get(
        "completed_gameweeks",
        []
    )

    existing_reports = data.get(
        "weekly_reports",
        {}
    )

    gameweeks = report_data.get(
        "gameweeks",
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

        if gameweek_key not in gameweeks:
            print(
                f"No report data available for "
                f"Gameweek {gameweek}. Skipping."
            )
            continue

        print(
            f"Gameweek {gameweek} is ready."
        )

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

            existing_reports[
                gameweek_key
            ] = ai_report

            data[
                "weekly_reports"
            ] = existing_reports

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
            f"Created {reports_created} new "
            f"AI report(s)."
        )


if __name__ == "__main__":
    main()
