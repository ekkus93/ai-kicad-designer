import io
import json
import threading
import time

from ai_kicad.pivot.controller import Tool, WorkflowController
from ai_kicad.pivot.mcp_server import MCPServer, _read_message, serve


def request(method, params=None, request_id=1):
    value = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        value["params"] = params
    return value


def test_initialize_list_call_invalid_schema_and_hidden_dispatch(tmp_path):
    controller = WorkflowController(tmp_path / "workspace")
    server = MCPServer(controller)
    initialized = server.handle(request("initialize"))
    assert initialized["result"]["serverInfo"]["name"] == "ai-kicad-pivot"
    tools = server.handle(request("tools/list"))["result"]["tools"]
    assert "define_requirements" in {tool["name"] for tool in tools}
    result = server.handle(request("tools/call", {"name": "get_design_state", "arguments": {}}))
    assert result["result"]["structuredContent"]["phase"] == "REQUIREMENTS"
    invalid = server.handle(
        request("tools/call", {"name": "get_design_state", "arguments": {"extra": 1}})
    )
    assert invalid["error"]["code"] == -32602
    forged = server.handle(
        request(
            "tools/call",
            {
                "name": "prepare_fabrication_package",
                "arguments": {
                    "expected_revision": None,
                    "idempotency_key": "forged",
                },
            },
        )
    )
    assert forged["error"]["data"]["code"] == "NOT_AUTHORIZED_IN_PHASE"


def test_timeout_and_malformed_transport(tmp_path):
    controller = WorkflowController(tmp_path / "workspace")

    def slow(_):
        time.sleep(0.1)
        return {"status": "late"}

    controller.tools["slow"] = Tool("slow", None, False, {"type": "object"}, slow)
    controller.visible_tools = lambda task_tools=None: [
        {"name": "slow", "inputSchema": {"type": "object"}}
    ]
    # Put the tool in the active phase to exercise transport timeout, not authorization.
    from ai_kicad.pivot.controller import PHASE_TOOLS, Phase

    PHASE_TOOLS[Phase.REQUIREMENTS].add("slow")
    try:
        response = MCPServer(controller, call_timeout_seconds=0.01).handle(
            request("tools/call", {"name": "slow", "arguments": {}})
        )
        assert response["error"]["data"]["code"] == "TIMEOUT"
    finally:
        PHASE_TOOLS[Phase.REQUIREMENTS].remove("slow")
    # A timed-out write remains in progress under its idempotency key; replay reports
    # reconciliation state instead of dispatching the mutation a second time.
    entered = threading.Event()
    finish = threading.Event()

    def slow_write(_):
        entered.set()
        finish.wait(timeout=1)
        return {"status": "applied"}

    write = Tool(
        "slow_write",
        None,
        True,
        {
            "type": "object",
            "properties": {
                "expected_revision": {"type": ["string", "null"]},
                "idempotency_key": {"type": "string"},
            },
            "required": ["expected_revision", "idempotency_key"],
        },
        slow_write,
    )
    controller.tools["slow_write"] = write
    PHASE_TOOLS[Phase.REQUIREMENTS].add("slow_write")
    try:
        timed = MCPServer(controller, call_timeout_seconds=0.01).handle(
            request(
                "tools/call",
                {
                    "name": "slow_write",
                    "arguments": {"expected_revision": None, "idempotency_key": "replay-key"},
                },
            )
        )
        assert timed["error"]["data"]["code"] == "TIMEOUT"
        assert entered.wait(timeout=0.2)
        replay = MCPServer(controller).handle(
            request(
                "tools/call",
                {
                    "name": "slow_write",
                    "arguments": {"expected_revision": None, "idempotency_key": "replay-key"},
                },
            )
        )
        assert replay["result"]["structuredContent"]["status"] == "RECONCILIATION_REQUIRED"
    finally:
        finish.set()
        PHASE_TOOLS[Phase.REQUIREMENTS].remove("slow_write")
    malformed_in = io.BytesIO(b"{bad json}\n")
    output = io.StringIO()
    serve(controller, malformed_in, output)
    assert json.loads(output.getvalue())["error"]["code"] == -32700


def test_content_length_frame_and_path_traversal_error(tmp_path):
    payload = json.dumps(request("initialize")).encode()
    framed = io.BytesIO(f"Content-Length: {len(payload)}\r\n\r\n".encode() + payload)
    assert _read_message(framed)["method"] == "initialize"
    controller = WorkflowController(tmp_path / "workspace")
    controller.tools["path_probe"] = Tool(
        "path_probe",
        None,
        False,
        {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
        lambda arguments: {"path": str(controller.confined_path(arguments["path"]))},
    )
    from ai_kicad.pivot.controller import PHASE_TOOLS, Phase

    PHASE_TOOLS[Phase.REQUIREMENTS].add("path_probe")
    try:
        response = MCPServer(controller).handle(
            request("tools/call", {"name": "path_probe", "arguments": {"path": "../x"}})
        )
        assert response["error"]["data"]["code"] == "INVALID_INPUT"
    finally:
        PHASE_TOOLS[Phase.REQUIREMENTS].remove("path_probe")
