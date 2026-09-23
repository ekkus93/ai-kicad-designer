"""Author and pre-layout validate the preregistered corpus.v6 IRs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ai_kicad.m2b import assets, validate


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Design:
    def __init__(self, design_id: str, name: str) -> None:
        self.data = {
            "profile": "m2b.1",
            "id": design_id,
            "name": name,
            "components": [],
            "nets": [],
            "no_connects": [],
            "relationships": [],
            "power_assertions": [],
        }
        self._nets: dict[str, list[list[str]]] = {}

    def component(
        self,
        component_id: str,
        refdes: str,
        asset: str,
        value: str,
        functions: list[dict] | None = None,
    ) -> None:
        item: dict = {
            "id": component_id,
            "refdes": refdes,
            "asset": asset,
            "value": value,
        }
        if functions is not None:
            item["functions"] = functions
        self.data["components"].append(item)

    def connect(self, net: str, component_id: str, pin: str) -> None:
        self._nets.setdefault(net, []).append([component_id, pin])

    def relation(self, relation_id: str, kind: str, **fields: object) -> None:
        self.data["relationships"].append({"id": relation_id, "kind": kind, **fields})

    def interface(self, component_id: str, refdes: str, value: str, net: str) -> None:
        self.component(component_id, refdes, "Connector_Generic:Conn_01x01", value)
        self.connect(net, component_id, "1")

    def flag(self, assertion_id: str, refdes: str, net: str) -> None:
        self.data["power_assertions"].append({"id": assertion_id, "refdes": refdes, "net": net})

    def finish(self) -> dict:
        self.data["nets"] = [{"id": net, "members": members} for net, members in self._nets.items()]
        return self.data


def add_regulator(
    d: Design,
    prefix: str,
    refdes: str,
    input_net: str,
    output_net: str,
    reference: str,
    cap_number: int,
) -> None:
    d.component(prefix, refdes, "Regulator_Linear:L7805", "L7805")
    d.component(f"{prefix}_input_c", f"C{cap_number}", "Device:C", "330n")
    d.component(f"{prefix}_output_c", f"C{cap_number + 1}", "Device:C", "100n")
    d.connect(input_net, prefix, "1")
    d.connect(reference, prefix, "2")
    d.connect(output_net, prefix, "3")
    d.connect(input_net, f"{prefix}_input_c", "1")
    d.connect(reference, f"{prefix}_input_c", "2")
    d.connect(output_net, f"{prefix}_output_c", "1")
    d.connect(reference, f"{prefix}_output_c", "2")
    d.relation(
        f"{prefix}.conversion",
        "power_stage",
        component=prefix,
        input=input_net,
        output=output_net,
        reference=reference,
        pins={"input": "1", "output": "3", "reference": "2"},
        polarity="positive",
    )
    d.relation(
        f"{prefix}.bypass.input",
        "decoupling",
        component=f"{prefix}_input_c",
        consumer=[prefix, "1"],
        supply=input_net,
        **{"return": reference},
    )
    d.relation(
        f"{prefix}.bypass.output",
        "decoupling",
        component=f"{prefix}_output_c",
        consumer=[prefix, "3"],
        supply=output_net,
        **{"return": reference},
    )


def add_timer(
    d: Design,
    prefix: str,
    refdes: str,
    supply: str,
    reference: str,
    output: str,
    resistor_number: int,
    capacitor_number: int,
) -> None:
    charge = f"{prefix}_charge"
    discharge_r = f"{prefix}_discharge"
    timing_c = f"{prefix}_timing_cap"
    control_c = f"{prefix}_control_bypass"
    disch = f"{prefix.upper()}_DISCH"
    timing = f"{prefix.upper()}_TIMING"
    control = f"{prefix.upper()}_CONT"
    d.component(prefix, refdes, "Timer:NE555D", "NE555D")
    d.component(charge, f"R{resistor_number}", "Device:R", "10k")
    d.component(discharge_r, f"R{resistor_number + 1}", "Device:R", "47k")
    d.component(timing_c, f"C{capacitor_number}", "Device:C", "10u")
    d.component(control_c, f"C{capacitor_number + 1}", "Device:C", "10n")
    for pin in ("8", "4"):
        d.connect(supply, prefix, pin)
    d.connect(reference, prefix, "1")
    d.connect(output, prefix, "3")
    d.connect(disch, prefix, "7")
    for pin in ("2", "6"):
        d.connect(timing, prefix, pin)
    d.connect(control, prefix, "5")
    d.connect(supply, charge, "1")
    d.connect(disch, charge, "2")
    d.connect(disch, discharge_r, "1")
    d.connect(timing, discharge_r, "2")
    d.connect(timing, timing_c, "1")
    d.connect(reference, timing_c, "2")
    d.connect(control, control_c, "1")
    d.connect(reference, control_c, "2")
    d.relation(
        f"{prefix}.function",
        "timer",
        component=prefix,
        supply=supply,
        reference=reference,
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
    d.relation(
        f"{prefix}.timing",
        "timing_ladder",
        upper=charge,
        lower=discharge_r,
        capacitor=timing_c,
        supply=supply,
        discharge=disch,
        timing=timing,
        reference=reference,
    )
    d.relation(
        f"{prefix}.control",
        "decoupling",
        component=control_c,
        consumer=[prefix, "5"],
        supply=control,
        **{"return": reference},
    )


def opamp_functions(role_a: str, role_b: str) -> list[dict]:
    return [
        {"id": "a", "role": role_a, "unit": 1, "pins": {"out": "1", "minus": "2", "plus": "3"}},
        {"id": "b", "role": role_b, "unit": 2, "pins": {"out": "7", "minus": "6", "plus": "5"}},
        {"id": "power", "role": "supply", "unit": 3, "pins": {"negative": "4", "positive": "8"}},
    ]


def add_opamp_package(
    d: Design,
    positive: str,
    negative: str,
    reference: str,
    cap_number: int,
    role_a: str,
    role_b: str,
) -> None:
    d.component(
        "amp", "U3", "Amplifier_Operational:NE5532", "NE5532", opamp_functions(role_a, role_b)
    )
    d.component("amp_cpos", f"C{cap_number}", "Device:C", "100n")
    d.component("amp_cneg", f"C{cap_number + 1}", "Device:C", "100n")
    d.connect(positive, "amp", "8")
    d.connect(negative, "amp", "4")
    d.connect(positive, "amp_cpos", "1")
    d.connect(reference, "amp_cpos", "2")
    d.connect(reference, "amp_cneg", "1")
    d.connect(negative, "amp_cneg", "2")
    d.relation(
        "amp.supply",
        "power_rails",
        component="amp",
        unit=3,
        positive=positive,
        negative=negative,
        reference=reference,
    )
    d.relation(
        "amp.bypass.plus",
        "decoupling",
        component="amp_cpos",
        consumer=["amp", "8"],
        supply=positive,
        **{"return": reference},
    )
    d.relation(
        "amp.bypass.minus",
        "decoupling",
        component="amp_cneg",
        consumer=["amp", "4"],
        supply=reference,
        **{"return": negative},
    )


def amp_pins(function: str) -> tuple[str, str, str]:
    return ("1", "2", "3") if function == "a" else ("7", "6", "5")


def add_buffer(
    d: Design, function: str, input_net: str, output_net: str, reference: str, unused: bool = False
) -> None:
    out, minus, plus = amp_pins(function)
    d.connect(input_net, "amp", plus)
    d.connect(output_net, "amp", out)
    d.connect(output_net, "amp", minus)
    fields: dict[str, object] = {
        "component": "amp",
        "function": function,
        "input": input_net,
        "output": output_net,
    }
    if unused:
        fields["unused"] = True
    else:
        fields["reference"] = reference
    d.relation(f"amp.{function}.stage", "amplifier", **fields)
    d.relation(
        f"amp.{function}.loop",
        "feedback",
        component="amp",
        function=function,
        source=out,
        sense=minus,
        net=output_net,
        polarity="negative",
    )


def add_noninverting(
    d: Design,
    function: str,
    input_net: str,
    output_net: str,
    reference: str,
    resistor_number: int,
) -> None:
    out, minus, plus = amp_pins(function)
    feedback = f"amp_{function}_feedback"
    gain = f"amp_{function}_gain"
    sum_net = f"AMP_{function.upper()}_FB"
    d.component(feedback, f"R{resistor_number}", "Device:R", "100k")
    d.component(gain, f"R{resistor_number + 1}", "Device:R", "10k")
    d.connect(input_net, "amp", plus)
    d.connect(output_net, "amp", out)
    d.connect(output_net, feedback, "2")
    d.connect(sum_net, "amp", minus)
    d.connect(sum_net, feedback, "1")
    d.connect(sum_net, gain, "1")
    d.connect(reference, gain, "2")
    d.relation(
        f"amp.{function}.stage",
        "amplifier",
        component="amp",
        function=function,
        input=input_net,
        output=output_net,
        reference=reference,
    )
    d.relation(
        f"amp.{function}.loop",
        "feedback",
        component="amp",
        function=function,
        source=out,
        sense=minus,
        net=output_net,
        polarity="negative",
        resistor=feedback,
    )
    d.relation(f"amp.{function}.gain", "shunt", component=gain, node=sum_net, reference=reference)


def add_inverting(
    d: Design,
    function: str,
    input_net: str,
    output_net: str,
    reference: str,
    resistor_number: int,
) -> None:
    out, minus, plus = amp_pins(function)
    input_r = f"amp_{function}_input"
    feedback = f"amp_{function}_feedback"
    sum_net = f"AMP_{function.upper()}_SUM"
    d.component(input_r, f"R{resistor_number}", "Device:R", "10k")
    d.component(feedback, f"R{resistor_number + 1}", "Device:R", "100k")
    d.connect(reference, "amp", plus)
    d.connect(input_net, input_r, "1")
    d.connect(sum_net, input_r, "2")
    d.connect(sum_net, "amp", minus)
    d.connect(sum_net, feedback, "1")
    d.connect(output_net, feedback, "2")
    d.connect(output_net, "amp", out)
    d.relation(
        f"amp.{function}.stage",
        "amplifier",
        component="amp",
        function=function,
        input=input_net,
        output=output_net,
        reference=reference,
    )
    d.relation(
        f"amp.{function}.loop",
        "feedback",
        component="amp",
        function=function,
        source=out,
        sense=minus,
        net=output_net,
        polarity="negative",
        resistor=feedback,
    )
    d.relation(
        f"amp.{function}.input", "series", component=input_r, input=input_net, output=sum_net
    )


def add_sallen_key(
    d: Design,
    function: str,
    input_net: str,
    output_net: str,
    reference: str,
    resistor_number: int,
    capacitor_number: int,
) -> None:
    out, minus, plus = amp_pins(function)
    upstream = f"sk_{function}_upstream_r"
    filter_r = f"sk_{function}_filter_r"
    shunt_c = f"sk_{function}_shunt_c"
    bridge_c = f"sk_{function}_bridge_c"
    intermediate = f"SK_{function.upper()}_INTERMEDIATE"
    filter_net = f"SK_{function.upper()}_FILTER"
    d.component(upstream, f"R{resistor_number}", "Device:R", "10k")
    d.component(filter_r, f"R{resistor_number + 1}", "Device:R", "10k")
    d.component(shunt_c, f"C{capacitor_number}", "Device:C", "10n")
    d.component(bridge_c, f"C{capacitor_number + 1}", "Device:C", "10n")
    d.connect(input_net, upstream, "1")
    d.connect(intermediate, upstream, "2")
    d.connect(intermediate, filter_r, "1")
    d.connect(filter_net, filter_r, "2")
    d.connect(filter_net, shunt_c, "1")
    d.connect(reference, shunt_c, "2")
    d.connect(intermediate, bridge_c, "1")
    d.connect(output_net, bridge_c, "2")
    d.connect(filter_net, "amp", plus)
    d.connect(output_net, "amp", out)
    d.connect(output_net, "amp", minus)
    d.relation(
        f"amp.{function}.stage",
        "amplifier",
        component="amp",
        function=function,
        input=filter_net,
        output=output_net,
        reference=reference,
    )
    d.relation(
        f"amp.{function}.loop",
        "feedback",
        component="amp",
        function=function,
        source=out,
        sense=minus,
        net=output_net,
        polarity="negative",
    )
    d.relation(
        f"sk.{function}.upstream",
        "series",
        component=upstream,
        input=input_net,
        output=intermediate,
    )
    d.relation(
        f"sk.{function}.filter", "series", component=filter_r, input=intermediate, output=filter_net
    )
    d.relation(
        f"sk.{function}.shunt", "shunt", component=shunt_c, node=filter_net, reference=reference
    )
    d.relation(
        f"sk.{function}.bridge",
        "bridge",
        component=bridge_c,
        first=intermediate,
        second=output_net,
        purpose="feedback",
    )


def add_rc(
    d: Design,
    prefix: str,
    input_net: str,
    output_net: str,
    reference: str,
    resistor_ref: str,
    capacitor_ref: str,
) -> None:
    d.component(f"{prefix}_r", resistor_ref, "Device:R", "1k")
    d.component(f"{prefix}_c", capacitor_ref, "Device:C", "100n")
    d.connect(input_net, f"{prefix}_r", "1")
    d.connect(output_net, f"{prefix}_r", "2")
    d.connect(output_net, f"{prefix}_c", "1")
    d.connect(reference, f"{prefix}_c", "2")
    d.relation(
        f"{prefix}.series", "series", component=f"{prefix}_r", input=input_net, output=output_net
    )
    d.relation(
        f"{prefix}.shunt", "shunt", component=f"{prefix}_c", node=output_net, reference=reference
    )


def add_highpass(
    d: Design,
    input_net: str,
    output_net: str,
    reference: str,
    capacitor_ref: str,
    resistor_ref: str,
) -> None:
    d.component("highpass_c", capacitor_ref, "Device:C", "100n")
    d.component("highpass_r", resistor_ref, "Device:R", "100k")
    d.connect(input_net, "highpass_c", "1")
    d.connect(output_net, "highpass_c", "2")
    d.connect(output_net, "highpass_r", "1")
    d.connect(reference, "highpass_r", "2")
    d.relation(
        "highpass.series", "series", component="highpass_c", input=input_net, output=output_net
    )
    d.relation(
        "highpass.shunt", "shunt", component="highpass_r", node=output_net, reference=reference
    )


def add_led(
    d: Design, prefix: str, input_net: str, reference: str, resistor_ref: str, led_ref: str
) -> None:
    middle = f"{prefix.upper()}_MID"
    d.component(f"{prefix}_r", resistor_ref, "Device:R", "1k")
    d.component(f"{prefix}_led", led_ref, "Device:LED", "LED")
    d.connect(input_net, f"{prefix}_r", "1")
    d.connect(middle, f"{prefix}_r", "2")
    d.connect(middle, f"{prefix}_led", "2")
    d.connect(reference, f"{prefix}_led", "1")
    d.relation(
        f"{prefix}.series", "series", component=f"{prefix}_r", input=input_net, output=middle
    )
    d.relation(
        f"{prefix}.polarity", "polarity", component=f"{prefix}_led", anode=middle, cathode=reference
    )


def v6_1() -> dict:
    d = Design("regulated_dual_opamp_mixed_outputs", "V6RegulatedDualOpampMixedOutputs")
    for args in [
        ("source", "J1", "External supply", "VIN"),
        ("return", "J2", "Return", "REF"),
        ("negative", "J3", "Negative rail", "VMINUS"),
        ("input_a", "J4", "Input A", "IN_A"),
        ("output_a", "J5", "Output A", "OUT_A"),
        ("input_b", "J6", "Input B", "IN_B"),
        ("output_b", "J7", "Output B", "FILTERED_B"),
    ]:
        d.interface(*args)
    add_regulator(d, "regulator", "U1", "VIN", "VPLUS", "REF", 1)
    add_opamp_package(d, "VPLUS", "VMINUS", "REF", 3, "amplifier", "amplifier")
    add_noninverting(d, "a", "IN_A", "OUT_A", "REF", 1)
    add_inverting(d, "b", "IN_B", "OUT_B", "REF", 3)
    add_led(d, "indicator", "OUT_A", "REF", "R5", "D1")
    add_rc(d, "output_filter", "OUT_B", "FILTERED_B", "REF", "R6", "C5")
    d.flag("flag.input", "#FLG01", "VIN")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.return", "#FLG03", "REF")
    return d.finish()


def v6_2() -> dict:
    d = Design("timer_filtered_buffer_split_load", "V6TimerFilteredBufferSplitLoad")
    for args in [
        ("source", "J1", "Supply", "VCC"),
        ("return", "J2", "Return", "REF"),
        ("negative", "J3", "Negative rail", "VMINUS"),
        ("output", "J4", "Buffered output", "BUFFERED"),
    ]:
        d.interface(*args)
    add_timer(d, "timer", "U1", "VCC", "REF", "TIMER_OUT", 1, 1)
    add_rc(d, "timer_filter", "TIMER_OUT", "FILTERED", "REF", "R3", "C3")
    add_opamp_package(d, "VCC", "VMINUS", "REF", 4, "buffer", "parked_buffer")
    add_buffer(d, "a", "FILTERED", "BUFFERED", "REF")
    add_buffer(d, "b", "REF", "PARK", "REF", unused=True)
    add_led(d, "indicator", "BUFFERED", "REF", "R4", "D1")
    d.flag("flag.supply", "#FLG01", "VCC")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.return", "#FLG03", "REF")
    return d.finish()


def v6_3() -> dict:
    d = Design("reference_sallen_key_output_rc", "V6ReferenceSallenKeyOutputRc")
    for args in [
        ("positive", "J1", "Positive rail", "VPLUS"),
        ("negative", "J2", "Negative rail", "VMINUS"),
        ("input", "J3", "Signal input", "IN"),
        ("output", "J4", "Filtered output", "FINAL"),
    ]:
        d.interface(*args)
    d.component("reference_upper", "R1", "Device:R", "10k")
    d.component("reference_lower", "R2", "Device:R", "10k")
    d.connect("VPLUS", "reference_upper", "1")
    d.connect("VREF", "reference_upper", "2")
    d.connect("VREF", "reference_lower", "1")
    d.connect("VMINUS", "reference_lower", "2")
    d.relation(
        "reference.midpoint",
        "reference_divider",
        upper="reference_upper",
        lower="reference_lower",
        positive="VPLUS",
        local="VREF",
        negative="VMINUS",
    )
    add_opamp_package(d, "VPLUS", "VMINUS", "VREF", 1, "buffer", "parked_buffer")
    add_sallen_key(d, "a", "IN", "FILTER_OUT", "VREF", 3, 3)
    add_buffer(d, "b", "VREF", "PARK", "VREF", unused=True)
    add_rc(d, "output_filter", "FILTER_OUT", "FINAL", "VREF", "R5", "C5")
    d.flag("flag.positive", "#FLG01", "VPLUS")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    return d.finish()


def v6_4() -> dict:
    d = Design("dual_timer_to_dual_opamp", "V6DualTimerToDualOpamp")
    for args in [
        ("source", "J1", "Shared supply", "VCC"),
        ("return", "J2", "Return", "REF"),
        ("negative", "J3", "Negative rail", "VMINUS"),
        ("output_a", "J4", "Output A", "OUT_A"),
        ("output_b", "J5", "Output B", "OUT_B"),
    ]:
        d.interface(*args)
    add_timer(d, "timer_a", "U1", "VCC", "REF", "TIMER_A_OUT", 1, 1)
    add_timer(d, "timer_b", "U2", "VCC", "REF", "TIMER_B_OUT", 3, 3)
    add_opamp_package(d, "VCC", "VMINUS", "REF", 5, "buffer", "amplifier")
    add_buffer(d, "a", "TIMER_A_OUT", "OUT_A", "REF")
    add_noninverting(d, "b", "TIMER_B_OUT", "OUT_B", "REF", 5)
    d.flag("flag.supply", "#FLG01", "VCC")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.return", "#FLG03", "REF")
    return d.finish()


def v6_5() -> dict:
    d = Design("sallen_key_dual_output_branches", "V6SallenKeyDualOutputBranches")
    for args in [
        ("positive", "J1", "Positive rail", "VPLUS"),
        ("negative", "J2", "Negative rail", "VMINUS"),
        ("return", "J3", "Reference", "REF"),
        ("input", "J4", "Signal input", "IN"),
        ("active_output", "J5", "Active filter output", "FILTER_OUT"),
        ("filtered_output", "J6", "RC output", "FINAL"),
    ]:
        d.interface(*args)
    add_opamp_package(d, "VPLUS", "VMINUS", "REF", 1, "buffer", "parked_buffer")
    add_sallen_key(d, "a", "IN", "FILTER_OUT", "REF", 1, 3)
    add_buffer(d, "b", "REF", "PARK", "REF", unused=True)
    add_led(d, "indicator", "FILTER_OUT", "REF", "R3", "D1")
    add_rc(d, "output_filter", "FILTER_OUT", "FINAL", "REF", "R4", "C5")
    d.flag("flag.positive", "#FLG01", "VPLUS")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.reference", "#FLG03", "REF")
    return d.finish()


def v6_6() -> dict:
    d = Design("highpass_parallel_mixed_dual_opamp", "V6HighpassParallelMixedDualOpamp")
    for args in [
        ("positive", "J1", "Positive rail", "VPLUS"),
        ("negative", "J2", "Negative rail", "VMINUS"),
        ("return", "J3", "Reference", "REF"),
        ("input", "J4", "Signal input", "IN"),
        ("output_a", "J5", "Output A", "OUT_A"),
        ("output_b", "J6", "Output B", "OUT_B"),
    ]:
        d.interface(*args)
    add_highpass(d, "IN", "HIGHPASS", "REF", "C1", "R1")
    add_opamp_package(d, "VPLUS", "VMINUS", "REF", 2, "amplifier", "amplifier")
    add_noninverting(d, "a", "HIGHPASS", "OUT_A", "REF", 2)
    add_inverting(d, "b", "HIGHPASS", "OUT_B", "REF", 4)
    d.flag("flag.positive", "#FLG01", "VPLUS")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.reference", "#FLG03", "REF")
    return d.finish()


def v6_7() -> dict:
    d = Design("dual_regulator_independent_subsystems", "V6DualRegulatorIndependentSubsystems")
    for args in [
        ("source", "J1", "External supply", "VIN"),
        ("return", "J2", "Return", "REF"),
        ("negative", "J3", "Negative rail", "VMINUS"),
        ("buffer_input", "J4", "Buffer input", "BUFFER_IN"),
        ("output", "J5", "Filtered output", "FINAL"),
    ]:
        d.interface(*args)
    add_regulator(d, "reg_a", "U1", "VIN", "VCC_A", "REF", 1)
    add_regulator(d, "reg_b", "U2", "VIN", "VCC_B", "REF", 3)
    add_timer(d, "timer", "U4", "VCC_A", "REF", "TIMER_OUT", 1, 5)
    add_led(d, "indicator", "TIMER_OUT", "REF", "R3", "D1")
    add_opamp_package(d, "VCC_B", "VMINUS", "REF", 7, "buffer", "parked_buffer")
    add_buffer(d, "a", "BUFFER_IN", "BUFFERED", "REF")
    add_buffer(d, "b", "REF", "PARK", "REF", unused=True)
    add_rc(d, "output_filter", "BUFFERED", "FINAL", "REF", "R4", "C9")
    d.flag("flag.input", "#FLG01", "VIN")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.return", "#FLG03", "REF")
    return d.finish()


def v6_8() -> dict:
    d = Design("regulated_timer_buffer_dual_branch", "V6RegulatedTimerBufferDualBranch")
    for args in [
        ("source", "J1", "External supply", "VIN"),
        ("return", "J2", "Return", "REF"),
        ("negative", "J3", "Negative rail", "VMINUS"),
        ("output", "J4", "Filtered output", "FINAL"),
    ]:
        d.interface(*args)
    add_regulator(d, "regulator", "U1", "VIN", "VCC", "REF", 1)
    add_timer(d, "timer", "U2", "VCC", "REF", "TIMER_OUT", 1, 3)
    add_opamp_package(d, "VCC", "VMINUS", "REF", 5, "buffer", "parked_buffer")
    add_buffer(d, "a", "TIMER_OUT", "BUFFERED", "REF")
    add_buffer(d, "b", "REF", "PARK", "REF", unused=True)
    add_led(d, "indicator", "BUFFERED", "REF", "R3", "D1")
    add_rc(d, "output_filter", "BUFFERED", "FINAL", "REF", "R4", "C7")
    d.flag("flag.input", "#FLG01", "VIN")
    d.flag("flag.negative", "#FLG02", "VMINUS")
    d.flag("flag.return", "#FLG03", "REF")
    return d.finish()


CASES = [v6_1, v6_2, v6_3, v6_4, v6_5, v6_6, v6_7, v6_8]
REQUESTS = [
    ("regulated_dual_opamp_mixed_outputs", "Regulated dual op-amp mixed outputs"),
    ("timer_filtered_buffer_split_load", "Timer, RC filter, buffer, split output load"),
    ("reference_sallen_key_output_rc", "Local-reference Sallen-Key with RC output"),
    ("dual_timer_to_dual_opamp", "Two timers feeding two units of one op-amp package"),
    ("sallen_key_dual_output_branches", "Sallen-Key output with LED and RC branches"),
    ("highpass_parallel_mixed_dual_opamp", "High-pass fanout to unlike dual op-amp stages"),
    (
        "dual_regulator_independent_subsystems",
        "Two regulators feeding independent timer and buffer subsystems",
    ),
    ("regulated_timer_buffer_dual_branch", "Regulated timer-buffer path with dual output branches"),
]


def main() -> None:
    if (HERE / "runs").exists() or (HERE / "automated_results.json").exists():
        raise SystemExit("refusing to author after blind execution began")
    expected_freeze = (HERE / "implementation_freeze.sha256").read_text().split()[0]
    if sha256(HERE / "implementation_freeze.json") != expected_freeze:
        raise SystemExit("implementation freeze hash mismatch")
    ir_dir = HERE / "ir"
    ir_dir.mkdir(exist_ok=False)
    hashes: dict[str, str] = {}
    cases = []
    for number, (factory, request) in enumerate(zip(CASES, REQUESTS, strict=True), 1):
        case_id = f"V6-{number}"
        data = factory()
        if data["id"] != request[0]:
            raise RuntimeError(f"design identity mismatch for {case_id}")
        validate(data, assets())
        path = ir_dir / f"{case_id}.json"
        path.write_text(json.dumps(data, indent=2) + "\n")
        hashes[case_id] = sha256(path)
        cases.append(
            {
                "case_id": case_id,
                "design_id": data["id"],
                "requested_design": request[1],
                "ir": f"ir/{case_id}.json",
            }
        )
    corpus = {
        "schema_version": "corpus.v6",
        "evaluation": "M2h1 — corpus.v6 frozen blind qualification",
        "held_out": True,
        "preregistered_case_count": 8,
        "required_accepted_count": 8,
        "cases": cases,
    }
    corpus_path = HERE / "corpus.v6.json"
    corpus_path.write_text(json.dumps(corpus, indent=2) + "\n")
    (HERE / "corpus.v6.sha256").write_text(f"{sha256(corpus_path)}  corpus.v6.json\n")
    (HERE / "ir.sha256.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps({"corpus_sha256": sha256(corpus_path), "ir_sha256": hashes}, indent=2))


if __name__ == "__main__":
    main()
