import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from ai_kicad.ir import InputError
from ai_kicad.m2b import assets
from ai_kicad.pivot.model import DesignModel, from_legacy_ir


ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"


def load(name):
    return json.loads((FIXTURE / name).read_text())


def canonical():
    return from_legacy_ir(
        load("design.json"),
        assets(),
        load("bom.json"),
        load("footprint_assets.lock.json"),
        load("board_profile.json"),
    )


def test_legacy_round_trip_is_lossless_for_reference_topology():
    model = canonical()
    round_trip = DesignModel.model_validate_json(model.model_dump_json())
    round_trip.require_revision_match()
    legacy = load("design.json")
    actual = {
        net.net_id: {(terminal.component_id, terminal.pin) for terminal in net.terminals}
        for net in model.nets
    }
    assert actual == {
        net["id"]: {tuple(member) for member in net["members"]} for net in legacy["nets"]
    }
    assert {component.reference for component in model.components} == {
        component["refdes"] for component in legacy["components"]
    }


def test_checked_canonical_fixture_model_matches_pinned_legacy_inputs():
    generated = DesignModel.model_validate_json((FIXTURE / "design-model.v1.json").read_text())
    generated.require_revision_match()
    assert generated == canonical()


@pytest.mark.parametrize("field", ["component_id", "reference"])
def test_duplicate_component_identity_is_rejected(field):
    payload = canonical().model_dump(mode="json")
    payload["components"][1][field] = payload["components"][0][field]
    with pytest.raises(ValidationError, match="duplicate"):
        DesignModel.model_validate(payload)


def test_missing_terminal_component_and_duplicate_terminal_are_rejected():
    payload = canonical().model_dump(mode="json")
    payload["nets"][0]["terminals"][0]["component_id"] = "absent"
    with pytest.raises(ValidationError, match="unknown component"):
        DesignModel.model_validate(payload)


def test_duplicate_physical_pad_assignment_is_rejected():
    payload = canonical().model_dump(mode="json")
    mapping = payload["components"][0]["pin_pad_map"]
    mapping[1]["pad"] = mapping[0]["pad"]
    with pytest.raises(ValidationError, match="duplicate or unknown pin/pad"):
        DesignModel.model_validate(payload)
    payload = canonical().model_dump(mode="json")
    payload["nets"][1]["terminals"][0] = copy.deepcopy(payload["nets"][0]["terminals"][0])
    with pytest.raises(ValidationError, match="more than once"):
        DesignModel.model_validate(payload)


def test_multi_unit_legacy_asset_is_explicitly_rejected():
    resolved = assets()
    legacy = load("design.json")
    legacy["components"][0]["asset"] = "Amplifier_Operational:NE5532"
    with pytest.raises(InputError, match="multi-unit"):
        from_legacy_ir(
            legacy,
            resolved,
            load("bom.json"),
            load("footprint_assets.lock.json"),
            load("board_profile.json"),
        )
