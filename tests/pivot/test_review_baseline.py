"""Injected-defect labels and the hand-check sample (REVIEWER_LOOP_SPEC.md R6.2)."""

from tools.pivot.build_review_baseline import hand_check_sample, injected_label, rating_page

TEXT = """(kicad_sch (symbol (lib_id "Device:R") (at 50 50 0) (unit 1)
  (property "Reference" "R1" (at 52.54 50 0)) (property "Value" "10k" (at 52.54 52.54 0))))"""
BASE = {"revision": "sha256:a", "image_sha256": ["p"], "checks": {"field_locality": "PASS"}}


def _label(case, kind, after, action=None):
    action = action or {
        "operation": "move_field",
        "reference": "R1",
        "unit": 1,
        "field": "Value",
        "x_mm": 80.0,
        "y_mm": 52.54,
        "angle": 0,
    }
    return injected_label(case, "d", kind, action, BASE, after, TEXT)


def test_injected_label_comes_from_the_manifest_and_is_verified():
    after = {"revision": "sha256:b", "image_sha256": ["q"], "checks": {"field_locality": "FAIL"}}
    label = _label("d__detached_value", "detached_value", after)
    assert label["part"] == {"reference": "R1", "unit": 1, "field": "Value"}
    assert label["location"]["from_mm"] == [52.54, 52.54]
    assert label["label_source"] == "injection_manifest"
    assert label["verification"]["moved_mm"] == 27.46
    assert label["verification"]["checks_changed"] == ["field_locality"]
    assert label["positive_case"] is True


def test_injection_without_a_visible_change_is_not_a_positive_case():
    same_image = {"revision": "sha256:b", "image_sha256": ["p"], "checks": BASE["checks"]}
    label = _label("d__x", "detached_value", same_image)
    assert label["verification"]["observable"] is False and label["positive_case"] is False
    tiny = dict(
        operation="move_field",
        reference="R1",
        unit=1,
        field="Value",
        x_mm=53.0,
        y_mm=52.54,
        angle=0,
    )
    after = {"revision": "sha256:b", "image_sha256": ["q"], "checks": BASE["checks"]}
    assert _label("d__y", "detached_value", after, tiny)["positive_case"] is False


def test_sheet_translation_label():
    after = {"revision": "sha256:b", "image_sha256": ["q"], "checks": {"page_balance": "FAIL"}}
    move = {"operation": "translate_sheet", "dx_mm": 60.96, "dy_mm": -10.16}
    label = _label("d__off_balance_page", "off_balance_page", after, move)
    assert label["part"] == {"sheet": True}
    assert label["location"] == {"dx_mm": 60.96, "dy_mm": -10.16}


def test_hand_check_sample_is_stratified_and_includes_ambiguous_probes():
    labels = []
    for kind, count in (("detached_value", 15), ("off_balance_page", 1)):
        for n in range(count):
            changed = ["field_locality"] if n != 3 else []
            labels.append(
                {
                    "case": f"d{n}__{kind}",
                    "defect_type": kind,
                    "verification": {"observable": True, "checks_changed": changed},
                }
            )
    sample = hand_check_sample(labels)
    reasons = {item["case"]: item["reason"] for item in sample}
    detached = [case for case in reasons if case.endswith("detached_value")]
    assert len([c for c in detached if reasons[c] == "stratified sample"]) >= 3
    assert reasons["d3__detached_value"] == "ambiguous probe: no check changed"
    assert "d0__off_balance_page" in reasons
    assert all(item["status"] == "PENDING_OWNER_CHECK" for item in sample)


def test_rating_page_hides_design_names():
    page = rating_page([{"code": "B01", "images": ["drawings/rc_lowpass/review-images/a.png"]}])
    assert "Drawing B01" in page and "Save ratings as JSON" in page
    assert "baseline-ratings.v1" in page
