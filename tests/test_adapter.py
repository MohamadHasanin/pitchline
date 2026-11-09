import pandas as pd
import pytest

from pitchline.adapters.statsbomb import SILVER_DIR, SOURCE
from pitchline.schema import EventSchema

pytestmark = pytest.mark.skipif(
    not SILVER_DIR.exists(), reason="no silver data, run `make silver` first"
)


def test_one_file_per_match(matches):
    assert {int(p.stem) for p in SILVER_DIR.glob("*.parquet")} == {m["match_id"] for m in matches}


def test_match_passes_schema(match):
    events = EventSchema.validate(pd.read_parquet(SILVER_DIR / f"{match['match_id']}.parquet"))
    assert (events["source"] == SOURCE).all()
    assert (events["match_id"] == str(match["match_id"])).all()
