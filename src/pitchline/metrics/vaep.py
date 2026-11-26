"""VAEP (Decroos et al., 2019): value each action by how it changes the chances of scoring and
conceding soon, using models trained on SPADL actions.

Shootout actions (period 5) are left out: a shootout isn't open play and doesn't change the
score.
"""

import numpy as np
import pandas as pd

from pitchline.metrics.spadl import ACTION_TYPES, BODY_PARTS, RESULTS
from pitchline.schema import PITCH_LENGTH, PITCH_WIDTH

SHOTS = ("shot", "shot_penalty", "shot_freekick")
WINDOW = 10  # "soon" = this action or one of the next 9, as in the VAEP paper
STATE = 3  # a game state is this action (a0) and the two before it (a1, a2)
PERIOD_START_MIN = {1: 0, 2: 45, 3: 90, 4: 105}  # minutes of play before each period


def goals(actions: pd.DataFrame) -> tuple[pd.Series, pd.Series]:
    """(goal, own_goal) flags per action; an own goal counts for the other team."""
    goal = actions["type_name"].isin(SHOTS) & (actions["result_name"] == "success")
    return goal, actions["result_name"] == "owngoal"


def labels(actions: pd.DataFrame) -> pd.DataFrame:
    """For each action: does the acting team score (`scores`) or concede (`concedes`) soon?

    Windows stay within one game and period; an own goal counts for the other team.
    """
    goal, own_goal = goals(actions)
    keys = [actions["game_id"], actions["period_id"]]
    scores = pd.Series(False, index=actions.index)
    concedes = pd.Series(False, index=actions.index)
    for k in range(WINDOW):  # look k actions ahead
        team = actions["team_id"].groupby(keys).shift(-k)  # missing past the end of the period
        same = team == actions["team_id"]
        other = team.notna() & ~same
        goal_k = goal.groupby(keys).shift(-k, fill_value=False)
        own_k = own_goal.groupby(keys).shift(-k, fill_value=False)
        scores |= (goal_k & same) | (own_k & other)
        concedes |= (goal_k & other) | (own_k & same)
    return pd.DataFrame({"scores": scores, "concedes": concedes})


def features(actions: pd.DataFrame) -> pd.DataFrame:
    """Game-state features for each action: its own description and the two before it.

    Every action is in its own team's frame (attacking left to right), so earlier actions by
    the other team are mirrored into the current team's frame. At the start of a period,
    missing earlier actions are filled with the current one, as in socceraction.
    """
    keys = [actions["game_id"], actions["period_id"]]
    cols = {}
    for i in range(STATE):
        a = actions if i == 0 else actions.groupby(keys).shift(i).fillna(actions)
        p = f"a{i}_"
        other = a["team_id"] != actions["team_id"]
        for name, vocab in (("type", ACTION_TYPES), ("result", RESULTS), ("bodypart", BODY_PARTS)):
            for value in vocab:
                cols[f"{p}{name}_{value}"] = a[f"{name}_name"] == value
        for point in ("start", "end"):
            x = np.where(other, PITCH_LENGTH - a[f"{point}_x"], a[f"{point}_x"])
            y = np.where(other, PITCH_WIDTH - a[f"{point}_y"], a[f"{point}_y"])
            dx, dy = PITCH_LENGTH - x, np.abs(PITCH_WIDTH / 2 - y)  # to the centre of the goal
            cols[f"{p}{point}_x"], cols[f"{p}{point}_y"] = x, y
            cols[f"{p}{point}_dist_to_goal"] = np.hypot(dx, dy)
            cols[f"{p}{point}_angle_to_goal"] = np.arctan2(dy, dx)
        if i > 0:
            cols[f"{p}same_team"] = ~other
            cols[f"{p}time_delta"] = actions["time_seconds"] - a["time_seconds"]
    # match context for the current action: when it happens, and the score before it
    cols["a0_period_id"] = actions["period_id"]
    cols["a0_time_seconds"] = actions["time_seconds"]
    cols["a0_time_seconds_overall"] = (
        actions["period_id"].map(PERIOD_START_MIN) * 60 + actions["time_seconds"]
    )
    cols.update(score_before(actions))
    return pd.DataFrame(cols, index=actions.index)


def score_before(actions: pd.DataFrame) -> dict[str, pd.Series]:
    """Goals of the acting team and of its opponent before each action, and the difference."""
    goal, own_goal = goals(actions)
    team = pd.Series(0, index=actions.index)
    opponent = pd.Series(0, index=actions.index)
    for _, game in actions.groupby("game_id"):
        for team_id in game["team_id"].unique():
            acting = game["team_id"] == team_id
            credited = (goal[game.index] & acting) | (own_goal[game.index] & ~acting)
            so_far = credited.cumsum() - credited  # goals before, not including this action
            team[game.index[acting]] = so_far[acting]
            opponent[game.index[~acting]] = so_far[~acting]
    return {
        "goalscore_team": team,
        "goalscore_opponent": opponent,
        "goalscore_diff": team - opponent,
    }
