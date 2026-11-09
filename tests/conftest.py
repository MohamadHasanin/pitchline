import json

import pytest

from pitchline.ingest.statsbomb import MATCHES, RAW_DIR

MATCH_LIST = RAW_DIR / MATCHES


def load_matches():
    return json.loads(MATCH_LIST.read_bytes()) if MATCH_LIST.exists() else []


@pytest.fixture(scope="session")
def matches():
    """The whole raw match list, for tests that check all matches at once."""
    return load_matches()


def match_name(match):
    return f"{match['home_team']['home_team_name']}-{match['away_team']['away_team_name']}"


@pytest.fixture(params=load_matches(), ids=match_name)
def match(request):
    """One match from the raw match list; tests using it run once per match."""
    return request.param
