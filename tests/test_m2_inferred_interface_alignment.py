"""Connector-row ranking uses the same directed semantics as frontier ranking."""

from types import SimpleNamespace

from ai_kicad.m2a import PITCH
from ai_kicad.m2_composition_candidate_rank import (
    _interface_roles,
    _signal_row_alignment_penalties,
)


def _block(name: str, kind: str, *roles: str):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=tuple(SimpleNamespace(role=role) for role in roles),
    )


def _plan(blocks, edges=(), precedence=()):
    return SimpleNamespace(
        blocks=tuple(blocks),
        edges=tuple(edges),
        precedence=tuple(precedence),
    )


def _edge(source: str, target: str, net: str = "n"):
    return SimpleNamespace(kind="signal", source=source, target=target, net=net)


def test_inferred_output_interface_aligns_with_producer_row():
    stage = _block("stage", "filter", "signal_in", "signal_out")
    inferred = _block("connector", "interface", "unspecified")
    directed = (("stage", "connector", "signal"),)
    plan = _plan((stage, inferred))
    centers = {"stage": (0, 0), "connector": (4 * PITCH, 3 * PITCH)}
    assert _interface_roles(plan, directed)["connector"] == {"signal_out"}
    assert _signal_row_alignment_penalties(plan, centers, directed) == (0, 3)

    # Explicit and precedence-inferred output polarity must rank alike.
    explicit = _block("connector", "interface", "signal_out")
    assert _signal_row_alignment_penalties(
        _plan((explicit, stage)), centers, directed
    ) == (0, 3)

    # Permuting declarations and renaming the net cannot change the result.
    renamed = (("stage", "connector", "renamed"),)
    assert _signal_row_alignment_penalties(
        _plan((inferred, stage)), centers, renamed
    ) == (0, 3)


def test_inferred_input_interface_aligns_with_consumer_row():
    stage = _block("stage", "filter", "signal_in", "signal_out")
    inferred = _block("input", "interface", "unspecified")
    directed = (("input", "stage", "n"),)
    plan = _plan((inferred, stage))
    centers = {"input": (0, 5 * PITCH), "stage": (4 * PITCH, 0)}
    assert _interface_roles(plan, directed)["input"] == {"signal_in"}
    assert _signal_row_alignment_penalties(plan, centers, directed) == (0, 5)


def test_ambiguous_bidirectional_inferred_interface_is_exempt():
    stage_in = _block("producer", "filter", "signal_in", "signal_out")
    stage_out = _block("consumer", "filter", "signal_in", "signal_out")
    inferred = _block("shared", "interface", "unspecified")
    directed = (("producer", "shared", "out"), ("shared", "consumer", "in"))
    centers = {
        "producer": (0, 0),
        "shared": (2 * PITCH, 8 * PITCH),
        "consumer": (4 * PITCH, 0),
    }
    plan = _plan((stage_in, inferred, stage_out))
    assert _interface_roles(plan, directed)["shared"] == {"signal_in", "signal_out"}
    assert _signal_row_alignment_penalties(plan, centers, directed) == (0, 0)


def test_power_and_reference_edges_do_not_imply_signal_polarity():
    first = _block("supply", "power_stage")
    ambiguous = _block("external", "interface", "power_in")
    edges = (
        SimpleNamespace(kind="power", source="external", target="supply", net="rail"),
        SimpleNamespace(kind="reference", source="supply", target="external", net="return"),
    )
    plan = _plan((first, ambiguous), edges)
    centers = {"supply": (0, 0), "external": (4 * PITCH, 3 * PITCH)}
    assert _interface_roles(plan, ())["external"] == set()
    assert _signal_row_alignment_penalties(plan, centers, ()) == (0, 0)
