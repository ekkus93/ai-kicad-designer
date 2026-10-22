from ai_kicad.pivot.controller import WorkflowController
from ai_kicad.pivot.mcp_server import MCPServer
from ai_kicad.pivot.requirements import assess_requirements


def test_requirement_intake_does_not_invent_essential_electrical_facts():
    result = assess_requirements("Make a blinking light.")
    assert result["status"] == "NEEDS_CLARIFICATION"
    assert result["facts"] == {}
    assert len(result["clarifying_questions"]) == 3
    assert result["assumptions"] == []


def test_conflicting_supply_ranges_are_not_collapsed():
    result = assess_requirements(
        "Supply voltage: 3-5 V or 9-12 V; maximum LED current: 15 mA; "
        "NE555D datasheet and pinout source are required."
    )
    assert result["status"] == "NEEDS_CLARIFICATION"
    assert "supply_voltage_min_v" not in result["facts"]
    assert "authoritative" in result["clarifying_questions"][0]


def test_mcp_requirement_tool_records_only_explicit_typed_facts(tmp_path):
    controller = WorkflowController(tmp_path / "workspace")
    server = MCPServer(controller)
    response = server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "define_requirements",
                "arguments": {
                    "description": (
                        "Supply voltage: 4.5-5.5 V; maximum LED current: 10 mA; "
                        "NE555D datasheet and pinout source: Texas Instruments."
                    ),
                    "expected_revision": None,
                    "idempotency_key": "requirements-explicit-v1",
                },
            },
        }
    )["result"]["structuredContent"]
    assert response["status"] == "READY_FOR_ENGINEERING_REVIEW"
    assert response["facts"] == {
        "supply_voltage_min_v": 4.5,
        "supply_voltage_max_v": 5.5,
        "max_output_current_ma": 10.0,
        "part_numbers": ["NE555D"],
        "pinout_source_mentioned": True,
    }
    recorded = controller._state()["requirement_assessment"]
    assert recorded["assumptions"] == []
    assert recorded["clarifying_questions"] == []
