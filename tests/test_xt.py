import pandas as pd
import pytest

from pitchline.metrics.xt import load_grid, threat, xt


def action(type_name, result_name, start, end):
    """A one-row SPADL actions table with just the columns xt() reads."""
    return pd.DataFrame(
        {
            "type_name": [type_name],
            "result_name": [result_name],
            "start_x": [start[0]],
            "start_y": [start[1]],
            "end_x": [end[0]],
            "end_y": [end[1]],
        }
    )


def test_grid_is_8_by_12_probabilities():
    grid = load_grid()
    assert grid.shape == (8, 12)
    assert ((grid > 0) & (grid < 1)).all()


def test_threat_on_pitch_edges_uses_the_edge_zones():
    grid = load_grid()
    corners = threat(pd.Series([0.0, 105.0]), pd.Series([0.0, 68.0]))
    assert list(corners) == [grid[0, 0], grid[-1, -1]]
    assert threat(pd.Series([104.0]), pd.Series([34.0]))[0] == grid.max()  # in front of goal


def test_forward_pass_gains_and_backward_pass_loses():
    into_box = xt(action("pass", "success", (60, 34), (95, 34)))[0]
    backward = xt(action("pass", "success", (60, 34), (30, 34)))[0]
    assert into_box > 0 > backward


@pytest.mark.parametrize(
    "type_name, result_name",
    [("pass", "fail"), ("shot", "success"), ("tackle", "success"), ("corner_crossed", "success")],
)
def test_only_successful_moves_get_xt(type_name, result_name):
    assert xt(action(type_name, result_name, (60, 34), (95, 34)))[0] == 0
