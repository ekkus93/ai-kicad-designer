"""Run one Ollama model against an isolated MCP stdio backend and fixed task."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import shutil
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from ai_kicad.pivot.benchmark import (
    BenchmarkBackend,
    BenchmarkGate,
    BenchmarkGateStatus,
    BenchmarkModel,
    BenchmarkToolCall,
    BenchmarkTrial,
    score_gates,
    score_reference_inspection,
)
from ai_kicad.pivot.evidence import EvidenceArtifact, EvidenceStatus
from tools.pivot.experiment_paths import create_experiment_dir


class McpStdio:
    """Minimal line-framed MCP client for isolated stdio server processes."""

    def __init__(self, command: list[str], cwd: Path, env: dict[str, str]):
        self.command = command
        self.cwd = cwd
        self.env = env
        self.process = None
        self.request_id = 0
        self.stderr_task = None
        self.stderr_lines: list[str] = []

    async def start(self, timeout: float) -> dict:
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            cwd=self.cwd,
            env=self.env,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024,
        )
        self.stderr_task = asyncio.create_task(self._drain_stderr())
        initialized = await self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ai-kicad-pivot-benchmark", "version": "0.1.0"},
            },
            timeout,
        )
        await self.notify("notifications/initialized")
        return initialized

    async def _drain_stderr(self) -> None:
        assert self.process is not None and self.process.stderr is not None
        while line := await self.process.stderr.readline():
            self.stderr_lines.append(line.decode(errors="replace").rstrip())

    async def notify(self, method: str, params: dict | None = None) -> None:
        assert self.process is not None and self.process.stdin is not None
        message: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        await self.process.stdin.drain()

    async def request(self, method: str, params: dict, timeout: float) -> dict:
        assert self.process is not None and self.process.stdin is not None
        assert self.process.stdout is not None
        self.request_id += 1
        request_id = self.request_id
        message = {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        self.process.stdin.write((json.dumps(message) + "\n").encode())
        await self.process.stdin.drain()
        while True:
            line = await asyncio.wait_for(self.process.stdout.readline(), timeout)
            if not line:
                raise RuntimeError("MCP server closed stdout before responding")
            response = json.loads(line)
            if response.get("id") == request_id:
                return response

    async def close(self) -> int:
        if self.process is None:
            return -1
        if self.process.stdin is not None:
            self.process.stdin.close()
        try:
            return await asyncio.wait_for(self.process.wait(), timeout=5)
        except TimeoutError:
            self.process.kill()
            return await self.process.wait()


def ollama_chat(request: dict, endpoint: str, timeout: float) -> dict:
    data = json.dumps(request).encode()
    req = urllib.request.Request(
        endpoint.rstrip("/") + "/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def ollama_model_digest(model: str, endpoint: str, timeout: float) -> str:
    """Resolve the exact local Ollama model digest for a benchmark record."""
    req = urllib.request.Request(endpoint.rstrip("/") + "/api/tags")
    with urllib.request.urlopen(req, timeout=timeout) as response:
        models = json.load(response).get("models", [])
    for item in models:
        if item.get("name") == model or item.get("model") == model:
            return item["digest"].removeprefix("sha256:")
    raise ValueError(f"Ollama model {model!r} is not available at {endpoint}")


def _guard_paths(arguments: dict, workspace: Path) -> str | None:
    """Reject absolute or relative tool paths that point outside the run copy."""
    for key, value in arguments.items():
        if not isinstance(value, str):
            continue
        lowered = key.lower()
        path_field = lowered in {"project", "schematic", "board", "source", "target"} or any(
            word in lowered for word in ("path", "file", "output", "directory", "dir")
        )
        if not path_field and not Path(value).is_absolute():
            continue
        candidate = Path(value)
        resolved = (candidate if candidate.is_absolute() else workspace / candidate).resolve()
        if not resolved.is_relative_to(workspace.resolve()):
            return f"path argument {key!r} resolves outside the isolated workspace"
    return None


def _tool_definitions(tools: list[dict], allowed: set[str]) -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
            },
        }
        for tool in tools
        if tool["name"] in allowed
    ]


def _validate_dispatch(
    name: str, arguments: object, allowed: set[str], workspace: Path
) -> str | None:
    """Enforce tool visibility again at dispatch time, including forged model calls."""
    if name not in allowed:
        return "INVALID_TOOL_CALL"
    if not isinstance(arguments, dict):
        return "INVALID_TOOL_ARGUMENTS"
    return _guard_paths(arguments, workspace)


def _error_class(value: str, taxonomy: set[str]) -> str:
    """Normalize backend and harness errors to the suite's declared taxonomy."""
    upper = value.upper()
    if "UNSUPPORTED" in upper or "NOT IMPLEMENTED" in upper:
        candidate = "UNSUPPORTED_CAPABILITY"
    elif (
        "INVALID" in upper
        or "OUTSIDE THE ISOLATED WORKSPACE" in upper
        or "INVALID_ARGUMENT" in upper
    ):
        candidate = "INVALID_INPUT"
    elif "TIMEOUT" in upper or "TIMED OUT" in upper or "DEADLINE" in upper:
        candidate = "WALL_CLOCK_BUDGET_EXCEEDED"
    elif "CONNECTION REFUSED" in upper or "BACKEND UNAVAILABLE" in upper:
        candidate = "BACKEND_UNAVAILABLE"
    else:
        candidate = value
    return candidate if candidate in taxonomy else "UNKNOWN_TOOL_ERROR"


