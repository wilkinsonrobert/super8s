import json
import urllib.request

LEAGUE_ID = 54930


def get_json(url):
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read().decode("utf-8"))


def get_h2h_matches(league_id):
    url = (
        f"https://fantasy.premierleague.com/api/"
        f"leagues-h2h-matches/league/{league_id}/?page=1"
    )
    return get_json(url)


def get_fpl_players():
    url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    return get_json(url)


if __name__ == "__main__":
    matches = get_h2h_matches(LEAGUE_ID)
    players = get_fpl_players()

    print(f"Retrieved {len(matches['results'])} H2H matches")
    print(f"Retrieved {len(players['elements'])} players")
