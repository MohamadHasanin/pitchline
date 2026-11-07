"""Convert raw StatsBomb files into canonical events (data/silver), validated by EventSchema."""

from pathlib import Path

from kloppy.domain import Dimension, MetricPitchDimensions

from pitchline.schema import PITCH_LENGTH, PITCH_WIDTH

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
