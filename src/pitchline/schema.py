"""Canonical event schema: the contract every provider adapter's output must pass."""

from kloppy.domain import BodyPart, EventType, SetPieceType

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
