"""Author the corrected V3-8-equivalent development fixture deterministically."""

import copy
import json

from ai_kicad.m2a import ROOT


def main() -> None:
    historical_path = ROOT / "fixtures/m2blind_v3/ir/V3-8.json"
    output_path = ROOT / "fixtures/m2e1a/ir/regulator_timer_led_corrected.json"
    historical = json.loads(historical_path.read_text())
    corrected = copy.deepcopy(historical)
    assertion = next(item for item in corrected["power_assertions"] if item["id"] == "flag.supply")
    stage = next(item for item in corrected["relationships"] if item["kind"] == "power_stage")
    if assertion["net"] != stage["output"]:
        raise RuntimeError("historical V3-8 no longer has the recorded output-rail assertion")
    assertion["net"] = stage["input"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(corrected, indent=2) + "\n")


if __name__ == "__main__":
    main()
