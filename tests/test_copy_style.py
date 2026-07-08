"""User-facing copy style tests."""

from advoi.copy_style import plain_copy
from advoi.decision.frames import FRAMES


def test_plain_copy_strips_em_dash():
    assert plain_copy("Option A \u2014 Fleet") == "Option A , Fleet"


def test_frame_labels_have_no_em_dash():
    for frame in FRAMES:
        assert "\u2014" not in frame.label
        assert "\u2013" not in frame.label