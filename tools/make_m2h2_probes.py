"""Freeze the four M2h2 development circuits before layout tuning.

This script writes only fixtures/m2h2/development. It never executes a layout.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "fixtures/m2h2/development"


def component(cid: str, ref: str, asset: str, value: str, **extra: object) -> dict:
    return {"id": cid, "refdes": ref, "asset": asset, "value": value, **extra}


class Circuit:
    def __init__(self, case: str, title: str):
        self.data = {
            "profile": "m2b.1",
            "id": case,
            "name": title,
            "components": [],
            "nets": [],
            "relationships": [],
            "no_connects": [],
            "power_assertions": [],
        }
        self.members: dict[str, list[list[str]]] = {}
        self.paths: list[dict] = []

    def part(self, cid: str, ref: str, asset: str, value: str, **extra: object) -> None:
        self.data["components"].append(component(cid, ref, asset, value, **extra))

    def net(self, name: str, *pins: tuple[str, str]) -> None:
        assert name not in self.members
        self.members[name] = [list(pin) for pin in pins]

    def add(self, net: str, *pins: tuple[str, str]) -> None:
        self.members[net].extend([list(pin) for pin in pins])

    def relation(self, rid: str, kind: str, **fields: object) -> None:
        self.data["relationships"].append({"id": rid, "kind": kind, **fields})

    def assertion(self, net: str, ordinal: int) -> None:
        self.data["power_assertions"].append(
            {"id": f"flag.{ordinal}", "refdes": f"#FLG{ordinal:02d}", "net": net}
        )

    def path(
        self,
        pid: str,
        start: tuple[str, str],
        end: tuple[str, str],
        *,
        kind: str,
        maximum_span_nm: int | None = None,
    ) -> None:
        self.paths.append(
            {
                "id": pid,
                "from": list(start),
                "to": list(end),
                "kind": kind,
                "maximum_span_nm": maximum_span_nm,
            }
        )

    def finish(self) -> tuple[dict, list[dict]]:
        self.data["nets"] = [
            {"id": name, "members": members} for name, members in self.members.items()
        ]
        validate(self.data, assets())
        return self.data, self.paths


def rc(
    c: Circuit,
    stem: str,
    ref_r: str,
    ref_c: str,
    input_net: str,
    output_net: str,
    return_net: str,
    *,
    value: str = "1k",
) -> None:
    c.part(f"{stem}_r", ref_r, "Device:R", value)
    c.part(f"{stem}_c", ref_c, "Device:C", "100n")
    c.add(input_net, (f"{stem}_r", "1"))
    c.net(output_net, (f"{stem}_r", "2"), (f"{stem}_c", "1"))
    c.add(return_net, (f"{stem}_c", "2"))
    c.relation(
        f"{stem}.series", "series", component=f"{stem}_r", input=input_net, output=output_net
    )
    c.relation(
        f"{stem}.shunt", "shunt", component=f"{stem}_c", node=output_net, reference=return_net
    )
    c.path(
        f"{stem}.shunt_path",
        (f"{stem}_r", "2"),
        (f"{stem}_c", "1"),
        kind="local_rc",
        maximum_span_nm=80_000_000,
    )


def timer(
    c: Circuit,
    stem: str,
    unit_ref: str,
    first_resistor: int,
    first_capacitor: int,
    supply: str,
    ret: str,
    output: str,
) -> None:
    c.part(stem, unit_ref, "Timer:NE555D", "NE555D")
    for suffix, ref, asset, value in (
        ("charge", f"R{first_resistor}", "Device:R", "10k"),
        ("discharge", f"R{first_resistor + 1}", "Device:R", "47k"),
        ("timing_cap", f"C{first_capacitor}", "Device:C", "10u"),
        ("control_bypass", f"C{first_capacitor + 1}", "Device:C", "10n"),
    ):
        c.part(f"{stem}_{suffix}", ref, asset, value)
    disch, timing, control = (
        f"{stem.upper()}_DISCH",
        f"{stem.upper()}_TIMING",
        f"{stem.upper()}_CONT",
    )
    c.add(supply, (stem, "8"), (stem, "4"), (f"{stem}_charge", "1"))
    c.add(ret, (stem, "1"), (f"{stem}_timing_cap", "2"), (f"{stem}_control_bypass", "2"))
    c.net(disch, (stem, "7"), (f"{stem}_charge", "2"), (f"{stem}_discharge", "1"))
    c.net(timing, (stem, "2"), (stem, "6"), (f"{stem}_discharge", "2"), (f"{stem}_timing_cap", "1"))
    c.net(control, (stem, "5"), (f"{stem}_control_bypass", "1"))
    c.net(output, (stem, "3"))
    c.relation(
        f"{stem}.function",
        "timer",
        component=stem,
        supply=supply,
        reference=ret,
        output=output,
        timing=timing,
        discharge=disch,
        control=control,
        pins={
            "supply": "8",
            "reference": "1",
            "output": "3",
            "trigger": "2",
            "threshold": "6",
            "discharge": "7",
            "control": "5",
            "reset": "4",
        },
    )
    c.relation(
        f"{stem}.ladder",
        "timing_ladder",
        upper=f"{stem}_charge",
        lower=f"{stem}_discharge",
        capacitor=f"{stem}_timing_cap",
        supply=supply,
        discharge=disch,
        timing=timing,
        reference=ret,
    )
    c.relation(
        f"{stem}.control",
        "decoupling",
        component=f"{stem}_control_bypass",
        consumer=[stem, "5"],
        supply=control,
        **{"return": ret},
    )
    c.path(
        f"{stem}.timing_path",
        (stem, "7"),
        (stem, "2"),
        kind="timing_local",
        maximum_span_nm=80_000_000,
    )
    c.path(
        f"{stem}.control_path",
        (stem, "5"),
        (f"{stem}_control_bypass", "1"),
        kind="support",
        maximum_span_nm=60_000_000,
    )


def dp1() -> tuple[dict, list[dict]]:
    c = Circuit("m2h2_dp1_passive_three_way", "M2h2Dp1PassiveThreeWay")
    for cid, ref, value in (
        ("input", "J1", "Signal input"),
        ("return", "J2", "Common return"),
        ("out_a", "J3", "Branch A output"),
        ("out_b", "J4", "Branch B output"),
        ("out_c", "J5", "Branch C output"),
    ):
        c.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    c.net("INPUT", ("input", "1"))
    c.net("REF", ("return", "1"))
    rc(c, "root", "R1", "C1", "INPUT", "FORK", "REF")
    for stem, ref_r, ref_c, net, port in (
        ("a", "R2", "C2", "A", "out_a"),
        ("b", "R3", "C3", "B", "out_b"),
        ("d", "R4", "C4", "D", "out_c"),
    ):
        rc(c, stem, ref_r, ref_c, "FORK", net, "REF")
        c.add(net, (port, "1"))
        c.path(
            f"fork.{stem}",
            ("root_r", "2"),
            (f"{stem}_r", "1"),
            kind="precedence_cross_fragment",
            maximum_span_nm=80_000_000,
        )
    c.part("load_r", "R5", "Device:R", "1k")
    c.part("load_led", "D1", "Device:LED", "LED")
    c.add("A", ("load_r", "1"))
    c.net("LED_NODE", ("load_r", "2"), ("load_led", "2"))
    c.add("REF", ("load_led", "1"))
    c.relation("load.series", "series", component="load_r", input="A", output="LED_NODE")
    c.relation("load.polarity", "polarity", component="load_led", anode="LED_NODE", cathode="REF")
    c.path(
        "a.to_load",
        ("a_r", "2"),
        ("load_r", "1"),
        kind="precedence_cross_fragment",
        maximum_span_nm=80_000_000,
    )
    c.assertion("REF", 1)
    return c.finish()


def amplifier(
    c: Circuit,
    stem: str,
    ref: str,
    *,
    active: str,
    input_net: str,
    output_net: str,
    positive: str,
    negative: str,
    reference: str,
    capacitor_first: int,
) -> None:
    functions = [
        {
            "id": "a",
            "role": "buffer" if active == "buffer" else "amplifier",
            "unit": 1,
            "pins": {"out": "1", "minus": "2", "plus": "3"},
        },
        {
            "id": "b",
            "role": "parked_buffer",
            "unit": 2,
            "pins": {"out": "7", "minus": "6", "plus": "5"},
        },
        {"id": "power", "role": "supply", "unit": 3, "pins": {"negative": "4", "positive": "8"}},
    ]
    c.part(stem, ref, "Amplifier_Operational:NE5532", "NE5532", functions=functions)
    c.part(f"{stem}_cpos", f"C{capacitor_first}", "Device:C", "100n")
    c.part(f"{stem}_cneg", f"C{capacitor_first + 1}", "Device:C", "100n")
    c.add(positive, (stem, "8"), (f"{stem}_cpos", "1"))
    c.add(negative, (stem, "4"), (f"{stem}_cneg", "2"))
    c.add(reference, (stem, "5"), (f"{stem}_cpos", "2"), (f"{stem}_cneg", "1"))
    c.net(f"{stem.upper()}_PARK", (stem, "7"), (stem, "6"))
    c.add(output_net, (stem, "1"), (stem, "2") if active == "buffer" else (f"{stem}_feedback", "2"))
    if active == "buffer":
        c.add(input_net, (stem, "3"))
    else:
        c.part(f"{stem}_input", "R5", "Device:R", "10k")
        c.part(f"{stem}_feedback", "R6", "Device:R", "47k")
        c.add(input_net, (f"{stem}_input", "1"))
        c.net(f"{stem.upper()}_SUM", (f"{stem}_input", "2"), (stem, "2"), (f"{stem}_feedback", "1"))
        c.add(reference, (stem, "3"))
        c.relation(
            f"{stem}.input",
            "series",
            component=f"{stem}_input",
            input=input_net,
            output=f"{stem.upper()}_SUM",
        )
        c.relation(
            f"{stem}.loop",
            "feedback",
            component=stem,
            function="a",
            source="1",
            sense="2",
            net=output_net,
            polarity="negative",
            resistor=f"{stem}_feedback",
        )
        c.path(
            f"{stem}.feedback",
            (stem, "1"),
            (stem, "2"),
            kind="feedback",
            maximum_span_nm=45_000_000,
        )
    if active == "buffer":
        c.relation(
            f"{stem}.loop",
            "feedback",
            component=stem,
            function="a",
            source="1",
            sense="2",
            net=output_net,
            polarity="negative",
        )
    c.relation(
        f"{stem}.stage",
        "amplifier",
        component=stem,
        function="a",
        input=input_net,
        output=output_net,
        reference=reference,
    )
    c.relation(
        f"{stem}.park",
        "amplifier",
        component=stem,
        function="b",
        input=reference,
        output=f"{stem.upper()}_PARK",
        unused=True,
    )
    c.relation(
        f"{stem}.park_loop",
        "feedback",
        component=stem,
        function="b",
        source="7",
        sense="6",
        net=f"{stem.upper()}_PARK",
        polarity="negative",
    )
    c.relation(
        f"{stem}.rails",
        "power_rails",
        component=stem,
        unit=3,
        positive=positive,
        negative=negative,
        reference=reference,
    )
    for suffix, pin, supply, ret in (
        ("cpos", "8", positive, reference),
        ("cneg", "4", reference, negative),
    ):
        c.relation(
            f"{stem}.{suffix}",
            "decoupling",
            component=f"{stem}_{suffix}",
            consumer=[stem, pin],
            supply=supply,
            **{"return": ret},
        )
        c.path(
            f"{stem}.{suffix}.support",
            (stem, pin),
            (f"{stem}_{suffix}", "1" if suffix == "cpos" else "2"),
            kind="support",
            maximum_span_nm=60_000_000,
        )
    c.path(
        f"{stem}.park_reference",
        (stem, "5"),
        (f"{stem}_cpos", "2"),
        kind="reference_distribution",
        maximum_span_nm=None,
    )


def dp2() -> tuple[dict, list[dict]]:
    c = Circuit("m2h2_dp2_dual_package_internal_reference", "M2h2Dp2DualPackageReference")
    for cid, ref, value in (
        ("positive", "J1", "Positive rail"),
        ("negative", "J2", "Negative rail"),
        ("input_a", "J3", "Buffer input"),
        ("output_a", "J4", "Buffer output"),
        ("input_b", "J5", "Gain input"),
        ("output_b", "J6", "Gain output"),
    ):
        c.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    c.part("divider_upper", "R1", "Device:R", "10k")
    c.part("divider_lower", "R2", "Device:R", "10k")
    c.net("VPLUS", ("positive", "1"), ("divider_upper", "1"))
    c.net("VMINUS", ("negative", "1"), ("divider_lower", "2"))
    c.net("VREF", ("divider_upper", "2"), ("divider_lower", "1"))
    c.net("IN_A", ("input_a", "1"))
    c.net("OUT_A", ("output_a", "1"))
    c.net("IN_B", ("input_b", "1"))
    c.net("OUT_B", ("output_b", "1"))
    c.relation(
        "divider",
        "reference_divider",
        upper="divider_upper",
        lower="divider_lower",
        positive="VPLUS",
        local="VREF",
        negative="VMINUS",
    )
    amplifier(
        c,
        "amp_a",
        "U1",
        active="buffer",
        input_net="IN_A",
        output_net="OUT_A",
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
        capacitor_first=1,
    )
    amplifier(
        c,
        "amp_b",
        "U2",
        active="inverting",
        input_net="IN_B",
        output_net="OUT_B",
        positive="VPLUS",
        negative="VMINUS",
        reference="VREF",
        capacitor_first=3,
    )
    c.path(
        "reference.to_parked_a",
        ("divider_upper", "2"),
        ("amp_a", "5"),
        kind="reference_distribution",
    )
    c.path(
        "reference.to_parked_b",
        ("divider_upper", "2"),
        ("amp_b", "5"),
        kind="reference_distribution",
    )
    c.assertion("VPLUS", 1)
    c.assertion("VMINUS", 2)
    return c.finish()


def dp3() -> tuple[dict, list[dict]]:
    c = Circuit("m2h2_dp3_dual_timer_rc", "M2h2Dp3DualTimerRc")
    for cid, ref, value in (
        ("source", "J1", "Shared supply"),
        ("return", "J2", "Common return"),
        ("out_a", "J3", "Timer A filtered"),
        ("out_b", "J4", "Timer B filtered"),
    ):
        c.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    c.net("VCC", ("source", "1"))
    c.net("REF", ("return", "1"))
    timer(c, "timer_a", "U1", 1, 1, "VCC", "REF", "A_RAW")
    timer(c, "timer_b", "U2", 3, 3, "VCC", "REF", "B_RAW")
    rc(c, "filter_a", "R5", "C5", "A_RAW", "A_OUT", "REF")
    rc(c, "filter_b", "R6", "C6", "B_RAW", "B_OUT", "REF")
    c.add("A_OUT", ("out_a", "1"))
    c.add("B_OUT", ("out_b", "1"))
    for stem, raw in (("a", "A_RAW"), ("b", "B_RAW")):
        c.path(
            f"timer_{stem}.to_filter",
            (f"timer_{stem}", "3"),
            (f"filter_{stem}_r", "1"),
            kind="precedence_cross_fragment",
            maximum_span_nm=80_000_000,
        )
    c.assertion("VCC", 1)
    c.assertion("REF", 2)
    return c.finish()


def dp4() -> tuple[dict, list[dict]]:
    c = Circuit("m2h2_dp4_regulated_dual_timer_branches", "M2h2Dp4RegulatedDualTimer")
    for cid, ref, value in (
        ("source", "J1", "Unregulated supply"),
        ("return", "J2", "Common return"),
        ("out_a", "J3", "Filtered branch A"),
        ("out_b", "J4", "Filtered branch B"),
    ):
        c.part(cid, ref, "Connector_Generic:Conn_01x01", value)
    c.net("VIN", ("source", "1"))
    c.net("REF", ("return", "1"))
    c.part("regulator", "U1", "Regulator_Linear:L7805", "L7805")
    c.part("reg_in_c", "C1", "Device:C", "330n")
    c.part("reg_out_c", "C2", "Device:C", "100n")
    c.add("VIN", ("regulator", "1"), ("reg_in_c", "1"))
    c.add("REF", ("regulator", "2"), ("reg_in_c", "2"), ("reg_out_c", "2"))
    c.net("VCC", ("regulator", "3"), ("reg_out_c", "1"))
    c.relation(
        "reg.stage",
        "power_stage",
        component="regulator",
        input="VIN",
        output="VCC",
        reference="REF",
        pins={"input": "1", "output": "3", "reference": "2"},
        polarity="positive",
    )
    for suffix, cap, pin, supply in (
        ("input", "reg_in_c", "1", "VIN"),
        ("output", "reg_out_c", "3", "VCC"),
    ):
        c.relation(
            f"reg.{suffix}_support",
            "decoupling",
            component=cap,
            consumer=["regulator", pin],
            supply=supply,
            **{"return": "REF"},
        )
        c.path(
            f"reg.{suffix}.support",
            ("regulator", pin),
            (cap, "1"),
            kind="support",
            maximum_span_nm=60_000_000,
        )
    timer(c, "timer_a", "U2", 1, 3, "VCC", "REF", "A_RAW")
    timer(c, "timer_b", "U3", 3, 5, "VCC", "REF", "B_RAW")
    rc(c, "filter_a", "R5", "C7", "A_RAW", "A_OUT", "REF")
    rc(c, "filter_b", "R6", "C8", "A_RAW", "B_OUT", "REF")
    c.add("A_OUT", ("out_a", "1"))
    c.add("B_OUT", ("out_b", "1"))
    c.part("led_r", "R7", "Device:R", "1k")
    c.part("led", "D1", "Device:LED", "LED")
    c.add("B_RAW", ("led_r", "1"))
    c.net("LED_NODE", ("led_r", "2"), ("led", "2"))
    c.add("REF", ("led", "1"))
    c.relation("led.series", "series", component="led_r", input="B_RAW", output="LED_NODE")
    c.relation("led.polarity", "polarity", component="led", anode="LED_NODE", cathode="REF")
    for stem in ("filter_a", "filter_b"):
        c.path(
            f"a.to_{stem}",
            ("timer_a", "3"),
            (f"{stem}_r", "1"),
            kind="precedence_cross_fragment",
            maximum_span_nm=80_000_000,
        )
    c.path(
        "b.to_led",
        ("timer_b", "3"),
        ("led_r", "1"),
        kind="precedence_cross_fragment",
        maximum_span_nm=80_000_000,
    )
    c.assertion("VIN", 1)
    c.assertion("REF", 2)
    return c.finish()


def canonical_fingerprint(design: dict) -> tuple:
    """Coarse isomorphism exclusion by typed object counts and degree multisets."""
    assets_by_id = {x["id"]: x["asset"] for x in design["components"]}
    return (
        tuple(sorted(assets_by_id.values())),
        tuple(sorted(x["kind"] for x in design["relationships"])),
        tuple(
            sorted(
                (len(x["members"]), tuple(sorted(assets_by_id[a] for a, _ in x["members"])))
                for x in design["nets"]
            )
        ),
    )


def historical_designs() -> list[tuple[str, dict]]:
    roots = [
        ROOT / "fixtures" / name
        for name in (
            "m2blind_v2",
            "m2blind_v3",
            "m2blind_v4",
            "m2blind_v5",
            "m2blind_v6",
            "m2e1",
            "m2f2",
            "m2g2",
        )
    ]
    found = []
    for root in roots:
        for folder in (root / "ir", root / "probes"):
            if folder.is_dir():
                for file in sorted(folder.glob("*.json")):
                    if file.name.endswith(".expected.json") or file.name == "manifest.json":
                        continue
                    try:
                        data = json.loads(file.read_text())
                    except (ValueError, OSError):
                        continue
                    if (
                        isinstance(data, dict)
                        and {"components", "nets", "relationships"} <= data.keys()
                    ):
                        found.append((str(file.relative_to(ROOT)), data))
    return found


def persist(case_id: str, design: dict, paths: list[dict], ancestry: list[str]) -> dict:
    design_text = json.dumps(design, indent=2) + "\n"
    expectations = {
        "schema_version": "m2h2.development-expectations.1",
        "frozen_before_layout_tuning": True,
        "terminal_inventory": sorted(
            [member for net in design["nets"] for member in net["members"]]
        ),
        "partitions": {net["id"]: sorted(net["members"]) for net in design["nets"]},
        "path_obligations": paths,
        "precedence": [
            {"source": list(a), "target": list(b), "strict_x": True}
            for a, b in (
                (tuple(path["from"]), tuple(path["to"]))
                for path in paths
                if path["kind"] == "precedence_cross_fragment"
            )
        ],
        "ancestry_comparison": ancestry,
    }
    expected_text = json.dumps(expectations, indent=2, sort_keys=True) + "\n"
    (OUT / f"{case_id}.json").write_text(design_text)
    (OUT / f"{case_id}.expected.json").write_text(expected_text)
    return {
        "id": case_id,
        "ir_sha256": hashlib.sha256(design_text.encode()).hexdigest(),
        "expectations_sha256": hashlib.sha256(expected_text.encode()).hexdigest(),
    }


def stress(design: dict, *, connector: str) -> dict:
    result = copy.deepcopy(design)
    result["id"] += "_long_fields"
    result["name"] += "LongFields"
    next(x for x in result["components"] if x["id"] == connector)["value"] = (
        "CONNECTOR_VALUE_24_CHARS"
    )
    assert len("CONNECTOR_VALUE_24_CHARS") == 24
    old = next(net["id"] for net in result["nets"] if [connector, "1"] in net["members"])
    new = "REQUIRED_NET_LABEL20"
    assert len(new) == 20
    next(net for net in result["nets"] if net["id"] == old)["id"] = new
    for relation in result["relationships"]:
        for key, value in list(relation.items()):
            if value == old:
                relation[key] = new
    validate(result, assets())
    return result


def main() -> None:
    if OUT.exists():
        raise SystemExit("development freeze already exists; refusing to rewrite")
    cases = [("dp1", *dp1()), ("dp2", *dp2()), ("dp3", *dp3()), ("dp4", *dp4())]
    historical = historical_designs()
    ancestry = {}
    for case_id, design, _ in cases:
        collisions = [
            name
            for name, old in historical
            if canonical_fingerprint(old) == canonical_fingerprint(design)
        ]
        if collisions:
            raise ValueError(f"topology fingerprint collision {case_id}: {collisions}")
        ancestry[case_id] = [
            f"No typed inventory/degree fingerprint match among {len(historical)} historical IRs"
        ]
    OUT.mkdir(parents=True)
    entries = [
        persist(case_id, design, paths, ancestry[case_id]) for case_id, design, paths in cases
    ]
    for case_id, design, paths in cases:
        if case_id in {"dp1", "dp3"}:
            derivative = stress(design, connector="out_c" if case_id == "dp1" else "out_b")
            entries.append(
                persist(
                    case_id + "_long_fields",
                    derivative,
                    paths,
                    ["Field-width derivative of frozen " + case_id],
                )
            )
    manifest = {
        "schema_version": "m2h2.development-manifest.1",
        "frozen_before_layout_tuning": True,
        "historical_comparison_count": len(historical),
        "cases": entries,
    }
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
