"""Tests for the FFmpeg SVG crop used by local schematic image review."""

import pytest

from ai_kicad.pivot.schematic_review_native import parse_ffmpeg_bbox


def test_parse_ffmpeg_bbox_extracts_visible_svg_region() -> None:
    output = (
        "[Parsed_bbox_0] n:0 pts:0 pts_time:0 x1:83 x2:396 y1:107 y2:337 "
        "w:314 h:231 crop=314:231:83:107 drawbox=83:107:314:231"
    )
    assert parse_ffmpeg_bbox(output) == (314, 231, 83, 107)


def test_parse_ffmpeg_bbox_uses_last_frame_measurement() -> None:
    output = "crop=10:20:1:2\nframe-two crop=30:40:5:6"
    assert parse_ffmpeg_bbox(output) == (30, 40, 5, 6)


def test_parse_ffmpeg_bbox_rejects_empty_svg() -> None:
    with pytest.raises(RuntimeError, match="find visible drawing content"):
        parse_ffmpeg_bbox("Output file is empty")
