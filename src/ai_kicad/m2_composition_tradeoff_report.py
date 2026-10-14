"""Bounded, source-neutral comparison of proved composition alternatives.

Development evidence only: this is not an independent aesthetic acceptance oracle.
"""

from __future__ import annotations


def _view(candidate: dict) -> dict:
    penalties = candidate.get("semantic_penalty_breakdown", {})
    score = candidate.get("score", ())
    key = candidate.get("selection_key", ())
    return {
        "seed": candidate.get("seed"),
        "round": candidate.get("round"),
        "stage_inversions": penalties.get("stage_order_violations"),
        "reversal_distance": penalties.get("reversal_distance"),
        "interface_side_violations": penalties.get("interface_side_violations"),
        "interface_owner_distance": penalties.get("interface_owner_distance"),
        "frontier_distance": penalties.get("frontier_distance"),
        "branch_alignment": penalties.get("branch_alignment"),
        "repeated_alignment": penalties.get("repeated_alignment"),
        "directed_interface_row_drift": penalties.get("directed_interface_row_drift"),
        "material_interface_row_dislocation": key[16] if len(key) > 16 else None,
        "independent_output_owner_row_drift": key[17] if len(key) > 17 else None,
        "local_signal_neighbor_gap": penalties.get("local_signal_neighbor_gap"),
        "route_backtracking": key[18] if len(key) > 18 else None,
        # Expose production route-length/bend ranking without mutating it.
        # Legacy/synthetic short keys have no such fields.
        "route_geometry_cost_nm": key[23] if len(key) > 23 else None,
        "route_bend_count": score[2] if len(score) > 2 else None,
        "routed_union_length_nm": score[0] if score else None,
    }


def _delta_from_selected(candidate: dict, selected: dict) -> dict:
    """Positive deltas are larger than selected; negative deltas are smaller."""
    keys = (
        "frontier_distance",
        "directed_interface_row_drift",
        "route_backtracking",
        "routed_union_length_nm",
    )
    return {
        key: (
            candidate[key] - selected[key]
            if candidate[key] is not None and selected[key] is not None
            else None
        )
        for key in keys
    }


def _first_rank_difference(candidate: dict, selected: dict) -> dict | None:
    """Locate the first production-key preference without re-ranking anything."""
    candidate_key = candidate.get("selection_key")
    selected_key = selected.get("selection_key")
    if not candidate_key or not selected_key:
        return None
    for index, (alternative_value, selected_value) in enumerate(zip(candidate_key, selected_key)):
        if alternative_value != selected_value:
            return {
                "index": index,
                "candidate_value": alternative_value,
                "selected_value": selected_value,
                "candidate_preferred": alternative_value < selected_value,
            }
    if len(candidate_key) != len(selected_key):
        return None
    return {
        "index": None,
        "candidate_value": None,
        "selected_value": None,
        "candidate_preferred": False,
    }


