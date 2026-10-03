"""Real-tool check of a proved alternate packing for a frozen interaction IR."""

from __future__ import annotations

import argparse
import json
import subprocess
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
from run_m2g2_qualification import _erc_violations, _normalized_svg, _sha


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


def extra_packings(baseline: Packing, variants=None) -> tuple[Packing, ...]:
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
    # A measured active-function row keeps package/support cells in an adjacent band.
    active = [
        item
        for item in items
        if not item.fragment.block.unused
        and item.fragment.block.kind
        in {"buffer", "noninverting_amplifier", "inverting_amplifier", "sallen_key"}
    ]
    support = [
        item for item in items if item.fragment.block.kind != "interface" and item not in active
    ]
    if len(active) > 1:
        row_top = min(item.envelope[1] for item in active)
        left = min(item.envelope[0] for item in items)
        for margin in (2, 4, 6, 8):
            replacement = {}
            cursor = left + margin * PITCH
            for item in active:
                replacement[item.fragment.block.id] = _place(item.fragment, cursor, row_top)
                cursor += item.envelope[2] - item.envelope[0] + 2 * PITCH
            next_top = max(item.envelope[3] for item in replacement.values()) + 2 * PITCH
            cursor = left
            for item in support:
                replacement[item.fragment.block.id] = _place(item.fragment, cursor, next_top)
                cursor += item.envelope[2] - item.envelope[0] + 2 * PITCH
            candidates.insert(
                0,
                Packing(
                    tuple(replacement.get(item.fragment.block.id, item) for item in items),
                    baseline.attempts + ("measured-active-row-support-band",),
                ),
            )
    # One measured row of all non-interface cells uses certified local variants.
    # Interface cells remain in their existing band; no semantic topology changes.
    if variants is not None:
        row_cells = [item for item in items if item.fragment.block.kind != "interface"]
        if len(row_cells) > 1:
            left = min(item.envelope[0] for item in items)
            row_top = (
                max(
                    (item.envelope[3] for item in items if item.fragment.block.kind == "interface"),
                    default=min(item.envelope[1] for item in items),
                )
                + 2 * PITCH
            )
            replacement = {}
            cursor = left
            for item in row_cells:
                fragment = min(
                    variants[item.fragment.block.id],
                    key=lambda variant: (
                        variant.envelope[2] - variant.envelope[0],
                        variant.envelope[3] - variant.envelope[1],
                        variant.id,
                    ),
                )
                replacement[item.fragment.block.id] = _place(fragment, cursor, row_top)
                cursor += fragment.envelope[2] - fragment.envelope[0] + 2 * PITCH
            if cursor - left - 2 * PITCH <= MAX_CONTENT_WIDTH:
                candidates.insert(
                    0,
                    Packing(
                        tuple(replacement.get(item.fragment.block.id, item) for item in items),
                        baseline.attempts + ("measured-all-cell-row",),
                    ),
                )
    # Generic vertical separation/backfill proposals include passive-only designs.
    movable = [item for item in items if item.fragment.block.kind != "interface"]
    for target in movable:
        for steps in (6, 10, 14, 20, 30, 40, 50, 60):
            moved = _place(target.fragment, target.envelope[0], target.envelope[1] + steps * PITCH)
            candidates.append(
                Packing(
                    tuple(moved if item is target else item for item in items),
                    baseline.attempts + ("measured-vertical-band",),
                )
            )
    # Preserve a staggered target while moving a conflicting peer below it.
    repaired = []
    for proposal in candidates:
        changed = [
            item
            for item, old in zip(proposal.fragments, items, strict=True)
            if item.delta != old.delta
        ]
        if len(changed) != 1:
            continue
        target = changed[0]
        replacements = {}
        for peer in proposal.fragments:
            if peer.fragment.block.id == target.fragment.block.id:
                continue
            if (
                max(peer.envelope[0], target.envelope[0])
                < min(peer.envelope[2], target.envelope[2])
                and max(peer.envelope[1], target.envelope[1])
                < min(peer.envelope[3], target.envelope[3])
                and peer.fragment.block.kind not in {"interface", "timer", "power_stage"}
            ):
                replacements[peer.fragment.block.id] = _place(
                    peer.fragment, peer.envelope[0], target.envelope[3] + PITCH
                )
        if replacements:
            repaired.append(
                Packing(
                    tuple(
                        replacements.get(item.fragment.block.id, item)
                        for item in proposal.fragments
                    ),
                    proposal.attempts + ("measured-peer-separation",),
                )
            )
    return tuple((*candidates, *repaired))


def interleaved(packing: Packing) -> bool:
    cells = [item for item in packing.fragments if item.fragment.block.kind != "interface"]
    return any(
        abs(first.envelope[1] - second.envelope[1]) > 5_080_000
        and max(first.envelope[1], second.envelope[1]) < min(first.envelope[3], second.envelope[3])
        and (first.envelope[2] <= second.envelope[0] or second.envelope[2] <= first.envelope[0])
        for index, first in enumerate(cells)
        for second in cells[index + 1 :]
    )


