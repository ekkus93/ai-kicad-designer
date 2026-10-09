"""Mutation and metamorphic controls for passive external interface flow inference."""

from ai_kicad.m2_route import _routable_edges
from ai_kicad.m2_semantics import BlockPlan, SemanticEdge, SemanticPlan, SemanticPort
from ai_kicad.m2_terminal_interface_flow import inferred_passive_interface_signal_relations


def _block(block_id: str, kind: str, *ports: tuple[str, str]) -> BlockPlan:
    return BlockPlan(
        id=block_id,
        kind=kind,
        relationships=(),
        occurrences=frozenset(),
        ports=tuple(
            SemanticPort(
                id=f"{block_id}.{index}",
                fragment=block_id,
                net=net,
                role=role,
                terminals=(),
            )
            for index, (net, role) in enumerate(ports)
        ),
    )


def _relations(*blocks: BlockPlan) -> tuple[tuple[str, str, str], ...]:
    plan = SemanticPlan(blocks=tuple(blocks), edges=(), owners={}, signal_order=())
    return inferred_passive_interface_signal_relations(plan)


def test_one_passive_connector_to_one_consumer_is_input() -> None:
    assert _relations(
        _block("connector", "interface", ("signal", "passive")),
        _block("gain_stage", "active", ("signal", "signal_in")),
    ) == (("connector", "gain_stage", "signal"),)


def test_one_producer_to_one_passive_connector_is_output() -> None:
    assert _relations(
        _block("connector", "interface", ("signal", "passive")),
        _block("output_stage", "active", ("signal", "signal_out")),
    ) == (("output_stage", "connector", "signal"),)


def test_two_unique_interfaces_keep_sorted_relations_across_permutations() -> None:
    blocks = (
        _block("right_connector", "interface", ("z", "passive")),
        _block("source", "active", ("z", "signal_out")),
        _block("left_connector", "interface", ("a", "passive")),
        _block("sink", "active", ("a", "signal_in")),
    )
    expected = (("left_connector", "sink", "a"), ("source", "right_connector", "z"))
    assert _relations(*blocks) == expected
    assert _relations(*reversed(blocks)) == expected


def test_ambiguous_producers_and_consumers_are_not_guessed() -> None:
    connector = _block("connector", "interface", ("n", "passive"))
    assert not _relations(
        connector,
        _block("first", "active", ("n", "signal_out")),
        _block("second", "active", ("n", "signal_out")),
    )
    assert not _relations(
        connector,
        _block("first", "active", ("n", "signal_in")),
        _block("second", "active", ("n", "signal_in")),
    )
    assert not _relations(
        connector,
        _block("producer", "active", ("n", "signal_out")),
        _block("consumer", "active", ("n", "signal_in")),
    )


def test_multiple_passive_connectors_do_not_claim_unique_ownership() -> None:
    assert not _relations(
        _block("left", "interface", ("n", "passive")),
        _block("right", "interface", ("n", "passive")),
        _block("source", "active", ("n", "signal_out")),
    )


def test_reference_power_and_explicit_interface_roles_are_excluded() -> None:
    for competing_role in ("power_in", "power_out", "reference"):
        assert not _relations(
            _block("connector", "interface", ("n", "passive")),
            _block("sink", "active", ("n", "signal_in")),
            _block("supply", "utility", ("n", competing_role)),
        )
    assert not _relations(
        _block("connector", "interface", ("n", "passive"), ("n", "signal_out")),
        _block("sink", "active", ("n", "signal_in")),
    )


def test_renamed_net_and_block_ids_preserve_direction_and_cardinality() -> None:
    original = _relations(
        _block("connector", "interface", ("a", "passive")),
        _block("stage", "active", ("a", "signal_in")),
    )
    renamed = _relations(
        _block("zeta", "interface", ("renamed", "passive")),
        _block("omega", "active", ("renamed", "signal_in")),
    )
    assert original == (("connector", "stage", "a"),)
    assert renamed == (("zeta", "omega", "renamed"),)


def test_unique_passive_interface_relation_becomes_required_visible_signal_route() -> None:
    connector = _block("connector", "interface", ("signal", "passive"))
    stage = _block("stage", "active", ("signal", "signal_in"))
    plan = SemanticPlan(blocks=(connector, stage), edges=(), owners={}, signal_order=())

    edges = _routable_edges(plan)

    assert edges == (
        SemanticEdge(
            "signal",
            "connector",
            "stage",
            "signal",
            ("inferred_passive_interface",),
        ),
    )


def test_existing_authored_interface_route_is_not_duplicated() -> None:
    connector = _block("connector", "interface", ("signal", "passive"))
    stage = _block("stage", "active", ("signal", "signal_in"))
    authored = SemanticEdge("signal", "connector", "stage", "signal", ("authored",))
    plan = SemanticPlan(
        blocks=(connector, stage),
        edges=(authored,),
        owners={},
        signal_order=(),
    )

    assert _routable_edges(plan) == (authored,)


def test_ambiguous_passive_interface_relationship_does_not_force_route() -> None:
    connector = _block("connector", "interface", ("signal", "passive"))
    first = _block("first", "active", ("signal", "signal_in"))
    second = _block("second", "active", ("signal", "signal_in"))
    plan = SemanticPlan(
        blocks=(connector, first, second),
        edges=(),
        owners={},
        signal_order=(),
    )

    assert _routable_edges(plan) == ()
