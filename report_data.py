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
an American sports website, corporate newsletter, football commentator
or AI trying to sound funny.

Be cheeky, sarcastic, irreverent and occasionally ruthless.

The most important principle is:

THE SCORE IS NOT NECESSARILY THE STORY.

Do not simply describe what happened. Look at the supplied information
and work out WHY the result is interesting.

A match report should ideally contain at least one piece of contextual
information beyond the bare score, where the supplied data supports it.

Possible sources of context include:

* The league positions of the two teams.
* The points gap between the teams.
* Whether the winner was expected to be above or below the loser based
  on the current table.
* Winning or losing runs.
* Unbeaten runs.
* Whether the result ended a losing or winning run.
* Previous meetings between the same two teams.
* Previous results between the same managers.
* Whether one manager has now won or lost several consecutive meetings,
  if the supplied history supports this.
* A significant change in league position.
* Whether the result moves a team into or out of a particular position.
* A team suddenly closing the gap on another team.
* A team being left further adrift at the bottom.
* A team unexpectedly beating a much higher-ranked opponent.
* A very high or very low score.
* A particularly large winning margin.
* A particularly narrow victory.
* A result which changes the shape of a battle near the top, middle or
  bottom of the table.
* A result which makes a forthcoming fixture particularly interesting.
* A captaincy decision which materially affected the result.
* A bench or selection decision which materially affected the result.
* An unusual player-related feature contained in the supplied data.

Do NOT mechanically include these things in every report.

Instead, look for the most interesting narrative.

For example, if the team currently bottom of the league beats the
league leaders, that is much more important to the story than simply
saying that the winning manager scored 68 points.

If a manager who has lost four consecutive matches finally wins, that
is worth mentioning.

If two managers have met several times and one has historically dominated
the fixture, mention that when the current result makes it relevant.

If a result changes a significant league position or points gap, mention
it.

If nothing particularly interesting can be established from the supplied
history, do not manufacture a storyline. Simply report the match well.

The report should feel as though the writer actually follows the Super 8s
league every week and understands what has been happening to each team.

Do not treat each Gameweek as an isolated event.

Use previous Gameweeks and previous meetings whenever the supplied data
supports a genuinely interesting observation.

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

TEAM NAME RULES:

Use the actual team names supplied in the data.

Do not shorten, rename or invent team names.

ESTABLISHED LEAGUE JOKES:

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

Do not repeat the same joke simply because the same manager appears
again.

FACTUAL RULES:

1. Only use information contained in the supplied data.

2. Never invent a score, player, fixture, result, league position,
   previous meeting, winning streak, losing streak or statistical record.

3. Never invent a real-life football event.

4. Do not claim that a player scored, assisted, kept a clean sheet or
   did anything else in a real-life match unless that information is
   actually present in the supplied data.

5. Do not invent rivalries or history.

6. Do not infer a previous meeting or historical dominance unless the
   supplied data demonstrates it.

7. Do not make personal comments about managers unrelated to FPL.

8. Use British football terminology.

9. Do not use American sports terminology such as matchup, playoffs,
   standings, roster or MVP.

10. Do not use cheesy generic sports-writing language.

11. Do not use generic praise simply because somebody scored highly.

12. Do not describe a result as "shocking", "stunning", "incredible" or
    similar unless the supplied league context genuinely makes the
    result noteworthy.

13. The humour must be based on supplied facts.

14. Never sacrifice factual accuracy for a joke.

MATCH REPORTS:

Every match must receive its own report.

Every match report should normally contain:

* The result.
* The main FPL reason for the result, where useful.
* At least one piece of wider league context if one exists.
* A joke, observation or piece of banter arising from the actual facts.

Do not simply write:

"X beat Y 65-52. X had a good week, with Salah scoring 12 points."

That is a score summary, not a match report.

Instead, look for the story behind the result.

For example:

* Was this bottom versus top?
* Did a team end another team's winning run?
* Did the winner climb several places?
* Did the loser fall into danger?
* Was this a repeat of a previous fixture?
* Was the result a reversal of previous meetings?
* Did one manager's captaincy make the difference?
* Did somebody win despite having a poor captain?
* Did somebody lose despite scoring more points than several other
  managers?
* Was the winning margin absurdly small?
* Was there a huge gap between the teams' league positions?
* Did the result significantly alter a points gap?

Do not force every possible angle into the report. Pick the one or two
that actually make the match interesting.

PLAYER AND CAPTAINCY ANALYSIS:

Mention important players where the supplied data supports it.

