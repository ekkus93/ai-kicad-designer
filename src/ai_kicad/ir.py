"""Strict M1a profile: the reviewed section 7 divider and no future features."""

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


def validate(raw: dict, reference: dict) -> dict:
    """Enforce the exact reviewed M1a electrical/capability profile.

    The fixture is a *validation specification*, never an observation source.
    Only the comparator may subsequently use the validated expected nets.
    """

    def check(actual: object, allowed: object, pointer: str) -> None:
        if type(actual) is not type(allowed):
            raise InputError(f"{pointer}: wrong type")
        if isinstance(allowed, dict):
            extra = actual.keys() - allowed.keys()
            missing = allowed.keys() - actual.keys()
            if extra or missing:
                raise InputError(f"{pointer}: unsupported/absent fields {sorted(extra | missing)}")
            for key in allowed:
                check(actual[key], allowed[key], f"{pointer}/{key}")
        elif isinstance(allowed, list):
            if len(actual) != len(allowed):
                raise InputError(f"{pointer}: unsupported item count")
            for index, (item, expected) in enumerate(zip(actual, allowed, strict=True)):
                check(item, expected, f"{pointer}/{index}")
        elif actual != allowed:
            raise InputError(f"{pointer}: unsupported M1a value {actual!r}")

    # Give the electrical ambiguity its own diagnostic even when a list grows.
    try:
        initial_members = [
            (member["component"], member["terminal"])
            for net in raw["logical"]["nets"]
            for member in net["members"]
        ]
    except (KeyError, TypeError):
        initial_members = []
    if len(initial_members) != len(set(initial_members)):
        raise InputError("duplicate terminal membership")
    check(raw, reference, "")
    members = [
        (member["component"], member["terminal"])
        for net in raw["logical"]["nets"]
        for member in net["members"]
    ]
    if len(members) != len(set(members)):
        raise InputError("duplicate terminal membership")
    terminals = {
        (component["id"], terminal["id"])
        for component in raw["logical"]["components"]
        for terminal in component["terminals"]
    }
    if set(members) != terminals:
        raise InputError("terminal inventory does not match net membership")
    return raw
