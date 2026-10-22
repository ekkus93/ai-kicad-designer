"""Immutable, content-addressed design revisions with CAS promotion."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .model import DesignModel


class RevisionError(RuntimeError):
    code = "REVISION_ERROR"


class StaleRevision(RevisionError):
    code = "STALE_REVISION"


class ConcurrentEdit(RevisionError):
    code = "CONCURRENT_EDIT"


class AmbiguousWrite(RevisionError):
    code = "AMBIGUOUS_WRITE"


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RevisionStore:
    """Promote complete staging directories while preserving every prior revision."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.revisions = self.root / "revisions"
        self.staging = self.root / "staging"
        self.current_file = self.root / "CURRENT"
        self.lease_file = self.root / ".writer-lease"
        self.idempotency_file = self.root / "idempotency.json"
        for directory in (self.root, self.revisions, self.staging):
            directory.mkdir(parents=True, exist_ok=True)

    def current_revision(self) -> str | None:
        return self.current_file.read_text().strip() if self.current_file.is_file() else None

    def revision_path(self, revision_id: str) -> Path:
        if not revision_id.startswith("sha256:") or len(revision_id) != 71:
            raise RevisionError("invalid revision identity")
        path = (self.revisions / revision_id.removeprefix("sha256:")).resolve()
        if not path.is_relative_to(self.revisions):
            raise RevisionError("revision path escapes store")
        return path

    @contextmanager
    def writer(self, owner: str) -> Iterator[None]:
        try:
            descriptor = os.open(self.lease_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise ConcurrentEdit("another writer holds the design lease") from exc
        try:
            os.write(descriptor, owner.encode())
            os.close(descriptor)
            yield
        finally:
            self.lease_file.unlink(missing_ok=True)

    def _write_pointer(self, revision_id: str) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix="CURRENT.", dir=self.root, text=True)
        try:
            os.write(descriptor, (revision_id + "\n").encode())
            os.fsync(descriptor)
            os.close(descriptor)
            os.replace(temporary, self.current_file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _read_idempotency(self) -> dict:
        return (
            json.loads(self.idempotency_file.read_text())
            if self.idempotency_file.is_file()
            else {}
        )

    def _write_idempotency(self, data: dict) -> None:
        descriptor, temporary = tempfile.mkstemp(
            prefix="idempotency.", dir=self.root, text=True
        )
        try:
            with os.fdopen(descriptor, "w") as stream:
                stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.idempotency_file)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def commit(
        self,
        model: DesignModel,
        files: dict[str, Path | bytes],
        *,
        expected_revision: str | None,
        idempotency_key: str,
        fault: str | None = None,
    ) -> str:
        model.require_revision_match()
        file_hashes = {}
        for relative, source in files.items():
            relative_path = Path(relative)
            if relative_path.is_absolute() or ".." in relative_path.parts:
                raise RevisionError("artifact path escapes revision")
            if isinstance(source, bytes):
                file_hashes[str(relative_path)] = hashlib.sha256(source).hexdigest()
            else:
                if source.is_symlink() or not source.is_file():
                    raise RevisionError("artifact source must be a regular file")
                file_hashes[str(relative_path)] = _hash(source)
        if model.native_artifacts != file_hashes:
            raise RevisionError("native artifact inventory differs from saved candidate files")
        idempotency = self._read_idempotency()
        previous = idempotency.get(idempotency_key)
        if previous:
            # Read legacy receipts written by the first pivot implementation.
            if isinstance(previous, str):
                if self.revision_path(previous).is_dir():
                    return previous
                raise AmbiguousWrite("idempotency record points to a missing revision")
            same_request = (
                previous.get("revision_id") == model.revision_id
                and previous.get("expected_revision") == expected_revision
                and previous.get("artifacts") == file_hashes
            )
            if not same_request:
                raise AmbiguousWrite("idempotency key was reused for a different candidate")
            if previous.get("status") == "COMMITTED":
                return previous["revision_id"]
            if previous.get("status") != "PREPARED":
                raise AmbiguousWrite("idempotency record has an unknown state")
            recorded_revision = previous["revision_id"]
            recorded_path = self.revision_path(recorded_revision)
            current = self.current_revision()
            if recorded_path.is_dir():
                if not self.verify(recorded_revision):
                    raise AmbiguousWrite("prepared revision failed immutable verification")
                if current == expected_revision:
                    self._write_pointer(recorded_revision)
                elif current != recorded_revision:
                    raise AmbiguousWrite("prepared revision conflicts with current pointer")
                previous["status"] = "COMMITTED"
                self._write_idempotency(idempotency)
                return recorded_revision
            if current != expected_revision:
                raise AmbiguousWrite("prepared write cannot be resumed from current pointer")
        elif self.current_revision() != expected_revision:
            raise StaleRevision("current revision does not match expected_revision")
        revision_id = model.revision_id
        # Persist intent before publishing the immutable directory or pointer. A restart
        # can then resolve the narrow crash windows using the same idempotency key.
        idempotency[idempotency_key] = {
            "status": "PREPARED",
            "revision_id": revision_id,
            "expected_revision": expected_revision,
            "artifacts": file_hashes,
        }
        self._write_idempotency(idempotency)
        final = self.revision_path(revision_id)
        if final.exists():
            manifest = json.loads((final / "manifest.json").read_text())
            if manifest["revision_id"] != revision_id or manifest["artifacts"] != file_hashes:
                raise AmbiguousWrite("existing revision content differs from this candidate")
            self._write_pointer(revision_id)
            idempotency[idempotency_key]["status"] = "COMMITTED"
            self._write_idempotency(idempotency)
            return revision_id
        candidate = Path(tempfile.mkdtemp(prefix="candidate-", dir=self.staging))
        try:
            (candidate / "design.json").write_text(model.model_dump_json(indent=2) + "\n")
            artifacts = {}
            for relative, source in files.items():
                relative_path = Path(relative)
                if relative_path.is_absolute() or ".." in relative_path.parts:
                    raise RevisionError("artifact path escapes revision")
                destination = candidate / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                if isinstance(source, bytes):
                    destination.write_bytes(source)
                else:
                    if source.is_symlink() or not source.is_file():
                        raise RevisionError("artifact source must be a regular file")
                    shutil.copy2(source, destination)
                artifacts[str(relative_path)] = _hash(destination)
            manifest = {
                "revision_id": revision_id,
                "design_sha256": _hash(candidate / "design.json"),
                "artifacts": artifacts,
            }
            (candidate / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            if fault == "before_promotion":
                raise OSError("injected failure before promotion")
            os.replace(candidate, final)
            if fault == "after_revision_before_pointer":
                raise OSError("injected failure after immutable revision write")
            self._write_pointer(revision_id)
            if fault == "after_pointer_before_idempotency":
                raise OSError("injected failure after pointer promotion")
            idempotency[idempotency_key]["status"] = "COMMITTED"
            self._write_idempotency(idempotency)
            return revision_id
        finally:
            if candidate.exists():
                shutil.rmtree(candidate)

    def rollback(self, target_revision: str, *, expected_revision: str) -> str:
        if self.current_revision() != expected_revision:
            raise StaleRevision("rollback expected_revision is stale")
        target = self.revision_path(target_revision)
        if not target.is_dir() or not (target / "manifest.json").is_file():
            raise RevisionError("rollback target is not a valid immutable revision")
        self._write_pointer(target_revision)
        return target_revision

    def verify(self, revision_id: str) -> bool:
        directory = self.revision_path(revision_id)
        if not directory.is_dir():
            return False
        manifest = json.loads((directory / "manifest.json").read_text())
        try:
            model = DesignModel.model_validate_json((directory / "design.json").read_text())
            model.require_revision_match()
        except (OSError, ValueError):
            return False
        try:
            artifacts_valid = all(
                not Path(relative).is_absolute()
                and ".." not in Path(relative).parts
                and (directory / relative).is_file()
                and _hash(directory / relative) == digest
                for relative, digest in manifest["artifacts"].items()
            )
        except (KeyError, TypeError, ValueError):
            return False
        return (
            manifest["revision_id"] == revision_id
            and model.revision_id == revision_id
            and _hash(directory / "design.json") == manifest.get("design_sha256")
            and artifacts_valid
        )
