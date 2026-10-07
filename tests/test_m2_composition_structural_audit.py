from ai_kicad.m2_composition_structural_audit import (
    StructuralFact,
    StructuralFinding,
    audit_structural_facts,
)


def test_rejects_structural_case_and_qualification_dispatch() -> None:
    facts = (
        StructuralFact("layout.py", 10, "condition", "case_id", "i4__b2_mixed"),
        StructuralFact("layout.py", 20, "condition", "qualification_group", "I4"),
    )

    findings = audit_structural_facts(facts)

    assert len(findings) == 2
    assert all(item.category == "benchmark_specific_control" for item in findings)


def test_rejects_refdes_net_topology_and_inventory_control() -> None:
    facts = (
        StructuralFact("rules.py", 1, "condition", "refdes", "R17"),
        StructuralFact("rules.py", 2, "condition", "net_name", "VREF"),
        StructuralFact("rules.py", 3, "condition", "topology_hash", "deadbeef"),
        StructuralFact("rules.py", 4, "condition", "inventory_signature", "2R1C"),
    )

    findings = audit_structural_facts(facts)

    assert len(findings) == 4
    assert {item.witness for item in findings} == {
        "refdes=R17",
        "net_name=VREF",
        "topology_hash=deadbeef",
        "inventory_signature=2R1C",
    }


def test_rejects_exact_inventory_lookup() -> None:
    facts = (
        StructuralFact("tables.py", 7, "inventory_lookup", "2R1C1U", "compact"),
    )

    assert audit_structural_facts(facts) == (
        StructuralFinding(
            "tables.py",
            7,
            "exact_inventory_special_case",
            "2R1C1U=compact",
        ),
    )


def test_rejects_precomputed_target_image_geometry() -> None:
    facts = (
        StructuralFact("targets.py", 3, "constant", "target_width", "812"),
        StructuralFact("targets.py", 4, "constant", "target_height", "514"),
        StructuralFact("targets.py", 5, "constant", "target_x", "92"),
    )

    findings = audit_structural_facts(facts)

    assert [item.category for item in findings] == [
        "precomputed_target_geometry",
        "precomputed_target_geometry",
        "precomputed_target_geometry",
    ]


def test_rejects_per_case_coordinate_maps_from_data_tables() -> None:
    facts = (
        StructuralFact("targets.py", 10, "coordinate_table", "i4", "(10,20)"),
        StructuralFact("targets.py", 11, "coordinate_table", "i4", "(30,40)"),
        StructuralFact("targets.py", 12, "coordinate_table", "other", "(1,2)"),
    )

    findings = audit_structural_facts(facts)

    assert findings == (
        StructuralFinding(
            "targets.py",
            10,
            "per_case_coordinate_map",
            "i4:2 entries",
        ),
    )


def test_generic_semantic_constants_and_single_coordinates_are_allowed() -> None:
    facts = (
        StructuralFact("layout.py", 1, "condition", "semantic_role", "output"),
        StructuralFact("layout.py", 2, "constant", "grid_pitch", "2.54"),
        StructuralFact("layout.py", 3, "coordinate_table", "semantic_anchor", "(0,0)"),
    )

    assert audit_structural_facts(facts) == ()


def test_finding_order_is_input_order_invariant() -> None:
    a = StructuralFact("b.py", 9, "condition", "case_id", "b1")
    b = StructuralFact("a.py", 2, "constant", "target_y", "42")

    forward = audit_structural_facts((a, b))
    reverse = audit_structural_facts((b, a))

    assert forward == reverse
    assert [item.path for item in forward] == ["a.py", "b.py"]