def summarize_comparable_candidates(selection: dict, limit: int = 8) -> dict:
    """Expose alternatives with the same leading flow/side obligations.

    The observer's visual criteria and thresholds are not modified. This report
    does not re-rank production candidates; it only makes already-proved
    candidate tradeoffs visible for engineering inspection.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    selected = {
        "seed": selection.get("selected_seed"),
        "round": selection.get("selected_round"),
        "score": selection.get("selected_score", ()),
        "selection_key": selection.get("selected_selection_key", ()),
        "semantic_penalty_breakdown": selection.get("selected_semantic_penalty_breakdown", {}),
    }
    selected_view = _view(selected)
    obligations = (
        "stage_inversions",
        "reversal_distance",
        "interface_side_violations",
    )
    alternatives = [
        {
            **_view(candidate),
            "first_rank_difference": _first_rank_difference(candidate, selected),
        }
        for candidate in selection.get("proved_candidates", ())
        if (
            candidate.get("seed"),
            candidate.get("round"),
        )
        != (selected_view["seed"], selected_view["round"])
    ]
    alternatives = [
        item for item in alternatives if all(item[key] == selected_view[key] for key in obligations)
    ]
    for item in alternatives:
        item["delta_from_selected"] = _delta_from_selected(item, selected_view)
        item["soft_semantic_delta_from_selected"] = {
            key: (
                item[key] - selected_view[key]
                if item[key] is not None and selected_view[key] is not None
                else None
            )
            for key in (
                "interface_owner_distance",
                "material_interface_row_dislocation",
                "independent_output_owner_row_drift",
            )
        }
        item["route_shape_delta_from_selected"] = {
            key: (
                item[key] - selected_view[key]
                if item[key] is not None and selected_view[key] is not None
                else None
            )
            for key in (
                "route_backtracking",
                "route_geometry_cost_nm",
                "route_bend_count",
                "routed_union_length_nm",
                "branch_alignment",
                "repeated_alignment",
            )
        }
    alternatives.sort(
        key=lambda item: (
            item["directed_interface_row_drift"] is None,
            item["directed_interface_row_drift"] or 0,
            item["routed_union_length_nm"] is None,
            item["routed_union_length_nm"] or 0,
            item["seed"] if item["seed"] is not None else -1,
            item["round"] if item["round"] is not None else -1,
        )
    )
    # Show route-shape improvements that production ranking may reject for
    # higher-priority semantic obligations. This is an audit view only.
    route_alternatives = sorted(
        alternatives,
        key=lambda item: (
            item["route_backtracking"] is None,
            item["route_backtracking"] if item["route_backtracking"] is not None else 0,
            item["route_geometry_cost_nm"] is None,
            item["route_geometry_cost_nm"] if item["route_geometry_cost_nm"] is not None else 0,
            item["seed"] if item["seed"] is not None else -1,
            item["round"] if item["round"] is not None else -1,
        ),
    )
    better_routes = sum(
        item["route_backtracking"] is not None
        and selected_view["route_backtracking"] is not None
        and (
            item["route_backtracking"] < selected_view["route_backtracking"]
            or (
                item["route_backtracking"] == selected_view["route_backtracking"]
                and item["route_geometry_cost_nm"] is not None
                and selected_view["route_geometry_cost_nm"] is not None
                and item["route_geometry_cost_nm"] < selected_view["route_geometry_cost_nm"]
            )
        )
        for item in alternatives
    )
    # Count which *earlier* production priorities prevent a proved route
    # improvement from winning. This diagnoses tradeoffs without relaxing
    # any semantic obligation or changing production candidate selection.
    blockers: dict[int, int] = {}
    for item in alternatives:
        delta = item["route_shape_delta_from_selected"]
        backtrack = delta["route_backtracking"]
        geometry = delta["route_geometry_cost_nm"]
        better = backtrack is not None and (
            backtrack < 0 or (backtrack == 0 and geometry is not None and geometry < 0)
        )
        first = item["first_rank_difference"]
        if not better or first is None or first["candidate_preferred"]:
            continue
        rank_index = first["index"]
        route_index = 18 if backtrack < 0 else 23
        if rank_index is not None and rank_index < route_index:
            blockers[rank_index] = blockers.get(rank_index, 0) + 1
    return {
        "selected": selected_view,
        "better_route_aesthetics_count": better_routes,
        "better_routes_blocked_by_rank_index": {
            str(index): blockers[index] for index in sorted(blockers)
        },
        "best_route_aesthetics_alternatives": route_alternatives[:limit],
        "same_flow_side_alternative_count": len(alternatives),
        "better_row_locality_count": sum(
            item["delta_from_selected"]["directed_interface_row_drift"] is not None
            and item["delta_from_selected"]["directed_interface_row_drift"] < 0
            for item in alternatives
        ),
        "best_row_locality_alternatives": alternatives[:limit],
        "truncated": len(alternatives) > limit,
        "acceptance_claimed": False,
    }