async def run_task(args: argparse.Namespace) -> Path:
    repo = args.repo_root.resolve()
    suite_path = args.suite.resolve()
    suite = json.loads(suite_path.read_text())
    fixture_manifest = repo / suite["fixture_manifest"]
    fixture = repo / "fixtures/pivot/reference_555_led_flasher_v1"
    task = next(item for item in suite["tasks"] if item["task_id"] == args.task)
    model_name = args.model or suite["model_profile"]["model"]
    model_digest = (
        suite["model_profile"]["model_digest"]
        if model_name == suite["model_profile"]["model"]
        else ollama_model_digest(model_name, args.ollama_endpoint, timeout=10)
    )
    budgets = suite["default_budgets"]
    taxonomy = set(suite["error_taxonomy"])
    time_limit = min(args.time_limit, budgets["time_limit_seconds"])
    token_limit = budgets["token_limit"]
    tool_limit = min(args.tool_call_limit, task.get("tool_call_limit", budgets["tool_call_limit"]))
    experiment = create_experiment_dir(repo, args.experiment_id)
    home = experiment / "home"
    home.mkdir()
    (home / ".config").mkdir()
    workspace = experiment / "workspace"
    shutil.copytree(args.project.resolve(), workspace)
    shutil.copyfile(fixture / "sym-lib-table", workspace / "sym-lib-table")
    initial_workspace_hashes = {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }
    config_path = experiment / "backend_config"
    if args.backend_config_template:
        config_path.write_text(
            args.backend_config_template.read_text()
            .replace("{workspace}", str(workspace))
            .replace("{experiment}", str(experiment))
        )
    server_command = [
        item.replace("{workspace}", str(workspace))
        .replace("{experiment}", str(experiment))
        .replace("{config}", str(config_path))
        for item in [args.server_command, *args.server_arg]
    ]
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "RUST_LOG": "warn",
        "MCP_BENCHMARK_WORKSPACE": str(workspace),
        "MCP_BENCHMARK_EXPERIMENT": str(experiment),
    }
    for item in args.server_env:
        key, separator, value = item.partition("=")
        if not separator or re.fullmatch(r"[A-Z_][A-Z0-9_]*", key) is None:
            raise ValueError("server environment entries must use KEY=value with uppercase keys")
        env[key] = (
            value.replace("{workspace}", str(workspace))
            .replace("{experiment}", str(experiment))
            .replace("{config}", str(config_path))
        )
    client = McpStdio(server_command, workspace, env)
    started = time.monotonic()
    compact_calls: list[BenchmarkToolCall] = []
    detailed_calls = []
    prompt_tokens = completion_tokens = 0
    final_text = ""
    tool_errors = []
    successfully_used: set[str] = set()
    final_prompt_sent = False
    server_info: dict | None = None
    execution_error: str | None = None
    exit_code = -1
    allowed = set(args.allow_tool)
    required_tools = set(args.require_tool or args.allow_tool)
    try:
        server_info = await asyncio.wait_for(client.start(min(30, time_limit)), timeout=35)
        for name in args.toolsets:
            response = await asyncio.wait_for(
                client.request(
                    "tools/call", {"name": "load_toolset", "arguments": {"name": name}}, 20
                ),
                timeout=22,
            )
            if response.get("error") or response.get("result", {}).get("isError"):
                raise RuntimeError(f"failed to load toolset {name}: {response}")
        listing = await asyncio.wait_for(client.request("tools/list", {}, 20), timeout=22)
        inventory = listing.get("result", {}).get("tools", [])
        if args.all_tools:
            allowed = {tool["name"] for tool in inventory}
            if not args.require_tool:
                required_tools = set()
        if not required_tools.issubset(allowed):
            raise ValueError("required tools must also be in the allowlist")
        definitions = _tool_definitions(inventory, allowed)
        if {item["function"]["name"] for item in definitions} != allowed:
            missing = sorted(allowed - {tool["name"] for tool in inventory})
            raise ValueError(f"allowed tools absent after loading toolsets: {missing}")
        if len(definitions) == 0:
            raise ValueError("at least one allowlisted tool is required")
        schematic = workspace / "Reference555LedFlasher.kicad_sch"
        user_prompt = (
            task["prompt"]
            + f"\nProject file: {workspace / 'Reference555LedFlasher.kicad_pro'}"
            + f"\nSchematic file: {schematic}"
            + "\nYou must call "
            + ", ".join(sorted(required_tools))
            + " before answering. Use the tool results "
            "for pin connectivity. Compute timing from the component values with units. "
            'Return exactly this JSON shape: {"pin_net_findings":[{"pin":1,"net":"GND"}], '
            '"timing_calculation":{"values":{"T_high_seconds":0,"T_low_seconds":0,'
            '"T_total_seconds":0,"frequency_hz":0}}, '
            '"LED_current_calculation":{"values":{"I_led_milliamps":0,'
            '"conservative_current_upper_bound_ma":0}},"defects":[],"uncertainty":""}. '
            "Include all eight NE555 pins, with the actual net names."
        )
        messages = [
            {
                "role": "system",
                "content": "You are being evaluated on tool use and engineering correctness. Call each required tool before answering. Do not infer a tool succeeded if it returned an error. Return only the requested JSON object and use numeric values in SI units.",
            },
            {"role": "user", "content": user_prompt},
        ]
        settings = {
            "temperature": suite["model_profile"]["temperature"],
            "num_ctx": suite["model_profile"]["num_ctx"],
            "num_predict": suite["model_profile"]["num_predict"],
        }
        for _ in range(tool_limit + 1):
            remaining = time_limit - (time.monotonic() - started)
            if remaining <= 0:
                raise TimeoutError("wall-clock budget exceeded")
            tools_complete = required_tools.issubset(successfully_used)
            if tools_complete and not final_prompt_sent:
                messages.append(
                    {
                        "role": "user",
                        "content": "All required tools have run. Return only the requested JSON object, with no explanation or markdown.",
                    }
                )
                final_prompt_sent = True
            chat_request = {
                "model": model_name,
                "messages": messages,
                "tools": [] if tools_complete else definitions,
                "stream": False,
                "think": False,
                "options": settings,
            }
            if tools_complete:
                chat_request["format"] = "json"
            response = await asyncio.wait_for(
                asyncio.to_thread(
                    ollama_chat,
                    chat_request,
                    args.ollama_endpoint,
                    remaining,
                ),
                timeout=remaining + 1,
            )
            prompt_tokens += int(response.get("prompt_eval_count", 0))
            completion_tokens += int(response.get("eval_count", 0))
            message = response["message"]
            if prompt_tokens + completion_tokens > token_limit:
                tool_errors.append("TOKEN_BUDGET_EXCEEDED")
                final_text = message.get("content", "")
                break
            messages.append(message)
            calls = message.get("tool_calls", [])
            if not calls:
                final_text = message.get("content", "")
                break
            for tool_call in calls:
                function = tool_call["function"]
                name = function["name"]
                arguments = function.get("arguments", {})
                error = None
                call_error_class = None
                result = None
                call_start = time.monotonic()
                if len(compact_calls) >= tool_limit:
                    error = "TOOL_CALL_BUDGET_EXCEEDED"
                else:
                    error = _validate_dispatch(name, arguments, allowed, workspace)
                if error:
                    tool_errors.append(_error_class(error, taxonomy))
                    result_text = json.dumps({"error": error, "dispatched": False})
                    valid = False
                else:
                    rpc_result = await asyncio.wait_for(
                        client.request(
                            "tools/call", {"name": name, "arguments": arguments}, remaining
                        ),
                        timeout=remaining,
                    )
                    result = rpc_result
                    result_text = json.dumps(rpc_result.get("result", rpc_result))
                    if len(result_text) > 32_000:
                        result_text = (
                            result_text[:32_000] + " [tool response truncated for model context]"
                        )
                    valid = not bool(
                        rpc_result.get("error") or rpc_result.get("result", {}).get("isError")
                    )
                    if valid:
                        successfully_used.add(name)
                    else:
                        tool_text = json.dumps(rpc_result)
                        call_error_class = _error_class(tool_text, taxonomy)
                        tool_errors.append(call_error_class)
                duration_ms = int((time.monotonic() - call_start) * 1000)
                compact_calls.append(
                    BenchmarkToolCall(
                        tool_name=name,
                        duration_ms=duration_ms,
                        error_class=(
                            _error_class(error, taxonomy)
                            if error
                            else (
                                call_error_class or _error_class("TOOL_ERROR", taxonomy)
                                if not valid
                                else None
                            )
                        ),
                        valid=valid,
                    )
                )
                detailed_calls.append(
                    {"tool_name": name, "arguments": arguments, "error": error, "response": result}
                )
                messages.append({"role": "tool", "tool_name": name, "content": result_text})
        else:
            tool_errors.append("TOOL_CALL_BUDGET_EXCEEDED")
            messages.append(
                {"role": "user", "content": "Stop calling tools and return your JSON result now."}
            )
            final_text = messages[-2].get("content", "")
    except Exception as exc:
        execution_error = f"{type(exc).__name__}: {exc}"
        tool_errors.append(_error_class(execution_error, taxonomy))
    finally:
        exit_code = await client.close()

    duration = time.monotonic() - started
    try:
        model_result = json.loads(final_text)
        gates = score_reference_inspection(
            model_result,
            json.loads((fixture / "design.json").read_text()),
            json.loads((fixture / "expected_behavior.json").read_text()),
            evidence_path="model_output.json",
        )
    except (json.JSONDecodeError, TypeError, KeyError) as exc:
        model_result = {"raw": final_text, "parse_error": str(exc)}
        gates = [
            BenchmarkGate(
                gate_id="structured_final_response",
                status=BenchmarkGateStatus.FAIL,
                summary="Model did not return valid structured JSON.",
                independent=True,
                evidence_paths=["model_output.json"],
            )
        ]
    if execution_error:
        gates.append(
            BenchmarkGate(
                gate_id="backend_execution",
                status=BenchmarkGateStatus.FAIL,
                summary=execution_error,
                independent=False,
                evidence_paths=["backend_error.json"],
            )
        )
    response_path = experiment / "model_output.json"
    response_path.write_text(json.dumps(model_result, indent=2) + "\n")
    (experiment / "mcp_tool_calls.json").write_text(json.dumps(detailed_calls, indent=2) + "\n")
    (experiment / "server_stderr.log").write_text("\n".join(client.stderr_lines) + "\n")
    workspace_hashes = {
        str(path.relative_to(workspace)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(workspace.rglob("*"))
        if path.is_file()
    }
    source_schematic = args.project.resolve() / "Reference555LedFlasher.kicad_sch"
    source_hash = hashlib.sha256(source_schematic.read_bytes()).hexdigest()
    changed_inputs = [
        rel
        for rel, digest in initial_workspace_hashes.items()
        if hashlib.sha256((workspace / rel).read_bytes()).hexdigest() != digest
    ]
    workspace_integrity = {
        "initial_input_hashes": initial_workspace_hashes,
        "changed_input_paths": changed_inputs,
        "new_workspace_paths": sorted(
            str(path.relative_to(workspace))
            for path in workspace.rglob("*")
            if path.is_file() and str(path.relative_to(workspace)) not in initial_workspace_hashes
        ),
        "unchanged": not changed_inputs,
    }
    integrity_path = experiment / "workspace_integrity.json"
    integrity_path.write_text(json.dumps(workspace_integrity, indent=2) + "\n")
    if execution_error:
        (experiment / "backend_error.json").write_text(
            json.dumps({"error": execution_error}, indent=2) + "\n"
        )
    output_path = experiment / "trial.json"
    artifacts = [
        EvidenceArtifact(
            path="model_output.json",
            sha256=hashlib.sha256(response_path.read_bytes()).hexdigest(),
            media_type="application/json",
            role="model_final_response",
        ),
        EvidenceArtifact(
            path="mcp_tool_calls.json",
            sha256=hashlib.sha256((experiment / "mcp_tool_calls.json").read_bytes()).hexdigest(),
            media_type="application/json",
            role="backend_call_trace",
        ),
        EvidenceArtifact(
            path="workspace_integrity.json",
            sha256=hashlib.sha256(integrity_path.read_bytes()).hexdigest(),
            media_type="application/json",
            role="workspace_input_integrity",
        ),
    ]
    if execution_error:
        artifacts.append(
            EvidenceArtifact(
                path="backend_error.json",
                sha256=hashlib.sha256((experiment / "backend_error.json").read_bytes()).hexdigest(),
                media_type="application/json",
                role="backend_execution_failure",
            )
        )
    used_tools = {call.tool_name for call in compact_calls if call.valid}
    tool_use_pass = required_tools.issubset(used_tools)
    gates.append(
        BenchmarkGate(
            gate_id="required_mcp_tool_use",
            status=BenchmarkGateStatus.PASS if tool_use_pass else BenchmarkGateStatus.FAIL,
            summary=(
                "The model used every task-required MCP tool."
                if tool_use_pass
                else f"Required MCP tools not successfully used: {sorted(required_tools - used_tools)}."
            ),
            independent=False,
            evidence_paths=["mcp_tool_calls.json"],
        )
    )
    gates.append(
        BenchmarkGate(
            gate_id="workspace_inputs_unchanged",
            status=(BenchmarkGateStatus.PASS if not changed_inputs else BenchmarkGateStatus.FAIL),
            summary=(
                "All files present before backend execution are unchanged."
                if not changed_inputs
                else f"Backend modified initial workspace inputs: {changed_inputs}."
            ),
            independent=True,
            evidence_paths=["workspace_integrity.json"],
        )
    )
    for gate_id, exceeded in (
        ("tool_call_budget", len(compact_calls) > tool_limit),
        ("token_budget", prompt_tokens + completion_tokens > token_limit),
        ("wall_clock_budget", duration > time_limit),
    ):
        gates.append(
            BenchmarkGate(
                gate_id=gate_id,
                status=BenchmarkGateStatus.FAIL if exceeded else BenchmarkGateStatus.PASS,
                summary="Observed usage exceeds its configured budget."
                if exceeded
                else "Observed usage is within its configured budget.",
                independent=True,
                evidence_paths=["usage_report.json"],
            )
        )
    usage_path = experiment / "usage_report.json"
    usage_path.write_text(
        json.dumps(
            {
                "elapsed_seconds": duration,
                "time_limit_seconds": time_limit,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "token_count": prompt_tokens + completion_tokens,
                "token_limit": token_limit,
                "tool_call_count": len(compact_calls),
                "tool_call_limit": tool_limit,
                "error_taxonomy_events": tool_errors,
            },
            indent=2,
        )
        + "\n"
    )
    artifacts.append(
        EvidenceArtifact(
            path="usage_report.json",
            sha256=hashlib.sha256(usage_path.read_bytes()).hexdigest(),
            media_type="application/json",
            role="budget_usage_report",
        )
    )
    schematic_unchanged = (
        source_hash
        == hashlib.sha256((workspace / "Reference555LedFlasher.kicad_sch").read_bytes()).hexdigest()
    )
    gates.append(
        BenchmarkGate(
            gate_id="source_schematic_unchanged",
            status=BenchmarkGateStatus.PASS if schematic_unchanged else BenchmarkGateStatus.FAIL,
            summary=(
                "The protected source schematic is unchanged."
                if schematic_unchanged
                else "The source schematic changed during the task."
            ),
            independent=True,
            evidence_paths=["mcp_tool_calls.json"],
        )
    )
    status = (
        EvidenceStatus.PASS
        if gates
        and all(gate.status is BenchmarkGateStatus.PASS for gate in gates)
        and not tool_errors
        else EvidenceStatus.FAIL
    )
    trial = BenchmarkTrial(
        schema_version="pivot-benchmark.v1",
        trial_id=args.experiment_id,
        task_id=task["task_id"],
        fixture_sha256=hashlib.sha256(fixture_manifest.read_bytes()).hexdigest(),
        recorded_at_utc=datetime.now(timezone.utc),
        model=BenchmarkModel(
            provider="ollama",
            model=model_name,
            digest=model_digest,
            settings=settings,
        ),
        backend=BenchmarkBackend(
            name=args.backend_name,
            version=args.backend_version,
            build_id=args.backend_build_id,
            mode=args.mode,
        ),
        time_limit_seconds=time_limit,
        token_limit=token_limit,
        tool_call_limit=tool_limit,
        elapsed_seconds=duration,
        token_count=prompt_tokens + completion_tokens,
        tool_calls=compact_calls,
        gates=gates,
        artifacts=artifacts,
        status=status,
    )
    record = {
        "trial": json.loads(trial.model_dump_json()),
        "server_info": (server_info or {}).get("result", {}).get("serverInfo"),
        "tool_errors": tool_errors,
        "process_exit_code": exit_code,
        "source_schematic_sha256": source_hash,
        "source_schematic_unchanged": schematic_unchanged,
        "workspace_hashes": workspace_hashes,
        "scores": score_gates(gates),
    }
    output_path.write_text(json.dumps(record, indent=2) + "\n")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--suite", type=Path, default=Path("fixtures/pivot/benchmark_suite_v1.json")
    )
    parser.add_argument("--task", default="inspect_reference_circuit")
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument(
        "--project", type=Path, required=True, help="Native KiCad project directory to copy"
    )
    parser.add_argument("--server-command", required=True, help="MCP server executable")
    parser.add_argument(
        "--server-arg", action="append", default=[], help="Argument passed to server"
    )
    parser.add_argument("--backend-config-template", type=Path)
    parser.add_argument("--toolsets", nargs="*", default=[])
    parser.add_argument("--allow-tool", action="append", default=[])
    parser.add_argument(
        "--all-tools",
        action="store_true",
        help="Expose every tool returned after loading the selected toolsets",
    )
    parser.add_argument("--require-tool", action="append", default=[])
    parser.add_argument(
        "--server-env", action="append", default=[], help="Child environment KEY=value"
    )
    parser.add_argument("--model", help="Override the suite's Ollama model for comparative trials")
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--time-limit", type=int, default=240)
    parser.add_argument("--tool-call-limit", type=int, default=24)
    parser.add_argument("--backend-name", required=True)
    parser.add_argument("--backend-version", required=True)
    parser.add_argument("--backend-build-id", required=True)
    parser.add_argument(
        "--mode",
        choices=("full_inventory", "phase_gated", "task_gated", "direct"),
        default="task_gated",
    )
    args = parser.parse_args()
    if not args.all_tools and not args.allow_tool:
        parser.error("provide --allow-tool or --all-tools")
    args.suite = (args.repo_root / args.suite).resolve()
    path = asyncio.run(run_task(args))
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
