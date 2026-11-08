import json

import pandas as pd
import pytest

from pitchline.adapters.statsbomb import SILVER_DIR, SOURCE
from pitchline.ingest.statsbomb import MATCHES, RAW_DIR
from pitchline.schema import EventSchema

MATCH_LIST = RAW_DIR / MATCHES
MATCHES_JSON = json.loads(MATCH_LIST.read_bytes()) if MATCH_LIST.exists() else []
MATCH_IDS = [m["match_id"] for m in MATCHES_JSON]

pytestmark = pytest.mark.skipif(
    not SILVER_DIR.exists(), reason="no silver data, run `make silver` first"
)


def test_one_file_per_match():
    assert {int(p.stem) for p in SILVER_DIR.glob("*.parquet")} == set(MATCH_IDS)


@pytest.mark.parametrize("match_id", MATCH_IDS)
def test_match_passes_schema(match_id):
    events = EventSchema.validate(pd.read_parquet(SILVER_DIR / f"{match_id}.parquet"))
    assert (events["source"] == SOURCE).all()
    assert (events["match_id"] == str(match_id)).all()
