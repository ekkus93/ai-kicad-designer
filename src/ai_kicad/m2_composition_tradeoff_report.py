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
        "directed_interface_row_drift": penalties.get("directed_interface_row_drift"),
        "local_signal_neighbor_gap": penalties.get("local_signal_neighbor_gap"),
        "route_backtracking": key[16] if len(key) > 16 else None,
        "routed_union_length_nm": score[0] if score else None,
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
        "interface_owner_distance",
    )
    alternatives = [
        _view(candidate)
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
    return {
        "selected": selected_view,
        "same_flow_side_alternative_count": len(alternatives),
        "best_row_locality_alternatives": alternatives[:limit],
        "truncated": len(alternatives) > limit,
        "acceptance_claimed": False,
    }
