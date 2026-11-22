"""Expected threat (xT): how much a move raises the chance of scoring in the next few actions.

Grid source (xt_grid.json)
--------------------------
- Author: Karun Singh, who introduced xT in "Introducing Expected Threat (xT)",
  https://karun.in/blog/expected-threat.html
- File: https://karun.in/blog/data/open_xt_12x8_v1.json, downloaded 2026-11-23, unchanged.
- Fitted on all matches of the 2017/18 Premier League season, so it reflects that league,
  not Euro 2024; with far more data than 51 matches, it's the more stable choice.
- Licence: none stated; it's published openly and is credited here and in the README.
- Layout: 8 rows across the pitch (width) by 12 columns along it (length), with the team in
  possession attacking left to right, as in the canonical frame. Each value is the chance
  that having the ball in that zone leads to a goal soon.
- To update: download the file again over xt_grid.json and re-run the xT tests.
"""

import json
from functools import cache
from pathlib import Path

import numpy as np
import pandas as pd

from pitchline.schema import PITCH_LENGTH, PITCH_WIDTH

GRID_FILE = Path(__file__).with_name("xt_grid.json")

# As in socceraction: only successful moves (the ball reaches a teammate, or the carrier keeps
# it) change the threat; other actions get 0.
MOVES = ("pass", "cross", "dribble")


@cache
def load_grid() -> np.ndarray:
    """The xT grid as an (8, 12) array: grid[row across the width, column along the length]."""
    return np.array(json.loads(GRID_FILE.read_text()))


def threat(x: pd.Series, y: pd.Series) -> np.ndarray:
    """Grid value of the zone each (x, y) falls in; points on the far edges use the last zone."""
    grid = load_grid()
    rows, cols = grid.shape
    col = np.clip((x / PITCH_LENGTH * cols).astype(int), 0, cols - 1)
    row = np.clip((y / PITCH_WIDTH * rows).astype(int), 0, rows - 1)
    return grid[row, col]


def xt(actions: pd.DataFrame) -> pd.Series:
    """xT added by each SPADL action: threat(end) - threat(start) for successful moves, else 0."""
    moved = actions["type_name"].isin(MOVES) & (actions["result_name"] == "success")
    start = threat(actions["start_x"], actions["start_y"])
    end = threat(actions["end_x"], actions["end_y"])
    return pd.Series(np.where(moved, end - start, 0.0), index=actions.index, name="xt")
