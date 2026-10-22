"""Capture and validate the host toolchain used by the MCP pivot."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run(command: list[str], *, timeout: int = 30) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, check=False, capture_output=True, text=True, timeout=timeout
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"command": command, "returncode": None, "stdout": "", "stderr": str(exc)}
    return {
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def _cpu_model() -> str | None:
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.is_file():
        return None
    for line in cpuinfo.read_text(errors="replace").splitlines():
        if line.startswith("model name"):
            return line.split(":", 1)[1].strip()
    return None


def _ollama_models(endpoint: str) -> tuple[list[dict[str, Any]], str | None]:
    request = urllib.request.Request(endpoint.rstrip("/") + "/api/tags")
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            payload = json.load(response)
    except (OSError, urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        return [], str(exc)
    models = payload.get("models")
    if not isinstance(models, list):
        return [], "Ollama returned no model inventory"
    return [
        {"name": item.get("name"), "digest": item.get("digest"), "size": item.get("size")}
        for item in models
        if isinstance(item, dict)
    ], None


def capture(root: Path, ollama_endpoint: str) -> dict[str, Any]:
    lock_path = root / "fixtures/m1a/toolchain.lock.json"
    lock = json.loads(lock_path.read_text())
    cpu_model = _cpu_model()
    platform_actual = {
        "os": platform.platform(),
        "architecture": platform.machine(),
        "cpu": platform.processor() or platform.machine(),
        "cpu_model": cpu_model,
    }
    platform_expected = lock.get("platform", {})
    platform_match = all(
        platform_actual.get(key) == platform_expected.get(key) for key in platform_expected
    )

    locked_files: list[dict[str, Any]] = []
    for group in ("executables", "libraries"):
        for item in lock[group]:
            path = Path(item["path"])
            actual = _sha256(path)
            locked_files.append(
                {
                    "id": item["id"],
                    "path": str(path),
                    "expected_sha256": item.get("file_sha256"),
                    "actual_sha256": actual,
                    "matches": actual == item.get("file_sha256"),
                }
            )

    launcher = next(item["path"] for item in lock["executables"] if item["id"] == "kicad-cli")
    kicad_version = _run([launcher, "kicad-cli", "version"])
    uv_version = _run(["uv", "--version"])
    ruff_version = _run([sys.executable, "-m", "ruff", "--version"])
    pytest_version = _run([sys.executable, "-m", "pytest", "--version"])
    ollama_version = _run(["ollama", "--version"])
    models, ollama_error = _ollama_models(ollama_endpoint)
    gpu_probe = _run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"], timeout=10
    )

    git_head = _run(["git", "-C", str(root), "rev-parse", "HEAD"])
    git_branch = _run(["git", "-C", str(root), "branch", "--show-current"])
    checks = {
        "python_3_12": sys.version_info[:2] == (3, 12),
        "uv_available": uv_version["returncode"] == 0,
        "ruff_available": ruff_version["returncode"] == 0,
        "pytest_available": pytest_version["returncode"] == 0,
        "locked_platform_matches": platform_match,
        "locked_kicad_version_matches": (
            kicad_version["returncode"] == 0
            and kicad_version["stdout"] == lock["executables"][0]["version"]
        ),
        "locked_file_hashes_match": all(item["matches"] for item in locked_files),
    }
    return {
        "schema_version": "mcp-pivot-host-environment.v1",
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository_root": str(root),
        "git": {"branch": git_branch["stdout"], "head": git_head["stdout"]},
        "host": {
            "os": platform_actual["os"],
            "architecture": platform_actual["architecture"],
            "cpu_model": cpu_model,
            "gpu": gpu_probe["stdout"] if gpu_probe["returncode"] == 0 else None,
        },
        "python": {"version": platform.python_version(), "executable": sys.executable},
        "uv": uv_version,
        "ruff": ruff_version,
        "pytest": pytest_version,
        "kicad": {
            "lock_path": str(lock_path.relative_to(root)),
            "lock_sha256": _sha256(lock_path),
            "platform_expected": platform_expected,
            "platform_actual": platform_actual,
            "version_probe": kicad_version,
            "locked_files": locked_files,
        },
        "ollama": {
            "version": ollama_version,
            "endpoint": ollama_endpoint,
            "models": models,
            "error": ollama_error,
        },
        "runner_policy": {
            "containers": "not used; host tools are pinned and invoked directly",
            "external_ordering": "disabled; no fabrication or procurement performed",
        },
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument(
        "--output", type=Path, default=Path("fixtures/pivot/host_environment_manifest.json")
    )
    parser.add_argument("--ollama-endpoint", default="http://127.0.0.1:11434")
    parser.add_argument("--require-ollama-model")
    args = parser.parse_args()

    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    output = output.resolve()
    if not output.is_relative_to(root):
        parser.error("--output must be inside the repository root")

    report = capture(root, args.ollama_endpoint)
    if args.require_ollama_model and args.require_ollama_model not in {
        item["name"] for item in report["ollama"]["models"]
    }:
        report["checks"]["required_ollama_model_available"] = False
        report["status"] = "FAIL"
    elif args.require_ollama_model:
        report["checks"]["required_ollama_model_available"] = True

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {"status": report["status"], "output": str(output), "checks": report["checks"]},
            indent=2,
        )
    )
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
