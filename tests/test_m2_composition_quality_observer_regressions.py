"""Independent human-composition observer regression controls."""

from types import SimpleNamespace

from ai_kicad.m2_composition_quality import observe_human_composition
from ai_kicad.m2_pack import LEFT, TOP


def _block(name, kind="stage", roles=()):
    return SimpleNamespace(
        id=name,
        kind=kind,
        ports=tuple(SimpleNamespace(role=role) for role in roles),
    )


def _edge(source, target, net="signal", kind="signal"):
    return SimpleNamespace(source=source, target=target, net=net, kind=kind)


def _precedence(source, target, net="signal", obligation="p1"):
    return SimpleNamespace(
        source_fragment=source,
        target_fragment=target,
        net=net,
        id=obligation,
    )


def _plan(edges=(), precedence=()):
    return SimpleNamespace(
        blocks=(_block("input", "interface", ("signal_in",)), _block("stage")),
        edges=edges,
        precedence=precedence,
    )


def test_duplicate_signal_branch_and_precedence_are_one_observed_relation():
    reversed_geometry = {"input": (50, 0, 60, 10), "stage": (0, 0, 10, 10)}
    base = observe_human_composition(_plan((_edge("input", "stage"),)), reversed_geometry)
    annotated = observe_human_composition(
        _plan(
            (
                _edge("input", "stage"),
                _edge("input", "stage", kind="branch"),
                _edge("input", "stage"),
            ),
            (
                _precedence("input", "stage"),
                _precedence("input", "stage", obligation="p2"),
            ),
        ),
        reversed_geometry,
    )
    assert not base.passed
    assert base.metrics.primary_stage_order_inversions == 1
    assert base.metrics.input_side_violations == 1
    assert base.as_dict() == annotated.as_dict()


def test_distinct_nets_and_distinct_precedence_relations_are_not_lost():
    reversed_geometry = {"input": (50, 0, 60, 10), "stage": (0, 0, 10, 10)}
    report = observe_human_composition(
        _plan(
            (_edge("input", "stage", net="a"),),
            (
                _precedence("input", "stage", net="a"),
                _precedence("input", "stage", net="b", obligation="p2"),
            ),
        ),
        reversed_geometry,
    )
    assert report.metrics.primary_stage_order_inversions == 2
    assert {item.net for item in report.violations} == {"a", "b"}


def test_page_centroid_uses_absolute_placement_origin():
    center_x = LEFT + 105_000_000
    center_y = TOP + 70_000_000
    plan = SimpleNamespace(blocks=(_block("only"),), edges=(), precedence=())
    centered = observe_human_composition(
        plan,
        {"only": (center_x - 10, center_y - 10, center_x + 10, center_y + 10)},
    )
    shifted = observe_human_composition(
        plan,
        {
            "only": (
                center_x + 1_270_000 - 10,
                center_y - 2_540_000 - 10,
                center_x + 1_270_000 + 10,
                center_y - 2_540_000 + 10,
            )
        },
    )
    assert centered.metrics.centroid_offset_x_nm == 0
    assert centered.metrics.centroid_offset_y_nm == 0
    assert shifted.metrics.centroid_offset_x_nm == 1_270_000
    assert shifted.metrics.centroid_offset_y_nm == -2_540_000
