"""Convert raw StatsBomb files into canonical events (data/silver), validated by EventSchema."""

import json
from pathlib import Path

import pandas as pd
from kloppy import statsbomb
from kloppy.domain import (
    BodyPartQualifier,
    Dimension,
    Event,
    EventDataset,
    EventType,
    ExpectedGoals,
    MetricPitchDimensions,
    Orientation,
    Point,
    SetPieceQualifier,
)

from pitchline.ingest.statsbomb import MATCHES, RAW_DIR
from pitchline.schema import PITCH_LENGTH, PITCH_WIDTH, EventSchema

SOURCE = "statsbomb"
SILVER_DIR = Path("data/silver/events") / SOURCE

# The canonical pitch frame from schema.py, in the form kloppy's transform() expects.
PITCH = MetricPitchDimensions(
    x_dim=Dimension(0, PITCH_LENGTH),
    y_dim=Dimension(0, PITCH_WIDTH),
    pitch_length=PITCH_LENGTH,
    pitch_width=PITCH_WIDTH,
    standardized=True,
)

# kloppy results (PassResult, ShotResult, DuelResult, ...) that count as a success;
# every other result is a fail, and events without a result get no outcome.
SUCCESS_RESULTS = {"COMPLETE", "GOAL", "WON", "SUCCESS"}

# Provider locations can sit just off the pitch (e.g. a corner recorded at x=120.1 of 120).
# Values within this many metres of an edge are moved onto it; anything further is left
# unchanged so EventSchema rejects it as a real error.
EDGE_TOLERANCE = 1.0


def load_match(match_id: int) -> EventDataset:
    """Read one match's raw events and lineups with kloppy, in the canonical pitch frame."""
    dataset = statsbomb.load(
        event_data=RAW_DIR / f"events/{match_id}.json",
        lineup_data=RAW_DIR / f"lineups/{match_id}.json",
    )
    return dataset.transform(
        to_pitch_dimensions=PITCH, to_orientation=Orientation.ACTION_EXECUTING_TEAM
    )


def outcome(event: Event) -> str | None:
    if event.result is None:
        return None
    return "success" if event.result.name in SUCCESS_RESULTS else "fail"


def qualifier(event: Event, kind: type) -> str | None:
    """Value of the event's first qualifier of `kind` (e.g. BodyPartQualifier), lowercased."""
    for q in event.qualifiers or []:
        if isinstance(q, kind):
            return q.value.name.lower()
    return None


def on_pitch(value: float, upper: float) -> float:
    """Move `value` onto the [0, upper] range if it's within EDGE_TOLERANCE of an edge."""
    if -EDGE_TOLERANCE <= value < 0:
        return 0.0
    if upper < value <= upper + EDGE_TOLERANCE:
        return upper
    return value


def end_point(event: Event) -> Point | None:
    """Where the ball ended up; kloppy names it differently per event type."""
    for attr in ("receiver_coordinates", "end_coordinates", "result_coordinates"):
        if point := getattr(event, attr, None):
            return point
    return None


def xg(event: Event) -> float | None:
    """Provider xG, shots only: kloppy copies it onto duels it derives from a shot."""
    if event.event_type != EventType.SHOT:
        return None
    return next((s.value for s in event.statistics or [] if isinstance(s, ExpectedGoals)), None)


def extra(event: Event, event_id: str) -> str:
    """StatsBomb-only fields as JSON; derived events (ids like "out-<id>", "card-<id>") carry
    their source event's raw data, so they only keep the possession number."""
    raw = event.raw_event
    fields = {"possession": raw["possession"]}
    if event_id == raw["id"]:
        fields["type"] = raw["type"]["name"]
        if raw.get("under_pressure"):
            fields["under_pressure"] = True
    if event.result is not None:
        fields["result"] = event.result.name.lower()
    if card := getattr(event, "card_type", None):  # only on card events
        fields["card"] = card.name.lower()  # first_yellow, second_yellow or red
    return json.dumps(fields)


def to_canonical(dataset: EventDataset, match_id: int) -> pd.DataFrame:
    """One row per kloppy event, with exactly the EventSchema columns."""
    rows, seen = [], set()
    for e in dataset.events:
        # kloppy splits a foul with a card into two events sharing one id; prefix the second
        # with its type ("card-<id>"), like kloppy's own derived events ("out-<id>").
        event_id = e.event_id
        if event_id in seen:
            event_id = f"{e.event_type.name.lower()}-{event_id}"
        seen.add(event_id)

        start, end = e.coordinates, end_point(e)
        rows.append(
            {
                "source": SOURCE,
                "match_id": str(match_id),
                "event_id": event_id,
                "period": e.period.id,
                "timestamp_s": e.timestamp.total_seconds(),
                "team_id": e.team.team_id,
                "player_id": e.player.player_id if e.player else None,
                "event_type": e.event_type.name.lower(),
                "outcome": outcome(e),
                "x": on_pitch(start.x, PITCH_LENGTH) if start else None,
                "y": on_pitch(start.y, PITCH_WIDTH) if start else None,
                "end_x": on_pitch(end.x, PITCH_LENGTH) if end else None,
                "end_y": on_pitch(end.y, PITCH_WIDTH) if end else None,
                "body_part": qualifier(e, BodyPartQualifier),
                "set_piece_type": qualifier(e, SetPieceQualifier),
                "xg": xg(e),
                "extra": extra(e, event_id),
            }
        )
    return pd.DataFrame(rows)


def write_match(match_id: int) -> Path:
    """Convert one match, validate it against EventSchema, and write it as Parquet."""
    events = EventSchema.validate(to_canonical(load_match(match_id), match_id))
    path = SILVER_DIR / f"{match_id}.parquet"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    events.to_parquet(tmp, index=False)
    tmp.replace(path)  # atomic: a crash never leaves a partial file at `path`
    return path


def adapt() -> None:
    """Rebuild silver events for every match in the raw match list."""
    matches = json.loads((RAW_DIR / MATCHES).read_bytes())
    for i, m in enumerate(matches, start=1):
        path = write_match(m["match_id"])
        print(f"[{i}/{len(matches)}] {path}")


if __name__ == "__main__":
    adapt()
