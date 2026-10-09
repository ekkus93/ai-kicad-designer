"""Bidirectional interface composition must not infer a false visual frontier."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import semantic_composition_penalty_breakdown
from ai_kicad.m2_composition_quality import observe_human_composition


def _interface(*roles: str):
    return SimpleNamespace(
        id="boundary",
        kind="interface",
        ports=tuple(SimpleNamespace(role=role) for role in roles),
    )


def _stage():
    return SimpleNamespace(id="stage", kind="filter", ports=())


def _case(
    interface,
    stage,
    *,
    producer: str,
    consumer: str,
    boundary_x: int,
    stage_x: int,
):
    edge = SimpleNamespace(kind="signal", source=producer, target=consumer, net="n")
    plan = SimpleNamespace(blocks=(interface, stage), edges=(edge,), precedence=())
    boxes = {
        "boundary": (boundary_x, 0, boundary_x + PITCH, PITCH),
        "stage": (stage_x, 0, stage_x + PITCH, PITCH),
    }
    packing = SimpleNamespace(
        fragments=tuple(
            SimpleNamespace(
                fragment=SimpleNamespace(
                    block=block, positions={}, text_positions={}, angles={}
                ),
                content_envelope=boxes[block.id],
                envelope=boxes[block.id],
                delta=(0, 0),
            )
            for block in (interface, stage)
        )
    )
    return plan, boxes, packing


def test_semantically_bidirectional_interface_has_no_frontier_polarity() -> None:
    interface, stage = _interface("signal_in", "signal_out"), _stage()
    plan, boxes, packing = _case(
        interface,
        stage,
        producer="boundary",
        consumer="stage",
        boundary_x=12 * PITCH,
        stage_x=0,
    )
    independent = observe_human_composition(plan, boxes)
    production = semantic_composition_penalty_breakdown(plan, packing)
    assert independent.metrics.input_side_violations == 0
    assert independent.metrics.output_side_violations == 0
    assert production.interface_side_violations == 0
    assert production.frontier_distance == 0
    # Directed stage precedence remains independently observed.
    assert independent.metrics.primary_stage_order_inversions == 1
    assert production.stage_order_violations == 1


def test_explicit_directed_interfaces_still_require_correct_visual_side() -> None:
    stage = _stage()
    input_port = _interface("signal_in")
    input_plan, input_boxes, input_packing = _case(
        input_port,
        stage,
        producer="boundary",
        consumer="stage",
        boundary_x=12 * PITCH,
        stage_x=0,
    )
    assert observe_human_composition(input_plan, input_boxes).metrics.input_side_violations == 1
    assert (
        semantic_composition_penalty_breakdown(input_plan, input_packing).interface_side_violations
        == 1
    )

    output_port = _interface("signal_out")
    output_plan, output_boxes, output_packing = _case(
        output_port,
        stage,
        producer="stage",
        consumer="boundary",
        boundary_x=0,
        stage_x=12 * PITCH,
    )
    assert observe_human_composition(output_plan, output_boxes).metrics.output_side_violations == 1
    assert (
        semantic_composition_penalty_breakdown(output_plan, output_packing).interface_side_violations
        == 1
    )
