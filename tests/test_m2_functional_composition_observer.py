from ai_kicad.m2_functional_composition_observer import (
    derive_functional_blocks,
    functional_block_dispersion,
    support_to_owner_distances,
    visual_ownership_witnesses,
)
from ai_kicad.m2_semantics import BlockPlan, PresentationNet, SemanticPlan


def _block(block_id: str, *occurrences: tuple[str, int], kind: str = "stage") -> BlockPlan:
    return BlockPlan(
        id=block_id,
        kind=kind,
        relationships=(f"rel.{block_id}",),
        occurrences=frozenset(occurrences),
        ports=(),
    )


def test_functional_block_inventory_marks_shared_infrastructure() -> None:
    plan = SemanticPlan(
        blocks=(
            _block("amp", ("U1", 1)),
            _block("vref", ("U2", 1), kind="reference"),
        ),
        edges=(),
        owners={},
        signal_order=(),
        presentation_nets=(
            PresentationNet(
                id="vref",
                terminals=(),
                fragments=("vref", "amp"),
                role="distributive",
                internally_generated=True,
            ),
        ),
    )

    witnesses = derive_functional_blocks(plan)
    assert [(witness.block, witness.shared) for witness in witnesses] == [
        ("amp", True),
        ("vref", True),
    ]
    assert witnesses[0].relationship_ids == ("rel.amp",)
    assert witnesses[0].occurrences == (("U1", 1),)


def test_visual_ownership_witnesses_report_owner_kind() -> None:
    plan = SemanticPlan(
        blocks=(_block("amp", ("U1", 1), ("R1", 1), kind="amplifier"),),
        edges=(),
        owners={("U1", 1): "amp", ("R1", 1): "amp"},
        signal_order=(),
    )

    witnesses = visual_ownership_witnesses(plan)
    assert [(witness.occurrence, witness.owner_kind) for witness in witnesses] == [
        (("R1", 1), "amplifier"),
        (("U1", 1), "amplifier"),
    ]


def test_functional_block_dispersion_retains_missing_coordinate_witnesses() -> None:
    plan = SemanticPlan(
        blocks=(_block("amp", ("U1", 1), ("R1", 1), ("C1", 1)),),
        edges=(),
        owners={},
        signal_order=(),
    )

    witness = functional_block_dispersion(plan, {("U1", 1): (0, 0), ("R1", 1): (10, 20)})[0]
    assert witness.bbox == (0, 0, 10, 20)
    assert witness.manhattan_span == 30
    assert witness.fragmented is True
    assert witness.missing_occurrences == (("C1", 1),)


def test_support_to_owner_distances_use_observed_owner_centroid() -> None:
    plan = SemanticPlan(
        blocks=(_block("amp", ("U1", 1), ("R1", 1)),),
        edges=(),
        owners={("U1", 1): "amp", ("R1", 1): "amp"},
        signal_order=(),
    )

    distances = support_to_owner_distances(plan, {("U1", 1): (0, 0), ("R1", 1): (10, 0)})
    assert distances == ((("R1", 1), "amp", 5), (("U1", 1), "amp", 5))
