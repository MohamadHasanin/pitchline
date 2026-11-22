"""SPADL actions from canonical events, compatible with socceraction's SPADL format.

SPADL (Decroos et al., 2019) describes on-ball actions with one vocabulary for every provider.
Its pitch is 105 x 68 m with the acting team attacking left to right, which is exactly the
canonical frame in schema.py, so coordinates carry over unchanged.
"""

import json

import pandas as pd
import pandera.pandas as pa
from pandera.typing import Series

from pitchline.schema import PITCH_LENGTH, PITCH_WIDTH

# socceraction's vocabularies (socceraction/spadl/config.py, MIT licence); an id is the
# position in the tuple, so the order must not change.
ACTION_TYPES = (
    "pass",
    "cross",
    "throw_in",
    "freekick_crossed",
    "freekick_short",
    "corner_crossed",
    "corner_short",
    "take_on",
    "foul",
    "tackle",
    "interception",
    "shot",
    "shot_penalty",
    "shot_freekick",
    "keeper_save",
    "keeper_claim",
    "keeper_punch",
    "keeper_pick_up",
    "clearance",
    "bad_touch",
    "non_action",
    "dribble",
    "goalkick",
)
RESULTS = ("fail", "success", "offside", "owngoal", "yellow_card", "red_card")
BODY_PARTS = ("foot", "head", "other", "head/other", "foot_left", "foot_right")

# Canonical event types that map to one SPADL type; others need a rule or are dropped.
SIMPLE_TYPES = {
    "carry": "dribble",
    "take_on": "take_on",
    "interception": "interception",
    "clearance": "clearance",
    "foul_committed": "foul",
    "miscontrol": "bad_touch",
}
KEEPER_TYPES = {
    "save": "keeper_save",
    "smother": "keeper_save",
    "reflex": "keeper_save",
    "save_attempt": "keeper_save",
    "claim": "keeper_claim",
    "punch": "keeper_punch",
    "pick_up": "keeper_pick_up",
}


def action_type(event: dict, extra: dict) -> str | None:
    """SPADL type of one canonical event (a silver row), or None if SPADL has no action for it."""
    kind, set_piece = event["event_type"], event["set_piece_type"]
    cross = extra.get("pass_type") == "cross"
    # as in socceraction: a corner or free kick counts as crossed if it's a cross or a high pass
    crossed = cross or extra.get("pass_height") == "high"
    if kind == "pass":
        if event["outcome"] not in ("success", "fail"):
            return None  # "Unknown" passes aren't part of play; socceraction drops them too
        if set_piece == "throw_in":
            return "throw_in"
        if set_piece == "goal_kick":
            return "goalkick"
        if set_piece == "corner_kick":
            return "corner_crossed" if crossed else "corner_short"
        if set_piece == "free_kick":
            return "freekick_crossed" if crossed else "freekick_short"
        return "cross" if cross else "pass"  # kick-offs are ordinary passes in SPADL
    if kind == "shot":
        if extra.get("result") == "own_goal":
            return "bad_touch"  # as in socceraction: an own goal is a bad touch by the defender
        if set_piece == "penalty":
            return "shot_penalty"
        if set_piece == "free_kick":
            return "shot_freekick"
        return "shot"
    if kind == "duel":
        return "tackle" if extra.get("duel") == "ground" else None  # aerial duels aren't actions
    if kind == "goalkeeper":
        return KEEPER_TYPES.get(extra.get("keeper"))
    return SIMPLE_TYPES.get(kind)  # pressure, recovery, generic, card, ball_out, ... -> None


CARD_RESULTS = {"first_yellow": "yellow_card", "second_yellow": "yellow_card", "red": "red_card"}
FOOT = {"right_foot": "foot_right", "left_foot": "foot_left", "drop_kick": "foot"}


