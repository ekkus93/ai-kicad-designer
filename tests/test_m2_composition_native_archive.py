"""Mutation tests for independently SHA-verified native KiCad SVG archives."""

import base64
import gzip
import hashlib

import pytest

from ai_kicad.m2_composition_native_archive import verify_native_render_parts


def _part(number, case):
    svg = b"<svg></svg>"
    return {
        "schema": "m2h2.native-render-archive.1",
        "qualification_head": "a" * 40,
        "archive_part": number,
        "archive_parts": 2,
        "renders": [{
            "case": case,
            "encoding": "gzip+base64",
            "svg_sha256": hashlib.sha256(svg).hexdigest(),
            "data": base64.b64encode(gzip.compress(svg, mtime=0)).decode(),
        }],
    }


def test_inventory_is_order_invariant_and_checks_every_svg():
    first, second = _part(1, "one"), _part(2, "two")
    assert verify_native_render_parts((first, second)) == verify_native_render_parts(
        (second, first)
    )


@pytest.mark.parametrize("mutation", ("digest", "part", "case", "head", "payload"))
def test_mutations_are_rejected(mutation):
    first, second = _part(1, "one"), _part(2, "two")
    if mutation == "digest":
        first["renders"][0]["svg_sha256"] = "0" * 64
    elif mutation == "part":
        second["archive_part"] = 1
    elif mutation == "case":
        second["renders"][0]["case"] = "one"
    elif mutation == "head":
        second["qualification_head"] = "b" * 40
    else:
        first["renders"][0]["data"] = "not-base64!"
    with pytest.raises(ValueError):
        verify_native_render_parts((first, second))
