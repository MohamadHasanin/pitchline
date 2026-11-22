import pandas as pd
import pytest

from pitchline.adapters.statsbomb import SILVER_DIR
from pitchline.metrics.spadl import to_actions

pytestmark = pytest.mark.skipif(
    not SILVER_DIR.exists(), reason="no silver data, run `make silver` first"
)

SHOTS = ("shot", "shot_penalty", "shot_freekick")


@pytest.fixture
def actions(match):
    """SPADL actions of one match; to_actions validates them against ActionSchema."""
    return to_actions(pd.read_parquet(SILVER_DIR / f"{match['match_id']}.parquet"))


def test_actions_belong_to_match(actions, match):
    assert len(actions) > 0
    assert (actions["game_id"] == str(match["match_id"])).all()


def test_goals_match_final_score(actions, match):
    play = actions[actions["period_id"] < 5]  # a shootout doesn't change the score
    home = str(match["home_team"]["home_team_id"])
    away = str(match["away_team"]["away_team_id"])

    def goals(team, opponent):  # own goals count for the opponent
        scored = play["type_name"].isin(SHOTS) & (play["result_name"] == "success")
        own = play["result_name"] == "owngoal"
        return int(
            (scored & (play["team_id"] == team)).sum() + (own & (play["team_id"] == opponent)).sum()
        )

    assert (goals(home, away), goals(away, home)) == (match["home_score"], match["away_score"])
