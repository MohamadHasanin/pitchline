"""Is the silver data correct as football? Checked against StatsBomb's match list and lineups."""

import json

import pandas as pd
import pytest

from pitchline.adapters.statsbomb import SILVER_DIR
from pitchline.ingest.statsbomb import RAW_DIR

pytestmark = pytest.mark.skipif(
    not SILVER_DIR.exists(), reason="no silver data, run `make silver` first"
)


@pytest.fixture(scope="session")
def events():
    """All silver events, read once, with kloppy's detailed result unpacked from `extra`."""
    df = pd.read_parquet(SILVER_DIR)
    df["result"] = df["extra"].map(lambda s: json.loads(s).get("result"))
    return df


@pytest.fixture(scope="session")
def lineups(matches):
    """Raw lineups by match ID: a list of (player_id, player_name) per match, as strings."""
    return {
        str(m["match_id"]): [
            (str(p["player_id"]), p["player_name"])
            for team in json.loads((RAW_DIR / f"lineups/{m['match_id']}.json").read_bytes())
            for p in team["lineup"]
        ]
        for m in matches
    }


def of_match(events, match):
    return events[events["match_id"] == str(match["match_id"])]


def team_ids(match):
    """(home, away) team IDs as the strings silver uses."""
    return str(match["home_team"]["home_team_id"]), str(match["away_team"]["away_team_id"])


def test_goals_match_final_score(match, events):
    play = of_match(events, match).query("period < 5")  # a shootout doesn't change the score
    home, away = team_ids(match)

    def goals(team, opponent):  # own goals count for the opponent
        scored = (play["team_id"] == team) & (play["result"] == "goal")
        own = (play["team_id"] == opponent) & (play["result"] == "own_goal")
        return int(scored.sum() + own.sum())

    assert (goals(home, away), goals(away, home)) == (match["home_score"], match["away_score"])


def test_two_teams(match, events):
    assert set(of_match(events, match)["team_id"]) == set(team_ids(match))


def test_at_least_90_minutes(match, events):
    play = of_match(events, match).query("period < 5")
    # each period's length is its last event's time (timestamps restart at 0 every period)
    assert play.groupby("period")["timestamp_s"].max().sum() >= 90 * 60


def test_team_ids_are_consistent(matches):
    """Across all matches, each team ID always has the same name, and each name the same ID."""
    pairs = {
        (m[f"{side}_team"][f"{side}_team_id"], m[f"{side}_team"][f"{side}_team_name"])
        for m in matches
        for side in ("home", "away")
    }
    assert len(pairs) == len({i for i, _ in pairs}) == len({n for _, n in pairs})


def test_player_ids_are_consistent(lineups):
    """Across all lineups, each player ID always has the same name (namesakes are allowed)."""
    pairs = {pair for players in lineups.values() for pair in players}
    assert len(pairs) == len({i for i, _ in pairs})


def test_players_are_in_lineup(match, events, lineups):
    in_events = set(of_match(events, match)["player_id"].dropna())
    assert in_events <= {i for i, _ in lineups[str(match["match_id"])]}
