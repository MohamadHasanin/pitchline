import json

import pandas as pd
import pytest
from pandera.errors import SchemaError, SchemaErrors

from pitchline.schema import EventSchema


@pytest.fixture
def events():
    """A pass, a shot and a team-level event with no player, location or details."""
    return pd.DataFrame(
        {
            "source": ["statsbomb"] * 3,
            "match_id": ["3930159"] * 3,
            "event_id": ["e1", "e2", "e3"],
            "period": [1, 1, 2],
            "timestamp_s": [0.31, 79.34, 0.0],
            "team_id": ["914", "914", "773"],
            "player_id": ["5574", "6001", None],
            "event_type": ["pass", "shot", "formation_change"],
            "outcome": ["success", "fail", None],
            "x": [52.5, 96.8, None],
            "y": [34.0, 23.5, None],
            "end_x": [35.9, 102.2, None],
            "end_y": [24.5, 30.6, None],
            "body_part": ["right_foot", "right_foot", None],
            "set_piece_type": ["kick_off", None, None],
            "xg": [None, 0.096, None],
            "extra": [json.dumps({"possession": 2}), json.dumps({"possession": 5}), None],
        }
    )


def test_valid_events_pass(events):
    EventSchema.validate(events)


def test_ids_are_coerced_to_strings(events):
    validated = EventSchema.validate(events.assign(match_id=3930159))
    assert (validated["match_id"] == "3930159").all()


@pytest.mark.parametrize(
    "break_it",
    [
        pytest.param(lambda df: df.assign(x=[120.0, 96.8, None]), id="x-off-pitch"),
        pytest.param(lambda df: df.assign(event_type="set_piece"), id="unknown-type"),
        pytest.param(lambda df: df.assign(possession=1), id="extra-column"),
        pytest.param(lambda df: df.drop(columns="xg"), id="missing-column"),
        pytest.param(lambda df: df.assign(event_id=["e1", "e1", "e3"]), id="duplicate-event"),
        pytest.param(lambda df: df.assign(team_id=["914", None, "773"]), id="null-team"),
    ],
)
def test_invalid_events_fail(events, break_it):
    with pytest.raises((SchemaError, SchemaErrors)):
        EventSchema.validate(break_it(events))
