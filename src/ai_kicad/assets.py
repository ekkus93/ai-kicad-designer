"""Resolve only the two M1a standard symbol definitions from hashed files."""

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .ir import InputError
from .sexpr import children, one, parse, quote


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Source(Strict):
    uri: str
    revision: str


class Dependency(Strict):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class AssetEntry(Strict):
    id: str
    kind: str
    library_id: str
    path: str
    file_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    dependencies: list[Dependency]
    source: Source
    license: str


class AssetLock(Strict):
    schema_version: str
    assets: list[AssetEntry]


@dataclass(frozen=True)
class Symbol:
    library_id: str
    definition: str
    pins: tuple[tuple[str, int, int], ...]  # number, x_nm, y_nm in library coordinates
    digest: str


def _extract_symbol(source: str, name: str) -> str:
    match = re.search(r"\(symbol\s+" + re.escape(quote(name)) + r"(?=\s|\))", source)
    if match is None:
        raise InputError(f"symbol {name} absent")
    start = match.start()
    depth = 0
    quoted = False
    escape = False
    for position in range(start, len(source)):
        char = source[position]
        if quoted:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[start : position + 1]
    raise InputError(f"unterminated symbol {name}")


def _nm(value: str) -> int:
    from decimal import Decimal

    converted = Decimal(value) * 1_000_000
    if converted != converted.to_integral_value():
        raise InputError(f"off-nanometer symbol coordinate {value}")
    return int(converted)


def resolve(design: dict, lock: AssetLock, lock_dir: Path) -> dict[str, Symbol]:
    if lock.schema_version != "m1.1":
        raise InputError("unsupported asset lock version")
    requests = {item["id"]: item["library_id"] for item in design["assets"]}
    entries = {entry.id: entry for entry in lock.assets}
    if entries.keys() != requests.keys():
        raise InputError("asset lock must contain exactly requested assets")
    result = {}
    for asset_id, library_id in sorted(requests.items()):
        entry = entries[asset_id]
        if entry.kind != "symbol" or entry.library_id != library_id:
            raise InputError(f"asset mismatch: {asset_id}")
        path = (lock_dir / entry.path).resolve()
        if not path.is_relative_to(lock_dir.resolve()):
            raise InputError("asset path traverses lock directory")
        data = path.read_bytes()
        if sha256(data) != entry.file_sha256:
            raise InputError(f"asset hash mismatch: {asset_id}")
        if entry.dependencies:
            raise InputError("M1a symbols must have no inheritance dependencies")
        name = library_id.split(":", 1)[1]
        definition = _extract_symbol(data.decode(), name)
        tree = parse(definition)
        if children(tree, "extends"):
            raise InputError("inherited symbols unsupported in M1a")
        pins = []
        for unit in children(tree, "symbol"):
            for pin in children(unit, "pin"):
                at = one(pin, "at")
                pins.append((str(one(pin, "number")[1]), _nm(at[1]), _nm(at[2])))
        numbers = [pin[0] for pin in pins]
        expected = ["1", "2"] if library_id == "Device:R" else ["1", "2", "3"]
        if sorted(numbers) != expected:
            raise InputError(f"unexpected actual pin inventory for {library_id}: {numbers}")
        result[asset_id] = Symbol(library_id, definition, tuple(pins), sha256(definition.encode()))
    for use in design["schematic"]["symbols"]:
        actual = {number for number, _, _ in result[use["asset"]].pins}
        if set(use["pin_map"]) != actual:
            raise InputError(f"pin map does not match asset: {use['id']}")
    return result
