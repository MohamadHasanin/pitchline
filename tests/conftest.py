import json

from pitchline.ingest.statsbomb import MATCHES, RAW_DIR

MATCH_LIST = RAW_DIR / MATCHES


def pytest_generate_tests(metafunc):
    """Run every test that takes a `match` argument once per match in the raw match list."""
    if "match" in metafunc.fixturenames:
        matches = json.loads(MATCH_LIST.read_bytes()) if MATCH_LIST.exists() else []
        metafunc.parametrize("match", matches, ids=match_name)


def match_name(match):
    return f"{match['home_team']['home_team_name']}-{match['away_team']['away_team_name']}"
