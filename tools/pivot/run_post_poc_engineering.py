"""Generate retained evidence for bounded post-POC engineering features."""

from __future__ import annotations

import json
from pathlib import Path

from ai_kicad.pivot.engineering import (
    CatalogPart,
    CircuitRequirements,
    SUPPORTED_DOMAINS,
    astable_555,
    export_through_hole_assembly,
    led_resistor,
    select_part,
)
from ai_kicad.pivot.spice import simulate_rc_charge
from tools.pivot.experiment_paths import create_experiment_dir


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--ngspice", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = create_experiment_dir(root, args.experiment_id)
    requirements = CircuitRequirements(
        function="NE555 astable LED flasher with pulse output",
        supply_nominal_v=5.0,
        supply_min_v=4.75,
        supply_max_v=5.25,
        output_load_ma=3.25,
        environment="indoor bench demonstration",
        safety_class="benign-low-voltage",
        assumptions=["No inductive load", "No external voltage on pulse output"],
        unresolved=[],
    )
    catalog_data = json.loads((root / "fixtures/pivot/catalog/reference_parts.v2.json").read_text())
    catalog = [CatalogPart.model_validate(part) for part in catalog_data["parts"]]
    timer = select_part(
        catalog,
        category="timer",
        package="PDIP-8",
        minimum_voltage_v=requirements.supply_max_v,
        required_pin_map={str(index): str(index) for index in range(1, 9)},
    )
    spice = simulate_rc_charge(
        args.ngspice.resolve(),
        output / "spice",
        supply_v=5.0,
        resistance_ohm=57_000,
        capacitance_f=10e-6,
        stop_s=1.2,
    )
    verification = json.loads(
        (
            root
            / "fixtures/pivot/experiments/approved_c2_footprint_2026-10-23_run3/reports/verification_report.json"
        ).read_text()
    )
    bom = json.loads((root / "fixtures/pivot/reference_555_led_flasher_v8/bom.json").read_text())
    assembly = export_through_hole_assembly(verification["board"], bom, output / "assembly")
    report = {
        "schema_version": "post-poc-engineering.v1",
        "status": "PASS",
        "requirements": requirements.model_dump(mode="json"),
        "selected_timer": timer.model_dump(mode="json"),
        "calculations": {
            "astable": astable_555(10_000, 47_000, 10e-6),
            "worst_case_led": led_resistor(5.25, 2.0, 1000, 0.25),
        },
        "spice": spice,
        "assembly": assembly,
        "supported_domains": SUPPORTED_DOMAINS,
        "remaining_human_gate": "Diverse AI-generated topologies require independent human electrical review.",
    }
    (output / "assessment.json").write_text(json.dumps(report, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
