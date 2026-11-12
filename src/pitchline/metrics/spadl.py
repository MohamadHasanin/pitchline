"""SPADL actions from canonical events, compatible with socceraction's SPADL format.

SPADL (Decroos et al., 2019) describes on-ball actions with one vocabulary for every provider.
Its pitch is 105 x 68 m with the acting team attacking left to right, which is exactly the
canonical frame in schema.py, so coordinates carry over unchanged.
"""

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