def action_result(event: dict, extra: dict, action: str, card: str | None = None) -> str:
    """SPADL result; `card` is the colour of the card a foul led to, if any."""
    if extra.get("result") == "own_goal":
        return "owngoal"
    if extra.get("result") == "offside":
        return "offside"
    if action == "foul":
        return CARD_RESULTS.get(card, "fail")  # a foul without a card is a fail
    if action == "bad_touch":
        return "fail"
    return "fail" if event["outcome"] == "fail" else "success"  # no outcome counts as success


def action_bodypart(event: dict, action: str) -> str:
    """SPADL body part; socceraction's defaults when the provider records none."""
    part = event["body_part"]
    if action == "throw_in":
        return "other"
    if not isinstance(part, str):  # missing
        return "other" if action.startswith("keeper") else "foot"
    if "head" in part:
        return "head"
    return FOOT.get(part, "other")  # hands, chest, keeper arm, ...


class ActionSchema(pa.DataFrameModel):
    """One row per SPADL action, in socceraction's column layout (ids plus readable names)."""

    game_id: Series[str]
    original_event_id: Series[str]  # the silver event it came from
    action_id: Series[int] = pa.Field(ge=0)  # order within the game
    period_id: Series[int] = pa.Field(ge=1, le=5)
    time_seconds: Series[float] = pa.Field(ge=0)  # from the start of the period
    team_id: Series[str]
    player_id: Series[str]
    start_x: Series[float] = pa.Field(ge=0, le=PITCH_LENGTH)
    start_y: Series[float] = pa.Field(ge=0, le=PITCH_WIDTH)
    end_x: Series[float] = pa.Field(ge=0, le=PITCH_LENGTH)
    end_y: Series[float] = pa.Field(ge=0, le=PITCH_WIDTH)
    type_id: Series[int] = pa.Field(ge=0, lt=len(ACTION_TYPES))
    type_name: Series[str] = pa.Field(isin=ACTION_TYPES)
    result_id: Series[int] = pa.Field(ge=0, lt=len(RESULTS))
    result_name: Series[str] = pa.Field(isin=RESULTS)
    bodypart_id: Series[int] = pa.Field(ge=0, lt=len(BODY_PARTS))
    bodypart_name: Series[str] = pa.Field(isin=BODY_PARTS)

    class Config:
        strict = True
        coerce = True
        unique = ["game_id", "action_id"]


def to_actions(events: pd.DataFrame) -> pd.DataFrame:
    """SPADL actions for one match's canonical events (silver), validated by ActionSchema."""
    extras = events["extra"].map(json.loads)
    # a foul's card is on a separate "card-<foul id>" row (see the adapter)
    cards = {
        event_id.removeprefix("card-"): extra["card"]
        for event_id, extra in zip(events["event_id"], extras, strict=True)
        if "card" in extra
    }
    rows = []
    for event, extra in zip(events.to_dict("records"), extras, strict=True):
        action = action_type(event, extra)
        if action is None:
            continue
        result = action_result(event, extra, action, cards.get(event["event_id"]))
        bodypart = action_bodypart(event, action)
        moved = pd.notna(event["end_x"])  # actions that don't move the ball end where they start
        rows.append(
            {
                "game_id": event["match_id"],
                "original_event_id": event["event_id"],
                "period_id": event["period"],
                "time_seconds": event["timestamp_s"],
                "team_id": event["team_id"],
                "player_id": event["player_id"],
                "start_x": event["x"],
                "start_y": event["y"],
                "end_x": event["end_x"] if moved else event["x"],
                "end_y": event["end_y"] if moved else event["y"],
                "type_id": ACTION_TYPES.index(action),
                "type_name": action,
                "result_id": RESULTS.index(result),
                "result_name": result,
                "bodypart_id": BODY_PARTS.index(bodypart),
                "bodypart_name": bodypart,
            }
        )
    actions = pd.DataFrame(rows)
    actions.insert(2, "action_id", range(len(actions)))
    return ActionSchema.validate(actions)
