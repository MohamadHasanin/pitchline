"""Canonical event schema: the contract every provider adapter's output must pass."""

import pandera.pandas as pa
from kloppy.domain import BodyPart, EventType, SetPieceType
from pandera.typing import Series

# Vocabularies are kloppy's enums, lowercased, so any kloppy-supported source maps directly.
EVENT_TYPES = tuple(e.name.lower() for e in EventType)
BODY_PARTS = tuple(e.name.lower() for e in BodyPart)
SET_PIECE_TYPES = tuple(e.name.lower() for e in SetPieceType)
OUTCOMES = ("success", "fail")

# Coordinate frame: a standard 105 x 68 m pitch (FIFA's recommended size, also used by SPADL).
# Providers each use their own system (StatsBomb 120 x 80, Wyscout/Opta 0-100, kloppy 0-1),
# so every adapter must rescale to this frame and orient it so the team in possession
# attacks left to right. Origin (0, 0) is a corner; x runs along the length, y across the width.
# Values are standardized metres: real pitch sizes vary and providers don't record them.
PITCH_LENGTH = 105.0
PITCH_WIDTH = 68.0


class EventSchema(pa.DataFrameModel):
    """One row per on-ball or off-ball event, from any provider."""

    # Identity: provider IDs kept as strings; `source` says which provider they belong to.
    source: Series[str]
    match_id: Series[str]
    event_id: Series[str]

    # Time: periods 1-2 normal time, 3-4 extra time, 5 penalty shootout.
    period: Series[int] = pa.Field(ge=1, le=5)
    timestamp_s: Series[float] = pa.Field(ge=0)  # seconds from the start of the period

    # Who and what: player is null for team-level events (e.g. formation change).
    team_id: Series[str]
    player_id: Series[str] = pa.Field(nullable=True)
    event_type: Series[str] = pa.Field(isin=EVENT_TYPES)
    outcome: Series[str] = pa.Field(isin=OUTCOMES, nullable=True)  # null when not applicable

    # Where, in the pitch frame above: null when the provider has no location (e.g. substitution);
    # end_x/end_y only for events that move the ball (pass, carry, shot).
    x: Series[float] = pa.Field(ge=0, le=PITCH_LENGTH, nullable=True)
    y: Series[float] = pa.Field(ge=0, le=PITCH_WIDTH, nullable=True)
    end_x: Series[float] = pa.Field(ge=0, le=PITCH_LENGTH, nullable=True)
    end_y: Series[float] = pa.Field(ge=0, le=PITCH_WIDTH, nullable=True)

    # Details: null when the provider doesn't record them or they don't apply.
    body_part: Series[str] = pa.Field(isin=BODY_PARTS, nullable=True)
    set_piece_type: Series[str] = pa.Field(isin=SET_PIECE_TYPES, nullable=True)
    xg: Series[float] = pa.Field(ge=0, le=1, nullable=True)  # provider xG, shots only
    extra: Series[str] = pa.Field(nullable=True)  # JSON object of provider-only fields

    class Config:
        strict = True  # reject columns not defined above
        coerce = True  # convert to the declared types (e.g. int IDs to str); fail if impossible
        unique = ["source", "match_id", "event_id"]  # one row per event
