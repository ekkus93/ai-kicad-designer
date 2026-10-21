"""Hard-gate preservation audit for M2h2 composition remediation.

Human-readable composition work is additive. This audit records the governed
hard policies that must remain unchanged before final closure can be considered.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

EXPECTED_HARD_GATES = {
    "content_spread_width_mm": 210,
    "content_spread_height_mm": 140,
    "local_path_mm": 80,
    "support_locality_mm": 60,
    "canonical_conductor_length_mm": 250,
    "locked_kicad": "KiCad 10.0.6",
    "erc_authoritative": True,
    "independent_observer_authoritative": True,
    "dp1_dp4_preserved": True,
    "cp_sat_absent": True,
    "local_ignored": True,
    "legacy_openclaw_unused": True,
}


@dataclass(frozen=True)
class HardGateFinding:
    gate: str
    expected: object
    observed: object


@dataclass(frozen=True)
class HardGateAudit:
    source_sha: str
    findings: tuple[HardGateFinding, ...]

    @property
    def passed(self) -> bool:
        return not self.findings

    def canonical_json(self) -> str:
        return json.dumps(_audit_dict(self), sort_keys=True, separators=(",", ":"))


def audit_hard_gates(source_sha: str, observed: dict[str, object]) -> HardGateAudit:
    """Compare observed current-source hard gates against frozen M2h2 policies."""
    _require_hex_sha(source_sha)
    findings = []
    for gate, expected in sorted(EXPECTED_HARD_GATES.items()):
        value = observed.get(gate, None)
        if value != expected:
            findings.append(HardGateFinding(gate, expected, value))
    return HardGateAudit(source_sha, tuple(findings))


def _require_hex_sha(source_sha: str) -> None:
    if len(source_sha) != 40 or any(
        character not in "0123456789abcdef" for character in source_sha
    ):
        raise ValueError("source_sha must be a 40-character lowercase hex commit SHA")


def _audit_dict(audit: HardGateAudit) -> dict[str, object]:
    return {
        "source_sha": audit.source_sha,
        "passed": audit.passed,
        "expected_hard_gates": EXPECTED_HARD_GATES,
        "findings": [finding.__dict__ for finding in audit.findings],
    }
