from ai_kicad import m2_composition_anti_overfitting_audit as audit


def test_audit_detects_fixture_case_id_control_flow() -> None:
    source = audit.SourceFile(
        "src/layout.py",
        "if case_id == 'i4__b2_mixed':\n    use_special_layout()\n",
    )

    findings = audit.audit_composition_sources((source,))

    assert audit.AuditFinding("src/layout.py", 1, "fixture_or_case_id", "i4__b2_mixed") in findings


def test_audit_scans_data_tables_not_only_conditionals() -> None:
    source = audit.SourceFile(
        "src/table.py",
        "TARGETS = {'a7__branch': (10, 20), 'b8__fanout': (30, 40)}\n",
    )

    findings = audit.audit_composition_sources((source,))

    categories = [finding.category for finding in findings]
    assert categories.count("fixture_or_case_id") == 2
    assert "precomputed_coordinate_map" in categories


def test_audit_detects_refdes_and_literal_net_name_special_cases() -> None:
    source = audit.SourceFile(
        "src/rules.py",
        "if refdes == 'R17' or net_name == 'VREF':\n    pin_to_corner()\n",
    )

    findings = audit.audit_composition_sources((source,))

    assert audit.AuditFinding("src/rules.py", 1, "refdes_specific_control", "R17") in findings
    assert audit.AuditFinding(
        "src/rules.py", 1, "literal_benchmark_net_name", "VREF"
    ) in findings


def test_audit_detects_qualification_group_and_topology_hash_special_cases() -> None:
    topology_hash = "0123456789abcdef0123456789abcdef01234567"
    source = audit.SourceFile(
        "src/rules.py",
        f"if group == 'M2H2_FINAL' or topology == '{topology_hash}':\n    pass\n",
    )

    findings = audit.audit_composition_sources((source,))

    assert audit.AuditFinding(
        "src/rules.py", 1, "qualification_group_control", "M2H2_FINAL"
    ) in findings
    assert audit.AuditFinding(
        "src/rules.py", 1, "topology_hash_special_case", topology_hash
    ) in findings


def test_comments_do_not_create_false_positive_findings() -> None:
    source = audit.SourceFile(
        "src/comments.py",
        "# i4__b2_mixed and R17 are allowed in explanatory comments\nvalue = 1\n",
    )

    findings = audit.audit_composition_sources((source,))

    assert findings == ()


def test_findings_are_deterministic_by_path_line_and_category() -> None:
    first = audit.SourceFile("b.py", "x = 'R1'\n")
    second = audit.SourceFile("a.py", "x = 'VOUT'\n")

    findings = audit.audit_composition_sources((first, second))

    assert [(finding.path, finding.category) for finding in findings] == [
        ("a.py", "literal_benchmark_net_name"),
        ("b.py", "refdes_specific_control"),
    ]
