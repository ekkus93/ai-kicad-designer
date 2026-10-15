"""Generic terminal-backed signal-flow inference."""

from __future__ import annotations

from .m2_semantics import SemanticPlan


def inferred_passive_interface_signal_relations(
    plan: SemanticPlan,
) -> tuple[tuple[str, str, str], ...]:
    """Infer unique passive input/output connections without name dispatch."""
    interfaces: dict[str, set[str]] = {}
    producers: dict[str, set[str]] = {}
    consumers: dict[str, set[str]] = {}
    excluded: set[str] = set()
    passive_owners: dict[str, set[str]] = {}
    for block in plan.blocks:
        for port in block.ports:
            net = getattr(port, "net", None)
            if not isinstance(net, str):
                continue
            if block.kind == "interface":
                if port.role == "passive":
                    interfaces.setdefault(net, set()).add(block.id)
                else:
                    excluded.add(net)
            elif port.role == "passive":
                # A second passive participant makes direction/ownership
                # ambiguous; never turn a shared net into a directed link.
                passive_owners.setdefault(net, set()).add(block.id)
            elif port.role == "signal_out":
                producers.setdefault(net, set()).add(block.id)
            elif port.role == "signal_in":
                consumers.setdefault(net, set()).add(block.id)
            elif port.role in {"power_in", "power_out", "reference"}:
                excluded.add(net)
    if isinstance(plan, SemanticPlan):
        excluded.update(
            net.id for net in plan.presentation_nets if net.role == "distributive"
        )
    excluded.update(
        edge.net for edge in plan.edges if edge.kind in {"feedback", "power", "support"}
    )
    result: set[tuple[str, str, str]] = set()
    for net, attached in interfaces.items():
        if net in excluded or len(attached) != 1 or passive_owners.get(net):
            continue
        interface = next(iter(attached))
        sources = producers.get(net, set())
        targets = consumers.get(net, set())
        if len(sources) == 1 and not targets:
            result.add((next(iter(sources)), interface, net))
        elif len(targets) == 1 and not sources:
            result.add((interface, next(iter(targets)), net))
    return tuple(sorted(result))
