"""Generate and independently screen bounded AI circuit-topology proposals."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import time
from urllib.error import URLError
from urllib.request import Request, urlopen

from tools.pivot.experiment_paths import create_experiment_dir


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _post_json(url: str, payload: dict, timeout: float = 180.0) -> dict:
    request = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _component_values(proposal: dict) -> dict[str, dict]:
    components = proposal.get("components")
    if not isinstance(components, list):
        raise ValueError("components must be an array")
    values = {}
    for component in components:
        if not isinstance(component, dict) or not isinstance(component.get("ref"), str):
            raise ValueError("each component must have a string ref")
        if component["ref"] in values:
            raise ValueError(f"duplicate component reference: {component['ref']}")
        if (
            not isinstance(component.get("kind"), str)
            or not isinstance(component.get("pins"), list)
            or not component["pins"]
            or any(not isinstance(pin, str) for pin in component["pins"])
        ):
            raise ValueError(f"component {component['ref']} has an invalid kind or pin list")
        if component["kind"] not in {"resistor", "capacitor", "led", "timer555", "port", "ground"}:
            raise ValueError(f"unsupported component kind: {component['kind']}")
        if (
            "value" not in component
            or component["value"] is not None
            and not isinstance(component["value"], str)
        ):
            raise ValueError(f"component {component['ref']} has an invalid value")
        if len(set(component["pins"])) != len(component["pins"]):
            raise ValueError(f"component {component['ref']} has duplicate pins")
        values[component["ref"]] = component
    return values


def _graph(proposal: dict) -> tuple[dict[str, dict], dict[str, str]]:
    components = _component_values(proposal)
    nets = proposal.get("nets")
    if not isinstance(nets, list):
        raise ValueError("nets must be an array")
    terminal_to_net: dict[str, str] = {}
    seen_nets = set()
    for net in nets:
        if (
            not isinstance(net, dict)
            or not isinstance(net.get("name"), str)
            or not isinstance(net.get("terminals"), list)
            or len(net["terminals"]) < 2
        ):
            raise ValueError("each net needs a name and at least two terminals")
        if net["name"] in seen_nets:
            raise ValueError(f"duplicate net name: {net['name']}")
        seen_nets.add(net["name"])
        for terminal in net["terminals"]:
            if not isinstance(terminal, str) or terminal.count(".") != 1:
                raise ValueError(f"invalid terminal identity: {terminal!r}")
            reference, pin = terminal.split(".")
            if reference not in components or pin not in components[reference]["pins"]:
                raise ValueError(f"unknown component terminal: {terminal}")
            if terminal in terminal_to_net:
                raise ValueError(f"terminal assigned more than once: {terminal}")
            terminal_to_net[terminal] = net["name"]

    expected_terminals = {
        f"{reference}.{pin}"
        for reference, component in components.items()
        for pin in component["pins"]
    }
    missing = expected_terminals - set(terminal_to_net)
    if missing:
        raise ValueError(f"unassigned component terminals: {sorted(missing)}")
    return components, terminal_to_net


def _value(value: object, *, quantity: str) -> float:
    if not isinstance(value, str):
        raise ValueError(f"{quantity} value must be a string")
    normalized = value.strip().replace("Ω", "ohm").replace("µ", "u").replace("μ", "u")
    multipliers = {"p": 1e-12, "n": 1e-9, "u": 1e-6, "m": 1e-3, "k": 1e3, "meg": 1e6, "g": 1e9}
    for unit in ("farads", "farad", "f", "ohms", "ohm", "v", "hz"):
        if normalized.lower().endswith(unit):
            normalized = normalized[: -len(unit)].strip()
            break
    text = normalized.lower().replace(" ", "")
    factor = 1.0
    suffix = next(
        (key for key in ("meg", "p", "n", "u", "m", "k", "g") if text.endswith(key)), None
    )
    if suffix:
        factor = multipliers[suffix]
        text = text[: -len(suffix)]
    try:
        result = float(text) * factor
    except ValueError as error:
        raise ValueError(f"unparseable {quantity} value: {value!r}") from error
    if result <= 0:
        raise ValueError(f"{quantity} value must be positive")
    return result


def evaluate_proposal(task: dict, raw_response: str) -> dict:
    checks = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    try:
        proposal = json.loads(raw_response)
        if not isinstance(proposal, dict) or not isinstance(proposal.get("topology"), str):
            raise ValueError("proposal must be an object with a topology description")
        components, terminal_net = _graph(proposal)
        check("structured_graph", True, "All component terminals map exactly once to named nets.")
    except (json.JSONDecodeError, ValueError) as error:
        check("structured_graph", False, str(error))
        return {
            "task_id": task["task_id"],
            "status": "FAIL",
            "checks": checks,
            "metrics": {},
            "downstream_gates": {
                "spice": "NOT_RUN_STRUCTURED_GRAPH_REJECTED",
                "native_kicad": "NOT_RUN_STRUCTURED_GRAPH_REJECTED",
                "human_electrical_review": "PENDING",
            },
        }

    family = task["family"]
    metrics: dict[str, float] = {}
    try:
        if family == "rc_lowpass":
            resistor, capacitor = components["R1"], components["C1"]
            topology_ok = (
                resistor["kind"] == "resistor"
                and capacitor["kind"] == "capacitor"
                and set(components) == {"R1", "C1", "VIN", "VOUT", "GND"}
                and {terminal_net["R1.A"], terminal_net["R1.B"]} == {"VIN", "VOUT"}
                and {terminal_net["C1.A"], terminal_net["C1.B"]} == {"VOUT", "GND"}
                and terminal_net["VIN.1"] == "VIN"
                and terminal_net["VOUT.1"] == "VOUT"
                and terminal_net["GND.1"] == "GND"
                and {item["kind"] for item in components.values()}
                == {"resistor", "capacitor", "port", "ground"}
            )
            check(
                "rc_topology",
                topology_ok,
                "Series R, output shunt C, and distinct source/output/return nodes.",
            )
            cutoff_hz = 1 / (
                2
                * 3.141592653589793
                * _value(resistor.get("value"), quantity="resistance")
                * _value(capacitor.get("value"), quantity="capacitance")
            )
            metrics["cutoff_hz"] = cutoff_hz
            limits = task["limits"]
            check(
                "cutoff_target",
                limits["cutoff_min_hz"] <= cutoff_hz <= limits["cutoff_max_hz"],
                f"independent RC calculation gives {cutoff_hz:.6g} Hz; target range is "
                f"{limits['cutoff_min_hz']}-{limits['cutoff_max_hz']} Hz.",
            )
        elif family == "led_limiter":
            resistor, led = components["R1"], components["D1"]
            topology_ok = (
                resistor["kind"] == "resistor"
                and led["kind"] == "led"
                and set(components) == {"R1", "D1", "VIN", "GND", "OUT"}
                and terminal_net["VIN.1"] == "VIN"
                and terminal_net["GND.1"] == "GND"
                and terminal_net["OUT.1"] == terminal_net["D1.A"]
                and terminal_net["D1.K"] == "GND"
                and {terminal_net["R1.A"], terminal_net["R1.B"]} == {"VIN", terminal_net["D1.A"]}
                and {item["kind"] for item in components.values()}
                == {"resistor", "led", "port", "ground"}
            )
            check(
                "led_series_topology",
                topology_ok,
                "The resistor and correctly oriented LED form one series path.",
            )
            resistance = _value(resistor.get("value"), quantity="resistance")
            limits = task["limits"]
            minimum_current = (limits["supply_v"] - limits["led_forward_max_v"]) / resistance
            maximum_current = (limits["supply_v"] - limits["led_forward_min_v"]) / resistance
            metrics.update(
                minimum_led_current_a=minimum_current, maximum_led_current_a=maximum_current
            )
            current_ok = (
                minimum_current >= limits["current_min_a"]
                and maximum_current <= limits["current_max_a"]
            )
            check(
                "led_current_bounds",
                current_ok,
                f"independent worst-case current is {minimum_current * 1e3:.3f}-"
                f"{maximum_current * 1e3:.3f} mA; allowed range is "
                f"{limits['current_min_a'] * 1e3:.3f}-{limits['current_max_a'] * 1e3:.3f} mA.",
            )
        elif family == "timer555_astable":
            timer = components["U1"]
            r_charge, r_discharge, capacitor = components["R1"], components["R2"], components["C1"]
            led_resistor, led = components["R3"], components["D1"]
            topology_ok = (
                timer["kind"] == "timer555"
                and r_charge["kind"] == "resistor"
                and r_discharge["kind"] == "resistor"
                and capacitor["kind"] == "capacitor"
                and led_resistor["kind"] == "resistor"
                and led["kind"] == "led"
                and components["C2"]["kind"] == "capacitor"
                and set(components)
                == {"U1", "R1", "R2", "C1", "R3", "D1", "C2", "VIN", "GND", "OUT"}
                and terminal_net["U1.8"] == "VIN"
                and terminal_net["U1.4"] == "VIN"
                and terminal_net["U1.1"] == "GND"
                and terminal_net["U1.2"] == terminal_net["U1.6"]
                and {terminal_net["R1.A"], terminal_net["R1.B"]} == {"VIN", terminal_net["U1.7"]}
                and {terminal_net["R2.A"], terminal_net["R2.B"]}
                == {terminal_net["U1.7"], terminal_net["U1.2"]}
                and {terminal_net["C1.A"], terminal_net["C1.B"]} == {terminal_net["U1.2"], "GND"}
                and terminal_net["U1.3"] == terminal_net["OUT.1"]
                and {terminal_net["R3.A"], terminal_net["R3.B"]}
                == {terminal_net["U1.3"], terminal_net["D1.A"]}
                and terminal_net["D1.K"] == "GND"
                and {terminal_net["C2.A"], terminal_net["C2.B"]} == {terminal_net["U1.5"], "GND"}
                and terminal_net["GND.1"] == "GND"
            )
            check(
                "timer_astable_topology",
                topology_ok,
                "NE555 supply/reset/timing/LED connections match the required topology.",
            )
            charge = _value(r_charge.get("value"), quantity="charge resistance")
            discharge = _value(r_discharge.get("value"), quantity="discharge resistance")
            capacitance = _value(capacitor.get("value"), quantity="timing capacitance")
            frequency = 1.44 / ((charge + 2 * discharge) * capacitance)
            metrics["frequency_hz"] = frequency
            limits = task["limits"]
            check(
                "oscillator_frequency",
                limits["frequency_min_hz"] <= frequency <= limits["frequency_max_hz"],
                f"independent 555 astable estimate is {frequency:.6g} Hz; target range is "
                f"{limits['frequency_min_hz']}-{limits['frequency_max_hz']} Hz.",
            )
            resistance = _value(led_resistor.get("value"), quantity="LED resistance")
            minimum_current = (limits["supply_v"] - limits["led_forward_max_v"]) / resistance
            maximum_current = (limits["supply_v"] - limits["led_forward_min_v"]) / resistance
            metrics.update(
                minimum_led_current_a=minimum_current, maximum_led_current_a=maximum_current
            )
            check(
                "led_current_bounds",
                minimum_current >= limits["led_current_min_a"]
                and maximum_current <= limits["led_current_max_a"],
                f"independent LED current estimate is {minimum_current * 1e3:.3f}-"
                f"{maximum_current * 1e3:.3f} mA.",
            )
        else:
            raise ValueError(f"unsupported task family: {family}")
    except (KeyError, TypeError, ValueError) as error:
        check("independent_calculation", False, str(error))

    passed = all(result["status"] == "PASS" for result in checks)
    return {
        "task_id": task["task_id"],
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "metrics": metrics,
        "downstream_gates": {
            "spice": "NOT_RUN" if not passed else "REQUIRES_CASE_SPECIFIC_REVIEW",
            "native_kicad": "NOT_RUN"
            if not passed
            else "REQUIRES_APPROVED_SYMBOL_AND_FOOTPRINT_MAP",
            "human_electrical_review": "PENDING",
        },
    }


def _model_identity(base_url: str, model_name: str) -> dict:
    with urlopen(f"{base_url.rstrip('/')}/api/tags", timeout=10) as response:
        models = json.load(response)["models"]
    matches = [model for model in models if model["name"] == model_name]
    if len(matches) != 1:
        raise ValueError(f"Ollama model not found exactly once: {model_name}")
    model = matches[0]
    with urlopen(f"{base_url.rstrip('/')}/api/version", timeout=10) as response:
        ollama_version = json.load(response).get("version")
    return {
        "name": model["name"],
        "digest": model["digest"],
        "parameter_size": model.get("details", {}).get("parameter_size"),
        "quantization_level": model.get("details", {}).get("quantization_level"),
        "ollama_version": ollama_version,
    }


def run_suite(
    root: Path, suite_path: Path, experiment_id: str, model_name: str, base_url: str
) -> Path:
    root = root.resolve()
    suite_path = suite_path.resolve()
    if not suite_path.is_relative_to(root):
        raise ValueError("suite path must be inside the repository")
    suite_bytes = suite_path.read_bytes()
    suite = json.loads(suite_bytes)
    model = _model_identity(base_url, model_name)
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    output = create_experiment_dir(root, experiment_id)
    raw_dir = output / "raw"
    raw_dir.mkdir()
    results = []

    for task in suite["tasks"]:
        prompt = (
            task["prompt"]
            + "\nResponse schema: "
            + json.dumps(suite["response_schema"], separators=(",", ":"))
        )
        payload = {
            "model": model_name,
            "prompt": prompt,
            "format": "json",
            "think": False,
            "stream": False,
            "options": {"temperature": 0, "seed": 20261023, "num_predict": 1800},
        }
        started = time.monotonic()
        generation = _post_json(f"{base_url.rstrip('/')}/api/generate", payload)
        elapsed = time.monotonic() - started
        response = generation.get("response", "")
        raw_record = {
            "task_id": task["task_id"],
            "prompt": prompt,
            "request": payload,
            "response": response,
            "done_reason": generation.get("done_reason"),
            "prompt_eval_count": generation.get("prompt_eval_count"),
            "eval_count": generation.get("eval_count"),
            "elapsed_s": round(elapsed, 3),
            "response_sha256": _sha256(response.encode()),
        }
        (raw_dir / f"{task['task_id']}.json").write_text(json.dumps(raw_record, indent=2) + "\n")
        result = evaluate_proposal(task, response)
        result["raw_output_path"] = f"raw/{task['task_id']}.json"
        result["raw_output_sha256"] = _sha256((raw_dir / f"{task['task_id']}.json").read_bytes())
        results.append(result)

    assessment = {
        "schema_version": "ai-topology-assessment.v1",
        "suite_id": suite["suite_id"],
        "suite_path": suite_path.relative_to(root).as_posix(),
        "suite_sha256": _sha256(suite_bytes),
        "model": model,
        "source_commit": source_commit,
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "sampling": {"temperature": 0, "seed": 20261023, "think": False},
        "task_count": len(results),
        "passed": sum(result["status"] == "PASS" for result in results),
        "failed": sum(result["status"] == "FAIL" for result in results),
        "results": results,
        "human_review": "PENDING",
        "overall_status": "PASS"
        if results and all(result["status"] == "PASS" for result in results)
        else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    reports = output / "reports"
    reports.mkdir()
    assessment_path = reports / "assessment.json"
    assessment_path.write_text(json.dumps(assessment, indent=2) + "\n")
    artifact_hashes = {
        path.relative_to(output).as_posix(): _sha256(path.read_bytes())
        for path in sorted(output.rglob("*"))
        if path.is_file()
    }
    manifest = {
        "schema_version": "ai-topology-experiment-manifest.v1",
        "experiment_id": experiment_id,
        "source_commit": source_commit,
        "suite_sha256": _sha256(suite_bytes),
        "model_digest": model["digest"],
        "artifacts": artifact_hashes,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--suite", type=Path, default=Path("fixtures/pivot/heldout_topology_suite_v1.json")
    )
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    try:
        output = run_suite(root, args.suite, args.experiment_id, args.model, args.ollama_url)
    except (OSError, ValueError, json.JSONDecodeError, URLError) as error:
        parser.exit(2, f"AI topology evaluation failed: {error}\n")
    assessment = json.loads((output / "reports/assessment.json").read_text())
    print(f"experiment={output}")
    print(
        f"overall_status={assessment['overall_status']} passed={assessment['passed']} failed={assessment['failed']}"
    )
    return 0 if assessment["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
