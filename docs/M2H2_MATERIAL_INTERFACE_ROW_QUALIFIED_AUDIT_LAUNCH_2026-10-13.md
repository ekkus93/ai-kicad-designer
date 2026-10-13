# M2h2 qualified material-row candidate — independent audit launch

**Status: EXACT-SOURCE ELECTRICAL / STRUCTURAL / GENERATION QUALIFICATION PASS; HUMAN-COMPOSITION ACCEPTANCE OPEN.**

Qualification source (unchanged by this documentation-only checkpoint): `d0b6fffd628519277faf0a4a17b817cd2e0ecf3d`.
Preserved source-matched evidence root: `$HOME/m2h2-evidence/d0b6fffd628519277faf0a4a17b817cd2e0ecf3d/` on the locked KiCad runner. Historical baselines and all frozen thresholds remain unchanged.

## Completed exact-source qualification

- Locked KiCad 10.0.6 toolchain diagnostic: [run 38400499651](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499651), PASS.
- Complete Fast Validation (locked-runner pytest/current-source real-tool regressions, hosted contracts and Ruff/static): [38400499408](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499408), PASS.
- 56 positive base cases x5 plus historical V3-8-negative: [38400499875](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499875), PASS.
- All I1–I6 five-run interactions: [38400499505](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499505), PASS.
- All nine structural-class five-run qualifications: [38400499660](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499660), PASS.
- Base and structural native KiCad render transfer: [38405120583](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38405120583), [38401007581](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38401007581), both PASS.
- Bounded generic development composition probe: [38400499754](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38400499754), PASS as source diagnostics only.

## Concrete remaining mixed-case falsification

Current `i4__b2_mixed` candidate selection remains seed 4/round 0, not seed 1/round 0. Both have zero stage inversions, reversal distance, interface-side violations and frontier distance; both also have **zero material-interface-row-dislocation penalty**, so the new tier does not resolve their tradeoff. Selected seed 4: directed-output row drift 68 grid units, route backtracking 78, routed union 335.28 mm. Proved alternative seed 1: row drift 28, backtracking 88, routed union 287.02 mm. Production priority first differs at key index 17 (route backtracking), favoring seed 4. This result is a diagnostic, **not evidence the alternative is visually acceptable**, nor justification to special-case a fixture.

## Required next independent checks

This documentation-only commit requests the full 90-case frozen historical visual comparison and the complete normalized 137-case x5 native SVG inventory against **exact qualification source `d0b6fffd628519277faf0a4a17b817cd2e0ecf3d`** using persisted evidence. Require per-case hard-defect and visual-aesthetic witnesses, including U-detours, branch inconsistency, repeated-stage alignment and mixed-case output ownership. Do not misinterpret a passing render inventory or electrical qualification as visual acceptance. If visual comparison fails, reconcile the failed criteria and continue generic source-level remediation from the exact current `master` head.

Sections 15–21 in `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` remain **unchecked**. No source freeze, overall PASS, corpus.v7 or M3 work is authorized.
