import json
import hashlib
from pathlib import Path

import pytest

from ai_kicad.pivot.revisions import ConcurrentEdit, RevisionStore, StaleRevision
from ai_kicad.pivot.cli import _model_from_fixture


ROOT = Path(__file__).resolve().parents[2]


def canonical():
    return _model_from_fixture(ROOT / "fixtures/pivot/reference_555_led_flasher_v1")


def changed_model(model, title):
    payload = model.model_dump(mode="json")
    payload["title"] = title
    payload["parent_revision"] = model.revision_id
    payload["revision_id"] = "sha256:" + "0" * 64
    provisional = type(model).model_validate(payload)
    payload["revision_id"] = provisional.content_revision()
    return type(model).model_validate(payload)


def model_with_files(model, title, files):
    payload = model.model_dump(mode="json")
    payload["title"] = title
    payload["parent_revision"] = model.revision_id
    payload["native_artifacts"] = {
        name: hashlib.sha256(content).hexdigest() for name, content in files.items()
    }
    payload["revision_id"] = "sha256:" + "0" * 64
    provisional = type(model).model_validate(payload)
    payload["revision_id"] = provisional.content_revision()
    return type(model).model_validate(payload)


def test_commit_cas_idempotency_rollback_and_immutable_prior_revision(tmp_path):
    store = RevisionStore(tmp_path / "store")
    first_files = {"native/a.txt": b"one"}
    first = model_with_files(canonical(), "revision one", first_files)
    with store.writer("one"):
        revision1 = store.commit(first, first_files, expected_revision=None, idempotency_key="a")
    second_files = {"native/a.txt": b"two"}
    second = model_with_files(first, "revision two", second_files)
    with store.writer("two"):
        revision2 = store.commit(
            second, second_files, expected_revision=revision1, idempotency_key="b"
        )
    assert (
        store.commit(second, second_files, expected_revision=revision1, idempotency_key="b")
        == revision2
    )
    assert (store.revision_path(revision1) / "native/a.txt").read_bytes() == b"one"
    with pytest.raises(StaleRevision):
        store.rollback(revision1, expected_revision="sha256:" + "1" * 64)
    assert store.rollback(revision1, expected_revision=revision2) == revision1
    assert store.verify(revision1)


def test_pointer_crash_window_reconciles_only_same_idempotent_request(tmp_path):
    root = tmp_path / "store"
    store = RevisionStore(root)
    first = canonical()
    revision1 = store.commit(first, {}, expected_revision=None, idempotency_key="first")
    second = changed_model(first, "second")
    with pytest.raises(OSError, match="after pointer promotion"):
        store.commit(
            second,
            {},
            expected_revision=revision1,
            idempotency_key="write-2",
            fault="after_pointer_before_idempotency",
        )
    restarted = RevisionStore(root)
    assert restarted.current_revision() == second.revision_id
    assert (
        restarted.commit(
            second,
            {},
            expected_revision=revision1,
            idempotency_key="write-2",
        )
        == second.revision_id
    )
    with pytest.raises(Exception, match="different candidate"):
        restarted.commit(
            changed_model(first, "different"),
            {},
            expected_revision=revision1,
            idempotency_key="write-2",
        )


def test_faults_preserve_last_pointer_and_restart_recovers(tmp_path):
    root = tmp_path / "store"
    store = RevisionStore(root)
    first = canonical()
    revision1 = store.commit(first, {}, expected_revision=None, idempotency_key="first")
    second = changed_model(first, "second")
    with pytest.raises(OSError, match="before promotion"):
        store.commit(
            second,
            {},
            expected_revision=revision1,
            idempotency_key="fault",
            fault="before_promotion",
        )
    assert RevisionStore(root).current_revision() == revision1
    with pytest.raises(OSError, match="after immutable"):
        store.commit(
            second,
            {},
            expected_revision=revision1,
            idempotency_key="fault2",
            fault="after_revision_before_pointer",
        )
    restarted = RevisionStore(root)
    assert restarted.current_revision() == revision1
    assert (
        restarted.commit(second, {}, expected_revision=revision1, idempotency_key="retry")
        == second.revision_id
    )


def test_stale_path_traversal_concurrent_lease_and_tamper(tmp_path):
    store = RevisionStore(tmp_path / "store")
    model = canonical()
    with pytest.raises(StaleRevision):
        store.commit(model, {}, expected_revision="sha256:" + "1" * 64, idempotency_key="x")
    with pytest.raises(Exception, match="escapes"):
        store.commit(model, {"../escape": b"x"}, expected_revision=None, idempotency_key="x")
    with store.writer("first"):
        with pytest.raises(ConcurrentEdit):
            with store.writer("second"):
                pass
    revision = store.commit(model, {}, expected_revision=None, idempotency_key="ok")
    path = store.revision_path(revision) / "design.json"
    data = json.loads(path.read_text())
    data["title"] = "tampered"
    path.write_text(json.dumps(data))
    assert not store.verify(revision)
