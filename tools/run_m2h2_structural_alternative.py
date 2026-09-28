"""Real-tool check of a proved alternate packing for a frozen interaction IR."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ai_kicad.assets import sha256
from ai_kicad.kicad import run_headless, validate_toolchain
from ai_kicad.m2a import (
    PITCH,
    ROOT,
    Scene,
    certify_scene_geometry,
    certify_scene_inputs,
    emit,
    observe,
    verify_serialized_scene,
)
from ai_kicad.m2b import assets, check_observed_layout, compare, validate
from ai_kicad.m2_compose import _assemble_candidate
from ai_kicad.m2_fragments import fragment_variants
from ai_kicad.m2_pack import (
    MAX_CONTENT_HEIGHT,
    MAX_CONTENT_WIDTH,
    Packing,
    _partial_beam_candidates,
    _place,
    pack_fragment_candidates,
)
from ai_kicad.m2_semantics import semantic_plan
from run_m2g2_qualification import _erc_violations, _normalized_svg


def band_count(packing, *, core_only: bool = False) -> int:
    cells = [
        item
        for item in packing.fragments
        if item.fragment.block.kind != "interface"
        and (
            not core_only
            or (
                not item.fragment.block.unused
                and item.fragment.block.kind
                in {
                    "timer",
                    "power_stage",
                    "buffer",
                    "noninverting_amplifier",
                    "inverting_amplifier",
                    "sallen_key",
                }
            )
        )
    ]
    tops = sorted({item.envelope[1] for item in cells})
    bands = []
    for top in tops:
        if not bands or top - bands[-1] > 5_080_000:
            bands.append(top)
    return len(bands)


def extra_packings(baseline: Packing) -> tuple[Packing, ...]:
    """Bounded measured row compaction and staggered-band development classes."""
    items = baseline.fragments
    functional = [item for item in items if item.fragment.block.function is not None]
    candidates = []
    for target in functional:
        for row_top in sorted({item.envelope[1] for item in functional}):
            if row_top == target.envelope[1]:
                continue
            row = [item for item in items if item is not target and item.envelope[1] == row_top]
            if not row:
                continue
            moved = _place(target.fragment, max(item.envelope[2] for item in row) + PITCH, row_top)
            candidates.append(
                Packing(
                    tuple(moved if item is target else item for item in items),
                    baseline.attempts + ("measured-functional-row-compaction",),
                )
            )
    for target in items:
        if target.fragment.block.kind in {"interface", "timer", "package_power"}:
            continue
        for anchor in items:
            if anchor is target or anchor.fragment.block.kind != "timer":
                continue
            for steps in (6, 10, 14):
                moved = _place(
                    target.fragment,
                    target.envelope[0],
                    anchor.envelope[3] - steps * PITCH,
                )
                candidates.append(
                    Packing(
                        tuple(moved if item is target else item for item in items),
                        baseline.attempts + ("measured-staggered-band",),
                    )
                )
    return tuple(candidates[:32])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bands", type=int, required=True)
    parser.add_argument("--core-bands", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    design = validate(json.loads(args.design.read_text()), assets())
    resolved = assets()
    owned_assets = {component["asset"] for component in design["components"]}
    emitted_assets = {
        key: asset
        for key, asset in resolved.items()
        if key not in ("Regulator_Linear:L7805", "Timer:NE555D") or key in owned_assets
    }
    plan = semantic_plan(design, emitted_assets)
    variants = fragment_variants(design, emitted_assets, plan)
    seeds = pack_fragment_candidates(plan, variants)
    packings = (*seeds, *_partial_beam_candidates(plan, variants), *extra_packings(seeds[0]))
    proved = []
    seen = set()
    for index, packing in enumerate(packings):
        identity = tuple((item.fragment.id, item.delta) for item in packing.fragments)
        if identity in seen or band_count(packing, core_only=args.core_bands) != args.bands:
            continue
        seen.add(identity)
        try:
            draft, routes, trees, reservations, metrics = _assemble_candidate(
                design, emitted_assets, plan, packing, retry=0
            )
        except Exception as exc:
            proved.append({"candidate": index, "proof": "rejected", "reason": str(exc)})
            continue
        scene = certify_scene_geometry(
            Scene(
                draft.positions,
                draft.wires,
                draft.wire_nets,
                draft.labels,
                draft.junctions,
                metrics,
                draft.angles,
                draft.text_positions,
            )
        )
        scene = certify_scene_inputs(
            scene,
            design,
            emitted_assets,
            {
                "schema_version": "m2h2.policy.1",
                "content_width_nm": MAX_CONTENT_WIDTH,
                "content_height_nm": MAX_CONTENT_HEIGHT,
                "canonical_conductor_length_nm": 250_000_000,
                "candidate_budget": 8,
                "repair_rounds_per_seed": 3,
                "grid_pitch_nm": PITCH,
            },
        )
        proved.append({"candidate": index, "proof": "pass"})
        args.out.mkdir(parents=True)
        results = []
        launcher = validate_toolchain(
            ROOT / "fixtures/m1a/toolchain.lock.json", ROOT / "requirements.lock"
        )
        for run in range(1, 6):
            stage = args.out / f"run{run}"
            schematic = emit(design, emitted_assets, scene, stage)
            verify_serialized_scene(design, scene, schematic)
            local_libraries = {"Regulator_Linear": "L7805", "Timer": "NE555D"}
            used_libraries = {
                component["asset"].split(":", 1)[0] for component in design["components"]
            } & set(local_libraries)
            if used_libraries:
                lines = ["(sym_lib_table", "  (version 7)"]
                for library in sorted(used_libraries):
                    stem = local_libraries[library]
                    (schematic.parent / f"{stem}.kicad_sym").write_bytes(
                        (ROOT / "fixtures/m2b" / f"{stem}.kicad_sym").read_bytes()
                    )
                    lines.append(
                        f'  (lib (name "{library}") (type "KiCad") '
                        f'(uri "${{KIPRJMOD}}/{stem}.kicad_sym") (options "") '
                        '(descr "Locked KiCad 10.0.6 symbol"))'
                    )
                lines.append(")")
                (schematic.parent / "sym-lib-table").write_text("\n".join(lines) + "\n")
            netlist, erc_path, svgs = run_headless(
                schematic, launcher, stage, ROOT / "fixtures/m2a/sym-lib-table"
            )
            observed = observe(schematic, netlist)
            electrical = compare(design, observed, resolved)
            layout = {**scene.metrics, **check_observed_layout(schematic, observed, design)}
            erc = json.loads(erc_path.read_text())
            report = {
                "run": run,
                "pass": electrical["status"] == "pass"
                and not electrical["diagnostics"]
                and _erc_violations(erc) == 0,
                "schematic_sha256": sha256(schematic.read_bytes()),
                "project_sha256": sha256(schematic.with_suffix(".kicad_pro").read_bytes()),
                "svg_normalized_sha256": [_normalized_svg(path) for path in svgs],
                "electrical": electrical,
                "erc_violation_count": _erc_violations(erc),
                "layout": layout,
                "scene_sha256": scene.certificate_digest,
                "candidate_input_policy_sha256": scene.certificate_input_digest,
                "canonical_lengths_nm": {tree.net: tree.length for tree in trees},
                "route_strategies": {route.net: route.strategy for route in routes},
                "reservation_count": len(reservations),
            }
            (stage / "reports/alternative.json").write_text(json.dumps(report, indent=2) + "\n")
            results.append(report)
        reproducible = all(
            {key: value for key, value in result.items() if key != "run"}
            == {key: value for key, value in results[0].items() if key != "run"}
            for result in results[1:]
        )
        payload = {
            "schema_version": "m2h2.structural-alternative.1",
            "design": str(args.design),
            "band_count": args.bands,
            "selected_candidate": index,
            "proof_attempts": proved,
            "accepted": reproducible and all(item["pass"] for item in results),
            "reproducible": reproducible,
            "runs": results,
        }
        (args.out / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
        print(json.dumps({"accepted": payload["accepted"], "candidate": index}))
        if not payload["accepted"]:
            raise SystemExit(1)
        return
    raise SystemExit(f"no proved {args.bands}-band candidate: {proved}")


if __name__ == "__main__":
    main()
