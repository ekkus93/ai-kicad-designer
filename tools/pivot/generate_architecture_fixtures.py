"""Generate canonical pivot schemas and the locked reference model."""

from __future__ import annotations

import json
from pathlib import Path

from ai_kicad.pivot.backend import BackendManifest
from ai_kicad.pivot.cli import _model_from_fixture
from ai_kicad.pivot.model import DesignModel


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def main() -> None:
    root = Path(__file__).resolve().parents[2]
    schema_dir = root / "fixtures/pivot/schemas"
    fixture = root / "fixtures/pivot/reference_555_led_flasher_v1"
    write_json(schema_dir / "design-model.v1.schema.json", DesignModel.model_json_schema())
    write_json(schema_dir / "backend-manifest.v1.schema.json", BackendManifest.model_json_schema())
    model = _model_from_fixture(fixture)
    model.require_revision_match()
    write_json(fixture / "design-model.v1.json", model.model_dump(mode="json"))
    print(model.revision_id)


if __name__ == "__main__":
    main()
