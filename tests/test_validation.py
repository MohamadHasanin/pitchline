"""Is the silver data correct as football? Checked against StatsBomb's own match list."""

import json

import pandas as pd
import pytest

from pitchline.adapters.statsbomb import SILVER_DIR

pytestmark = pytest.mark.skipif(
    not SILVER_DIR.exists(), reason="no silver data, run `make silver` first"
)


@pytest.fixture(scope="session")
def events():
    """All silver events, read once, with kloppy's detailed result unpacked from `extra`."""
    df = pd.read_parquet(SILVER_DIR)
    df["result"] = df["extra"].map(lambda s: json.loads(s).get("result"))
    return df