def frozen_obligations(observed: dict, design: dict, expected: dict) -> dict:
    """Recheck frozen expectations from XML and independently resolved embedded pins."""
    physical = {part["id"] for part in design["components"]}
    reference = {part["id"]: part["refdes"] for part in design["components"]}
    expected_partitions = sorted(
        sorted((reference[component], pin) for component, pin in members if component in physical)
        for members in expected["partitions"].values()
    )
    actual_partitions = sorted(
        sorted((ref, pin) for ref, pin in members) for members in observed["nets"].values()
    )
    actual_terminals = sorted(
        (component, pin)
        for members in observed["nets"].values()
        for ref, pin in members
        for component, component_ref in reference.items()
        if component_ref == ref
    )
    expected_terminals = sorted(
        tuple(item) for item in expected["terminal_inventory"] if item[0] in physical
    )
    paths = []
    for obligation in expected["path_obligations"]:
        first = observed["pin_positions"][(reference[obligation["from"][0]], obligation["from"][1])]
        second = observed["pin_positions"][(reference[obligation["to"][0]], obligation["to"][1])]
        span = abs(first[0] - second[0]) + abs(first[1] - second[1])
        limit = obligation["maximum_span_nm"]
        paths.append(
            {
                "id": obligation["id"],
                "span_nm": span,
                "limit_nm": limit,
                "pass": limit is None or span <= limit,
            }
        )
    precedence = []
    for relation in expected["precedence"]:
        first = observed["pin_positions"][(reference[relation["source"][0]], relation["source"][1])]
        second = observed["pin_positions"][
            (reference[relation["target"][0]], relation["target"][1])
        ]
        precedence.append(
            {
                "source": relation["source"],
                "target": relation["target"],
                "source_x_nm": first[0],
                "target_x_nm": second[0],
                "pass": first[0] < second[0],
            }
        )
    return {
        "partition_match": actual_partitions == expected_partitions,
        "terminal_match": actual_terminals == expected_terminals,
        "paths": paths,
        "precedence": precedence,
        "pass": actual_partitions == expected_partitions
        and actual_terminals == expected_terminals
        and all(item["pass"] for item in paths + precedence),
    }


