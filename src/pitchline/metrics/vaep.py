"""VAEP (Decroos et al., 2019): value each action by how it changes the chances of scoring and
conceding soon, using models trained on SPADL actions.

Shootout actions (period 5) are left out: a shootout isn't open play and doesn't change the
score.
"""

import pandas as pd

SHOTS = ("shot", "shot_penalty", "shot_freekick")
WINDOW = 10  # "soon" = this action or one of the next 9, as in the VAEP paper


def labels(actions: pd.DataFrame) -> pd.DataFrame:
    """For each action: does the acting team score (`scores`) or concede (`concedes`) soon?

    Windows stay within one game and period; an own goal counts for the other team.
    """
    goal = actions["type_name"].isin(SHOTS) & (actions["result_name"] == "success")
    own_goal = actions["result_name"] == "owngoal"
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
