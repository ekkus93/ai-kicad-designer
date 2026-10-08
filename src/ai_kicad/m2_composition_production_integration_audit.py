"""Production-source audit for M2h2 semantic candidate ranking integration.

This audit is intentionally source-text based: final closure must prove the
production composer ranks fully proved candidates with the semantic readability
key before lower-priority routing compactness and whitespace tie-breakers.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionIntegrationFinding:
    category: str
    witness: str


REQUIRED_SYMBOLS = (
    "composition_candidate_key",
    "semantic_composition_penalties",
)


def audit_production_ranking_integration(source: str) -> tuple[ProductionIntegrationFinding, ...]:
    """Return findings for missing semantic-ranking production integration."""
    findings: list[ProductionIntegrationFinding] = []
    for symbol in REQUIRED_SYMBOLS:
        if symbol not in source:
            findings.append(
                ProductionIntegrationFinding(
                    "missing_semantic_ranking_symbol",
                    symbol,
                )
            )
    if "selected = min(proved_candidates, key=lambda item: item[0])" in source:
        findings.append(
            ProductionIntegrationFinding(
                "routing_compactness_still_primary",
                "selected = min(proved_candidates, key=lambda item: item[0])",
            )
        )
    if '"rule": "proved_union_length_then_worst_length_bends_area"' in source:
        findings.append(
            ProductionIntegrationFinding(
                "stale_candidate_selection_rule",
                "proved_union_length_then_worst_length_bends_area",
            )
        )
    if "composition_candidate_key(plan," not in source:
        findings.append(
            ProductionIntegrationFinding(
                "semantic_key_not_applied_to_proved_candidates",
                "composition_candidate_key(plan, <packing>, <routing_compactness>)",
            )
        )
    return tuple(findings)


def production_ranking_integration_passes(source: str) -> bool:
    """Return true only when no production-integration finding remains."""
    return not audit_production_ranking_integration(source)
