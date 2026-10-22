"""Small stdio MCP transport around :class:`WorkflowController`.

The transport deliberately contains no KiCad logic.  It exposes the controller's
phase-filtered registry and keeps authorization in ``dispatch`` so a forged call
cannot bypass tool visibility.
"""

from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from typing import BinaryIO, TextIO

from pydantic import ValidationError

from .backend import BackendError
from .controller import ControllerError, WorkflowController
from .revisions import RevisionError


JSONRPC_ERRORS = {
    "PARSE_ERROR": -32700,
    "INVALID_REQUEST": -32600,
    "METHOD_NOT_FOUND": -32601,
    "INVALID_PARAMS": -32602,
    "INTERNAL_ERROR": -32603,
}


class SchemaError(ValueError):
    pass


def validate_arguments(schema: dict, value: object, path: str = "arguments") -> None:
    """Validate the deliberately small JSON Schema subset used by pivot tools."""
    expected = schema.get("type")
    allowed = expected if isinstance(expected, list) else [expected]
    matches = (
        ("object" in allowed and isinstance(value, dict))
        or ("string" in allowed and isinstance(value, str))
        or ("boolean" in allowed and isinstance(value, bool))
        or ("integer" in allowed and isinstance(value, int) and not isinstance(value, bool))
        or ("array" in allowed and isinstance(value, list))
        or ("null" in allowed and value is None)
        or expected is None
    )
    if not matches:
        raise SchemaError(f"{path} has invalid type")
    if isinstance(value, list):
        item_schema = schema.get("items", {})
        for index, item in enumerate(value):
            validate_arguments(item_schema, item, f"{path}[{index}]")
        return
    if not isinstance(value, dict):
        return
    properties = schema.get("properties", {})
    missing = set(schema.get("required", [])) - set(value)
    if missing:
        raise SchemaError(f"{path} is missing {sorted(missing)}")
    if schema.get("additionalProperties") is False:
        extra = set(value) - set(properties)
        if extra:
            raise SchemaError(f"{path} contains unknown fields {sorted(extra)}")
    for name, child in properties.items():
        if name in value:
            validate_arguments(child, value[name], f"{path}.{name}")


@dataclass
class MCPServer:
    controller: WorkflowController
    call_timeout_seconds: float = 30.0
    task_tools: set[str] | None = None

    def _error(self, request_id: object, code: int, message: str, data: dict | None = None) -> dict:
        error: dict = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return {"jsonrpc": "2.0", "id": request_id, "error": error}

    def handle(self, request: object) -> dict | None:
        if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
            return self._error(None, JSONRPC_ERRORS["INVALID_REQUEST"], "invalid JSON-RPC request")
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})
        if not isinstance(method, str) or not isinstance(params, dict):
            return self._error(request_id, JSONRPC_ERRORS["INVALID_REQUEST"], "invalid request")
        if method == "notifications/initialized":
            return None
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {"tools": {"listChanged": True}},
                    "serverInfo": {"name": "ai-kicad-pivot", "version": "0.1.0"},
                },
            }
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"tools": self.controller.visible_tools(self.task_tools)},
            }
        if method != "tools/call":
            return self._error(request_id, JSONRPC_ERRORS["METHOD_NOT_FOUND"], "method not found")
        name, arguments = params.get("name"), params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return self._error(request_id, JSONRPC_ERRORS["INVALID_PARAMS"], "invalid tool call")
        tool = self.controller.tools.get(name)
        if tool is None:
            return self._error(request_id, JSONRPC_ERRORS["INVALID_PARAMS"], "unknown tool")
        try:
            validate_arguments(tool.schema, arguments)
            executor = ThreadPoolExecutor(max_workers=1)
            future = executor.submit(self.controller.dispatch, name, arguments)
            try:
                result = future.result(timeout=self.call_timeout_seconds)
            finally:
                executor.shutdown(wait=False, cancel_futures=True)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result, sort_keys=True)}],
                    "structuredContent": result,
                    "isError": False,
                },
            }
        except FutureTimeout:
            return self._error(
                request_id,
                -32001,
                "tool call timed out; reconcile exact revision before retry",
                {"code": "TIMEOUT", "mutation_occurred": "unknown"},
            )
        except (SchemaError, ValidationError) as exc:
            return self._error(request_id, JSONRPC_ERRORS["INVALID_PARAMS"], str(exc))
        except (ControllerError, RevisionError, BackendError) as exc:
            return self._error(
                request_id,
                -32000,
                str(exc),
                {"code": getattr(exc, "code", type(exc).__name__), "mutation_occurred": False},
            )
        except Exception as exc:  # defensive JSON-RPC boundary
            return self._error(request_id, JSONRPC_ERRORS["INTERNAL_ERROR"], type(exc).__name__)


def _read_message(stream: BinaryIO) -> object | None:
    first = stream.readline()
    if not first:
        return None
    if first.lower().startswith(b"content-length:"):
        try:
            length = int(first.split(b":", 1)[1].strip())
            while stream.readline() not in (b"\r\n", b"\n", b""):
                pass
            payload = stream.read(length)
        except (ValueError, OSError) as exc:
            raise SchemaError("malformed MCP frame") from exc
    else:
        payload = first
    return json.loads(payload)


def _write_message(stream: TextIO, response: dict) -> None:
    payload = json.dumps(response, separators=(",", ":"))
    stream.write(payload + "\n")
    stream.flush()


def serve(
    controller: WorkflowController,
    input_stream: BinaryIO | None = None,
    output_stream: TextIO | None = None,
) -> None:
    input_stream = input_stream or sys.stdin.buffer
    output_stream = output_stream or sys.stdout
    server = MCPServer(controller)
    while True:
        try:
            request = _read_message(input_stream)
            if request is None:
                return
            response = server.handle(request)
        except (json.JSONDecodeError, SchemaError) as exc:
            response = server._error(None, JSONRPC_ERRORS["PARSE_ERROR"], str(exc))
        if response is not None:
            _write_message(output_stream, response)
