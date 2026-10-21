"""Construction of structured bounded-layout failure evidence."""

from __future__ import annotations


def _layout_failure_evidence(plan, variants, seeds, attempts, last_error, complete_attempts):
    return {
        "schema_version": "m2g2.composition-failure.1",
        "stage": "layout_schematic",
        "semantic_obligations": sorted(
            {
                obligation.id
                for choices in variants.values()
                for variant in choices
                for obligation in variant.obligations
            }
        ),
        "owners": [
            {"occurrence": list(occurrence), "fragment": owner}
            for occurrence, owner in sorted(plan.owners.items())
        ],
        "variants": [
            {
                "fragment": block_id,
                "variant": variant.id,
                "local_construction": variant.construction_evidence(),
                "content_envelope": list(variant.content_envelope),
                "packing_envelope": list(variant.packing_envelope),
                "reservations": [
                    {
                        "id": reservation.id,
                        "owner": reservation.owner,
                        "class": reservation.clearance_class,
                        "rect": list(reservation.rect),
                        "net": reservation.permitted_net,
                        "capacity": reservation.capacity,
                    }
                    for reservation in variant.reservations
                ],
                "gateways": [
                    {
                        "id": gateway.id,
                        "net": gateway.net,
                        "terminals": [list(terminal) for terminal in gateway.terminals],
                        "escape_direction": gateway.escape_direction,
                        "escape_polyline": [list(point) for point in gateway.escape_polyline],
                    }
                    for gateway in variant.gateways
                ],
                "wire_provenance": [list(value) for value in variant.wire_provenance],
                "protected_paths": [
                    {
                        "id": path.id,
                        "owner": path.owner,
                        "net": path.net,
                        "terminal_pairs": [list(pair) for pair in path.terminal_pairs],
                        "edges": [
                            [list(edge.start), list(edge.end)] for edge in path.local_tree_edges
                        ],
                    }
                    for path in variant.protected_paths
                ],
            }
            for block_id, choices in sorted(variants.items())
            for variant in choices
        ],
        "candidate_decisions": [
            {
                "seed": index,
                "packing_attempts": list(seed.attempts),
                "placements": [
                    {
                        "fragment": item.fragment.block.id,
                        "variant": item.fragment.id,
                        "local_construction": item.fragment.construction_evidence(),
                        "envelope": list(item.envelope),
                    }
                    for item in seed.fragments
                ],
            }
            for index, seed in enumerate(seeds[:8])
        ],
        "layout_attempts": attempts,
        "route_junction_provenance": "not_evaluated_no_accepted_route",
        "failed_metric": last_error,
        "threshold": "unchanged M2 layout/electrical gates",
        "budgets": {
            "seed_limit": 8,
            "repair_rounds_per_seed": 3,
            "complete_attempt_limit": 32,
            "complete_attempts_used": complete_attempts,
        },
    }
