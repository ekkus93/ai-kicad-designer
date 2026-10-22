"""Cross-check the reference electrical design, BOM, and pinned footprints."""

import hashlib
import json
import re
from pathlib import Path

from ai_kicad.m2b import assets, validate
from ai_kicad.ir import load_json

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "fixtures/pivot/reference_555_led_flasher_v1"


def test_bom_maps_every_component_pin_to_a_real_locked_footprint_pad() -> None:
    design = validate(load_json(FIXTURE / "design.json"), assets())
    bom = json.loads((FIXTURE / "bom.json").read_text())
    footprint_lock = json.loads((FIXTURE / "footprint_assets.lock.json").read_text())
    components = {component["refdes"]: component for component in design["components"]}
    entries = {item["refdes"]: item for item in bom["items"]}
    footprint_entries = {
        f"{item['library']}:{item['footprint']}": item for item in footprint_lock["assets"]
    }

    assert set(entries) == set(components)
    assert all(item["mpn"] != "TBD" and item.get("source") for item in entries.values())
    for refdes, component in components.items():
        item = entries[refdes]
        pins = {pin.number for unit in assets()[component["asset"]].units.values() for pin in unit}
        mapped = set(item["symbol_pin_to_pad"])
        assert mapped == pins
        footprint = footprint_entries[item["footprint"]]
        path = FIXTURE / footprint["path"]
        data = path.read_bytes()
        assert hashlib.sha256(data).hexdigest() == footprint["sha256"]
        pads = set(re.findall(rb"\(pad\s+\"?(\d+)\"?\s", data))
        assert set(item["symbol_pin_to_pad"].values()) <= {pad.decode() for pad in pads}


def test_timing_and_led_bounds_are_reproducible() -> None:
    behavior = json.loads((FIXTURE / "expected_behavior.json").read_text())
    values = behavior["nominal_inputs"]
    ra = values["ra_ohm"]
    rb = values["rb_ohm"]
    cap = values["c_f"]
    high = 0.693 * (ra + rb) * cap
    low = 0.693 * rb * cap
    assert abs(high - behavior["nominal"]["high_s"]) < 1e-9
    assert abs(low - behavior["nominal"]["low_s"]) < 1e-9
    assert abs(1 / (high + low) - behavior["nominal"]["frequency_hz"]) < 1e-6
    led = behavior["indicator"]
    current = led["supply_max_v"] / (led["resistor_ohm"] * (1 - led["resistor_tolerance_fraction"]))
    assert current * 1000 <= led["conservative_current_upper_bound_ma_ignoring_led_drop"]
    assert (
        current**2 * led["resistor_ohm"] * (1 - led["resistor_tolerance_fraction"])
        <= (led["resistor_power_upper_bound_w"])
    )
