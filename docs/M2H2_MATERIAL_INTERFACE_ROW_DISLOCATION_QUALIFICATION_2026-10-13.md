# M2h2 material interface-row dislocation — source qualification checkpoint

Status: **SOURCE BEHAVIOR CANDIDATE; NOT NATIVE VISUAL ACCEPTANCE**.

## Source and generic intent

The behavior commit `5c547d0d6b77054a314f345d6f7bdcb074e8d0d6` introduces a separate material output/input row-dislocation tier in deterministic composition candidate selection. The tier measures only each interface's nearest directed semantic owner and uses the pre-existing 80 mm local-visible signal corridor threshold. When a directed connector is more than that distance away from every owning row, this excess outranks marginal return-leg/backtracking improvements; connector-row differences within that corridor remain below route-backtracking. Flow reversal, interface side, semantic grouping, and all hard electrical/placement invariants remain above this tier. No case/refdes/net-name or historical-threshold special case was introduced.

Compatibility/regression commit `3d3e7e2bb77d7480cdb558ce08126f4c4fcc02e3` preserves the existing two-value alignment helper contract and stable semantic vector/named-map equality, while exposing the separate tier in diagnostic production selection keys. The locked-runner complete pytest and full current-source V6-3/DP2/connector/selected-triple/whole-band regression steps passed on that commit. Its static check found one test formatting issue only. Formatting-only source `519d3856f5a088f2127dbfbc97dfbc5ef0b5fc3e` applies the exact Ruff diff; at this launch, source-matched Fast Validation 38399951542 has passed static lint/format/diff and hosted contracts, with locked-runner qualification still in progress. Its pinned toolchain diagnostic is separately tracked. Do not pre-claim full Fast Validation or aesthetic acceptance.

## Required evidence

Request exact-head five-run qualification for all 56 positives with V3-8 negative, all I1–I6 interactions, all nine structural classes, and the generic development composition probe. Recheck rank diagnostics for the two already-proved `i4__b2_mixed` alternatives, without assuming either layout now wins or passes the frozen independent visual observer. If source qualification passes, independently audit all 90 historical cases and normalized native renders from the exact preserved source evidence root, then inspect all 137 distinct governed native cases.

The latest completed older-source 90-case independent audit still failed hard-defect closure, individual nonworsening, routing aesthetics, repeated-structure tolerance, and mixed-case improvement. These five criteria remain open and unchanged. Sections 15–21 of `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` remain unchecked until exact-source affirmative evidence is available. Historical artifacts and tolerances are immutable.