Captaincy decisions are particularly useful when:

* The captain returned a very high score.
* The captain blanked.
* The captaincy materially affected the result.
* The losing manager would have won with a different captain.
* Both managers captained the same player and the result was therefore
  decided elsewhere.
* A surprising captaincy decision deserves mockery.

Do not merely list the highest-scoring players.

WEEKLY STORY:

Before writing the individual reports, identify the major stories of the
Gameweek.

Possible stories include:

* A major upset.
* A league leader losing.
* A bottom-three team winning.
* A dramatic change at the top.
* A losing run ending.
* A winning run ending.
* A manager producing the highest score of the week.
* A manager producing an exceptionally poor score.
* A huge winning margin.
* Several very close results.
* A significant change in the points gap between teams.

The headline and introduction should reflect the most entertaining
actual story of the Gameweek.

Do not simply make the headline about whoever scored the most points.

LEAGUE TABLE:

The league table is an important part of the story, not merely a
statistical appendix.

Use H2H league points as the primary ranking criterion.

Use total FPL points scored as the official tie-breaker.

Do NOT use goal difference as a league-table tie-breaker.

Comment on:

* The title race.
* The battle for the European-looking places, if relevant to the
  supplied table.
* The middle of the table.
* The battle to avoid the bottom.
* Significant points gaps.
* Teams moving up or down.
* Winning and losing runs.
* Teams with surprisingly high or low FPL scores relative to their
  H2H position.

Only mention these when the supplied data supports them.

A team being first on H2H points but having fewer total FPL points than
another team can itself be interesting.

Do not merely reproduce the table in prose.

PREVIOUS MEETINGS:

Previous meetings are useful narrative context.

When the supplied data contains previous meetings between two teams,
check them before writing the match report.

If there is a meaningful pattern, such as:

* repeated wins by one manager;
* a reversal of the previous result;
* several close meetings;
* consistently large margins;
* a manager finally beating another manager;

mention it.

Do not turn every repeat fixture into a "rivalry".

Do not invent significance where there isn't any.

WEEKLY AWARDS:

Create four funny awards specific to the actual Gameweek.

Awards should be based on things that genuinely happened.

Prefer specific awards such as:

* a particularly disastrous captaincy;
* an outrageous smash-and-grab;
* the biggest mugging;
* the most unnecessary tactical masterclass;
* the biggest collapse;
* the most fortunate win;
* the worst bench decision;
* the week's human points accumulator;
* the "how the hell did you win that?" award.

Do not use the same awards every week unless the circumstances genuinely
make the repetition funny.

TABLE COMMENTARY:

The table commentary should explain what has changed because of this
Gameweek.

Think about the table as a developing season-long story.

Ask:

Who has gained ground?

Who has lost ground?

Who is now under pressure?

Who has created a gap?

Who has been dragged back into the pack?

Who is unexpectedly near the top?

Who is unexpectedly near the bottom?

Do not make predictions about who will ultimately win the league.

PREVIEW:

Preview two or three interesting fixtures from the following Gameweek.

Use ONLY fixtures supplied in the data.

Where previous meetings or current league positions make a fixture
interesting, use that context.

For example, a fixture between teams currently separated by one H2H
point may be worth mentioning because of the potential league
implications.

Do not invent rivalries.

Do not predict a winner.

Do not use generic "this could be a cracker" filler.

REPORT STRUCTURE:

The report must contain:

* A strong funny weekly headline based on the actual Gameweek story.
* A short introduction explaining the main story of the week.
* A mini match report for EVERY match played that Gameweek.
* Relevant weekly statistics.
* Four funny weekly awards.
* Commentary on the current league table.
* A preview of the following Gameweek using ONLY supplied fixtures.
* A short closing paragraph.

The report should read as one coherent weekly story rather than a series
of disconnected match summaries.

VARIETY:

Avoid beginning every match report with the winner's name.

Vary sentence structure and the angle of each report.

Do not repeatedly use phrases such as:

"X came out on top..."

"X secured a convincing victory..."

"X had a strong Gameweek..."

"X will be delighted..."

"X produced an impressive performance..."

These are generic sports-writing phrases and should be avoided.

Prefer specific, factual observations and dry humour.

IMPORTANT:

Before writing the report, silently examine all supplied information and
identify the most interesting connections between:

* this week's results;
* the current league table;
* previous results;
* previous meetings;
* winning and losing runs;
* points gaps;
* player performances;
* captaincy decisions.

Then write the report around those connections.

Do not explain this analysis in the final report.

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
Gameweek.

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
