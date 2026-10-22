"""Strict, machine-readable benchmark trial records and independent gate scoring."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
import math
from typing import Literal

from pydantic import Field, model_validator

from .evidence import EvidenceArtifact, EvidenceStatus, StrictModel


class BenchmarkGateStatus(StrEnum):
    """Gate results distinguish missing capability from an incorrect result."""

    PASS = "PASS"
    FAIL = "FAIL"
    UNSUPPORTED = "UNSUPPORTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class BenchmarkModel(StrictModel):
    provider: str = Field(min_length=1)
    model: str = Field(min_length=1)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    settings: dict[str, int | float | str | bool]


class BenchmarkBackend(StrictModel):
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    build_id: str = Field(min_length=1)
    mode: Literal["full_inventory", "phase_gated", "task_gated", "direct"]


class BenchmarkGate(StrictModel):
    gate_id: str = Field(min_length=1)
    status: BenchmarkGateStatus
    summary: str = Field(min_length=1)
    independent: bool
    evidence_paths: list[str]


class BenchmarkToolCall(StrictModel):
    tool_name: str = Field(min_length=1)
    duration_ms: int = Field(ge=0)
    error_class: str | None = None
    valid: bool


class BenchmarkTrial(StrictModel):
    schema_version: Literal["pivot-benchmark.v1"]
    trial_id: str = Field(min_length=1)
    task_id: str = Field(min_length=1)
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    recorded_at_utc: datetime
    model: BenchmarkModel
    backend: BenchmarkBackend
    time_limit_seconds: int = Field(gt=0)
    token_limit: int = Field(gt=0)
    tool_call_limit: int = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)
    token_count: int = Field(ge=0)
    tool_calls: list[BenchmarkToolCall]
    gates: list[BenchmarkGate]
    artifacts: list[EvidenceArtifact]
    status: EvidenceStatus

    @model_validator(mode="after")
    def validate_trial(self) -> BenchmarkTrial:
        if (
            self.recorded_at_utc.tzinfo is None
            or self.recorded_at_utc.utcoffset() != timezone.utc.utcoffset(self.recorded_at_utc)
        ):
            raise ValueError("recorded_at_utc must be normalized to UTC")
        outcomes = {gate.gate_id: gate.status for gate in self.gates}
        if (
            len(self.tool_calls) > self.tool_call_limit
            and outcomes.get("tool_call_budget") is not BenchmarkGateStatus.FAIL
        ):
            raise ValueError("tool-call limit exceeded without a failing budget gate")
        if (
            self.token_count > self.token_limit
            and outcomes.get("token_budget") is not BenchmarkGateStatus.FAIL
        ):
            raise ValueError("token limit exceeded without a failing budget gate")
        if (
            self.elapsed_seconds > self.time_limit_seconds
            and outcomes.get("wall_clock_budget") is not BenchmarkGateStatus.FAIL
        ):
            raise ValueError("time limit exceeded without a failing budget gate")
        paths = {artifact.path for artifact in self.artifacts}
        for gate in self.gates:
            if gate.independent and set(gate.evidence_paths) - paths:
                raise ValueError(f"gate {gate.gate_id!r} references missing artifacts")
        return self


def score_gates(gates: list[BenchmarkGate]) -> dict[str, int | float]:
    """Count outcomes separately; unsupported gates are excluded from accuracy."""
    counts = {
        status.value.lower(): sum(gate.status is status for gate in gates)
        for status in BenchmarkGateStatus
    }
    eligible = counts["pass"] + counts["fail"]
    counts["accuracy"] = counts["pass"] / eligible if eligible else 0.0
    counts["eligible"] = eligible
    return counts


def score_reference_inspection(
    response: dict,
    design: dict,
    expected_behavior: dict,
    *,
    evidence_path: str,
) -> list[BenchmarkGate]:
    """Judge a model's read-only reference review against pinned circuit facts."""
    pin_to_net = {
        pin: net["id"]
        for net in design["nets"]
        for component_id, pin in net["members"]
        if component_id == "timer"
    }
    findings = {
        str(item.get("pin")): item.get("net")
        for item in response.get("pin_net_findings", [])
        if isinstance(item, dict)
    }
    pins_pass = findings == pin_to_net
    timing = response.get("timing_calculation", {}).get("values", {})
    nominal = expected_behavior["nominal"]
    time_names = {
        "T_high_seconds": "high_s",
        "T_low_seconds": "low_s",
        "T_total_seconds": "period_s",
        "frequency_hz": "frequency_hz",
    }
    timing_pass = all(
        isinstance(timing.get(actual), (int, float))
        and math.isclose(timing[actual], nominal[expected], rel_tol=0.01, abs_tol=1e-9)
        for actual, expected in time_names.items()
    )
    led_values = response.get("LED_current_calculation", {}).get("values", {})
    led_expected = expected_behavior["indicator"]
    current = led_values.get("I_led_milliamps")
    current_pass = (
        isinstance(current, (int, float))
        and math.isclose(
            current,
            led_expected["estimated_nominal_current_ma_at_5v_and_1.9v_vf"],
            rel_tol=0.15,
        )
        and math.isclose(
            led_values.get("conservative_current_upper_bound_ma", float("nan")),
            led_expected["conservative_current_upper_bound_ma_ignoring_led_drop"],
            rel_tol=0.01,
        )
    )
    return [
        BenchmarkGate(
            gate_id="native_pin_net_map",
            status=BenchmarkGateStatus.PASS if pins_pass else BenchmarkGateStatus.FAIL,
            summary="All timer pin nets match the canonical circuit graph."
            if pins_pass
            else "One or more timer pins are missing or assigned to the wrong net.",
            independent=True,
            evidence_paths=[evidence_path],
        ),
        BenchmarkGate(
            gate_id="timing_calculation",
            status=BenchmarkGateStatus.PASS if timing_pass else BenchmarkGateStatus.FAIL,
            summary="High, low, period, and frequency match the pinned nominal equations."
            if timing_pass
            else "At least one timing value is missing or outside 1% of the independent result.",
            independent=True,
            evidence_paths=[evidence_path],
        ),
        BenchmarkGate(
            gate_id="led_current_bounds",
            status=BenchmarkGateStatus.PASS if current_pass else BenchmarkGateStatus.FAIL,
            summary="Nominal current and conservative upper bound match the reference."
            if current_pass
            else "Nominal current or the requested conservative upper bound is missing or incorrect.",
            independent=True,
            evidence_paths=[evidence_path],
        ),
    ]
