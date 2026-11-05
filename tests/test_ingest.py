import json

import pytest

from pitchline.ingest.statsbomb import EXPECTED_MATCHES, MATCH_FILES, MATCHES, RAW_DIR

pytestmark = pytest.mark.skipif(
    not (RAW_DIR / MATCHES).exists(), reason="no raw data, run `make ingest` first"
)


def load(rel):
    return json.loads((RAW_DIR / rel).read_bytes())


def test_match_list():
    assert len(load(MATCHES)) == EXPECTED_MATCHES


@pytest.mark.parametrize("kind", MATCH_FILES)
def test_one_file_per_match(kind):
    files = {int(p.stem) for p in (RAW_DIR / kind).glob("*.json")}
    assert files == {m["match_id"] for m in load(MATCHES)}


def test_no_partial_downloads():
    assert not list(RAW_DIR.rglob("*.tmp"))


def test_file_contents():
    for m in load(MATCHES):
        match_id = m["match_id"]
        assert load(f"events/{match_id}.json"), match_id
        assert len(load(f"lineups/{match_id}.json")) == 2, match_id
        assert load(f"three-sixty/{match_id}.json"), match_id
