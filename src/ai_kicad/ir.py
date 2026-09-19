"""Strict M1 divider profile with explicit intentional NC variant."""

import copy
import json
from pathlib import Path


class InputError(ValueError):
    pass


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise InputError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(), object_pairs_hook=_object)
    except (OSError, ValueError) as exc:
        raise InputError(str(exc)) from exc
    if not isinstance(data, dict):
        raise InputError("JSON root must be an object")
    return data


def canonicalize(raw: dict) -> dict:
    """Sort only collections declared unordered by the M1 profile."""
    data = copy.deepcopy(raw)
    for key in ("assets", "evidence"):
        data[key].sort(key=lambda item: item["id"])
    for key in ("components", "nets", "blocks", "domains", "relationships"):
        data["logical"][key].sort(key=lambda item: item["id"])
    data["logical"]["no_connects"].sort(
        key=lambda item: (item["terminal"]["component"], item["terminal"]["terminal"])
    )
    for component in data["logical"]["components"]:
        component["terminals"].sort(key=lambda item: item["id"])
    for net in data["logical"]["nets"]:
        net["members"].sort(key=lambda item: (item["component"], item["terminal"]))
    for key in ("symbols", "constraints"):
        data["schematic"][key].sort(key=lambda item: item["id"])
    return data


def validate(raw: dict, reference: dict | None = None) -> dict:
    """Check the two reviewed M1 divider forms and reject future capabilities.

    The exemplar is a profile vocabulary, never an artifact observation source.
    """
    if reference is None:
        reference = load_json(Path(__file__).resolve().parents[2] / "fixtures/m1a/divider.json")
    try:
        members = [
            (member["component"], member["terminal"])
            for net in raw["logical"]["nets"]
            for member in net["members"]
        ]
        nc = [
            (item["terminal"]["component"], item["terminal"]["terminal"])
            for item in raw["logical"]["no_connects"]
        ]
    except (KeyError, TypeError) as exc:
        raise InputError("invalid terminal membership") from exc
    if len(members + nc) != len(set(members + nc)):
        raise InputError("duplicate terminal membership")
    try:
        data = canonicalize(raw)
    except (KeyError, TypeError, AttributeError) as exc:
        raise InputError("unsupported M1 structure") from exc
    exemplar = canonicalize(reference)
    variant = any(
        asset.get("library_id") == "Connector_Generic:Conn_01x04" for asset in data["assets"]
    )
    if variant:
        connector_asset = next(a for a in exemplar["assets"] if a["id"] == "sym.j3")
        connector_asset.update(id="sym.j4", library_id="Connector_Generic:Conn_01x04")
        exemplar["assets"].sort(key=lambda item: item["id"])
        connector = next(c for c in exemplar["logical"]["components"] if c["id"] == "j.io")
        connector["terminals"].append(
            {
                "id": "p4",
                "number": "4",
                "name": "NC",
                "electrical_type": "passive",
                "role": "intentionally_unused",
                "domain": "dom.input",
            }
        )
        use = next(s for s in exemplar["schematic"]["symbols"] if s["id"] == "s.io")
        use["asset"] = "sym.j4"
        use["pin_map"]["4"] = "p4"
        exemplar["logical"]["no_connects"] = [
            {
                "terminal": {"component": "j.io", "terminal": "p4"},
                "reason": "Reserved connector contact; deliberately left unconnected.",
                "evidence": ["ev.requirement"],
            }
        ]

    def check(actual: object, allowed: object, pointer: str) -> None:
        if type(actual) is not type(allowed):
            raise InputError(f"{pointer}: wrong type")
        if isinstance(allowed, dict):
            extra = actual.keys() ^ allowed.keys()
            if extra:
                raise InputError(f"{pointer}: unsupported/absent fields {sorted(extra)}")
            for key in allowed:
                check(actual[key], allowed[key], f"{pointer}/{key}")
        elif isinstance(allowed, list):
            if len(actual) != len(allowed):
                raise InputError(f"{pointer}: unsupported item count")
            for index, (item, expected) in enumerate(zip(actual, allowed, strict=True)):
                check(item, expected, f"{pointer}/{index}")
        elif pointer == "/logical/no_connects/0/reason":
            if not isinstance(actual, str) or not actual.strip() or len(actual) > 200:
                raise InputError("intentional NC requires a concise nonempty reason")
        elif actual != allowed:
            raise InputError(f"{pointer}: unsupported M1 value {actual!r}")

    check(data, exemplar, "")
    terminals = {
        (component["id"], terminal["id"])
        for component in data["logical"]["components"]
        for terminal in component["terminals"]
    }
    if set(members + nc) != terminals:
        raise InputError("terminal inventory does not match nets and intentional NCs")
    return data
