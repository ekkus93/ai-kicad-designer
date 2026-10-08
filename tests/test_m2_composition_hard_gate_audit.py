import pytest

from ai_kicad.m2_composition_hard_gate_audit import (
    EXPECTED_HARD_GATES,
    audit_hard_gates,
)

_SHA = "a" * 40


def test_expected_hard_gates_pass_without_findings() -> None:
    audit = audit_hard_gates(_SHA, dict(EXPECTED_HARD_GATES))

    assert audit.passed
    assert audit.findings == ()


def test_weakened_conductor_or_spread_gate_blocks_closure() -> None:
    observed = dict(EXPECTED_HARD_GATES)
    observed["canonical_conductor_length_mm"] = 300
    observed["content_spread_width_mm"] = 220

    audit = audit_hard_gates(_SHA, observed)

    assert not audit.passed
    assert [finding.gate for finding in audit.findings] == [
        "canonical_conductor_length_mm",
        "content_spread_width_mm",
    ]


def test_cp_sat_local_and_legacy_openclaw_guards_are_explicit() -> None:
    observed = dict(EXPECTED_HARD_GATES)
    observed["cp_sat_absent"] = False
    observed["local_ignored"] = False
    observed["legacy_openclaw_unused"] = False

    audit = audit_hard_gates(_SHA, observed)

    assert not audit.passed
    assert {finding.gate for finding in audit.findings} == {
        "cp_sat_absent",
        "local_ignored",
        "legacy_openclaw_unused",
    }


def test_audit_json_is_deterministic() -> None:
    first = audit_hard_gates(_SHA, dict(EXPECTED_HARD_GATES))
    second = audit_hard_gates(_SHA, dict(reversed(tuple(EXPECTED_HARD_GATES.items()))))

    assert first.canonical_json() == second.canonical_json()


def test_source_sha_is_validated() -> None:
    with pytest.raises(ValueError, match="source_sha"):
        audit_hard_gates("not-a-sha", dict(EXPECTED_HARD_GATES))