def select_scene(design: dict, emitted_assets: dict, args) -> tuple:
    """A fresh bounded search for every clean build; no repeated emission of one scene."""
    plan = semantic_plan(design, emitted_assets)
    variants = fragment_variants(design, emitted_assets, plan)
    seeds = pack_fragment_candidates(plan, variants)
    packings = (
        *seeds,
        *_partial_beam_candidates(plan, variants),
        *extra_packings(seeds[0], variants),
    )
    candidates = []
    seen = set()
    for index, packing in enumerate(packings):
        identity = tuple((item.fragment.id, item.delta) for item in packing.fragments)
        if identity in seen:
            continue
        seen.add(identity)
        observed_bands = band_count(packing, core_only=args.core_bands)
        if observed_bands < args.bands if args.minimum_bands else observed_bands != args.bands:
            continue
        if args.interleaved and not interleaved(packing):
            continue
        cells = packing.fragments
        # Sound occupied-envelope pruning; certification remains authoritative.
        if any(
            max(first.envelope[0], second.envelope[0]) < min(first.envelope[2], second.envelope[2])
            and max(first.envelope[1], second.envelope[1])
            < min(first.envelope[3], second.envelope[3])
            for ordinal, first in enumerate(cells)
            for second in cells[ordinal + 1 :]
        ):
            continue
        candidates.append((index, packing))
    # The finite alternatives beyond eight seeds remain explicitly uncovered.
    retained = candidates[:8]
    attempts = []
    proved = []
    for seed, (index, packing) in enumerate(retained):
        for retry in range(4):
            try:
                draft, routes, trees, reservations, metrics = _assemble_candidate(
                    design, emitted_assets, plan, packing, retry=retry
                )
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
            except Exception as exc:
                attempts.append(
                    {
                        "seed": seed,
                        "candidate": index,
                        "retry": retry,
                        "proof": "rejected",
                        "reason": str(exc),
                    }
                )
                continue
            attempts.append({"seed": seed, "candidate": index, "retry": retry, "proof": "pass"})
            quality = (
                max((tree.length for tree in trees), default=0),
                sum(tree.length for tree in trees),
                scene.certificate_digest,
            )
            proved.append((quality, scene, routes, trees, reservations, packing, index, retry))
    ledger = {
        "candidate_budget": 8,
        "repair_rounds_per_seed": 3,
        "slot_ceiling": 32,
        "complete_attempts": len(attempts),
        "attempts": attempts,
        "available_class_candidates": len(candidates),
        "retained_seeds": len(retained),
        "budget_uncovered_candidate_indices": [index for index, _ in candidates[8:]],
    }
    if not proved:
        raise RuntimeError(f"no proved class candidate: {json.dumps(ledger)}")
    selected = min(proved, key=lambda item: item[0])
    return (*selected[1:], ledger)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--design", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--bands", type=int, required=True)
    parser.add_argument("--core-bands", action="store_true")
    parser.add_argument("--interleaved", action="store_true")
    parser.add_argument("--minimum-bands", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    args.out.mkdir(parents=True)
    design = validate(json.loads(args.design.read_text()), assets())
    expected = json.loads(args.design.with_suffix(".expected.json").read_text())
    resolved = assets()
    owned_assets = {component["asset"] for component in design["components"]}
    emitted_assets = {
        key: asset
        for key, asset in resolved.items()
        if key not in ("Regulator_Linear:L7805", "Timer:NE555D") or key in owned_assets
    }
    launcher = validate_toolchain(
        ROOT / "fixtures/m1a/toolchain.lock.json", ROOT / "requirements.lock"
    )
    results = []
    for run in range(1, 6):
        stage = args.out / f"run{run}"
        try:
            scene, routes, trees, reservations, packing, index, retry, ledger = select_scene(
                design, emitted_assets, args
            )
        except Exception as exc:
            (args.out / "failed_search.json").write_text(
                json.dumps({"run": run, "failure": str(exc)}, indent=2) + "\n"
            )
            raise
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
        frozen = frozen_obligations(observed, design, expected)
        erc = json.loads(erc_path.read_text())
        report = {
            "run": run,
            "pass": electrical["status"] == "pass"
            and not electrical["diagnostics"]
            and _erc_violations(erc) == 0
            and frozen["pass"],
            "serialized_scene_verified": "pass",
            "selected_candidate": index,
            "selected_retry": retry,
            "all_bands": band_count(packing),
            "active_core_bands": band_count(packing, core_only=True),
            "interleaved": interleaved(packing),
            "search": ledger,
            "placements": [
                {
                    "block": item.fragment.block.id,
                    "kind": item.fragment.block.kind,
                    "envelope": item.envelope,
                    "variant": item.fragment.id,
                }
                for item in packing.fragments
            ],
            "schematic_sha256": sha256(schematic.read_bytes()),
            "project_sha256": sha256(schematic.with_suffix(".kicad_pro").read_bytes()),
            "svg_normalized_sha256": [_normalized_svg(path) for path in svgs],
            "electrical": electrical,
            "erc_violation_count": _erc_violations(erc),
            "frozen_obligations": frozen,
            "layout": layout,
            "scene_sha256": scene.certificate_digest,
            "candidate_input_policy_sha256": scene.certificate_input_digest,
            "canonical_lengths_nm": {tree.net: tree.length for tree in trees},
            "route_strategies": {route.net: route.strategy for route in routes},
            "reservation_count": len(reservations),
        }
        (stage / "reports/alternative.json").write_text(json.dumps(report, indent=2) + "\n")
        results.append(report)
        print(
            json.dumps(
                {
                    "case": args.design.stem,
                    "run": run,
                    "pass": report["pass"],
                    "all_bands": report["all_bands"],
                    "active_core_bands": report["active_core_bands"],
                    "interleaved": report["interleaved"],
                }
            ),
            flush=True,
        )
    reproducible = len(results) == 5 and all(
        {key: value for key, value in result.items() if key != "run"}
        == {key: value for key, value in results[0].items() if key != "run"}
        for result in results[1:]
    )
    payload = {
        "schema_version": "m2h2.structural-alternative.2",
        "design": str(args.design),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "source_sha256": {
            str(path.relative_to(ROOT)): _sha(path)
            for path in sorted((ROOT / "src/ai_kicad").glob("*.py"))
        },
        "runner_sha256": _sha(Path(__file__)),
        "toolchain_lock_sha256": _sha(ROOT / "fixtures/m1a/toolchain.lock.json"),
        "asset_lock_sha256": _sha(ROOT / "fixtures/m2b/assets.lock.json"),
        "policy_lock_sha256": _sha(ROOT / "fixtures/m1a/policy.lock.json"),
        "expected_sha256": _sha(args.design.with_suffix(".expected.json")),
        "design_sha256": _sha(args.design),
        "runs_per_case": 5,
        "normalization": "Only run ordinal and documented SVG title fields; no search/certificate normalization",
        "required_class": {
            "bands": args.bands,
            "core_only": args.core_bands,
            "minimum_bands": args.minimum_bands,
            "interleaved": args.interleaved,
        },
        "accepted": reproducible and all(item["pass"] for item in results),
        "reproducible": reproducible,
        "runs": results,
    }
    (args.out / "results.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({key: value for key, value in payload.items() if key != "runs"}), flush=True)
    if not payload["accepted"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
