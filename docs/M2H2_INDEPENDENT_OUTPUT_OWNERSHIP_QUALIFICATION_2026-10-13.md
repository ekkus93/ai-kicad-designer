# M2h2 independent final-output ownership — full qualification launch

**Status: SOURCE REGRESSION / STATIC QUALIFIED; NATIVE HUMAN-COMPOSITION ACCEPTANCE NOT YET ESTABLISHED.**

## Production behavior

Source commit `7e8ce802a323f2fc7e7395a6b95b173e94b06f7f` adds a generic measured, semantic multi-output ranking tier to `m2_composition_candidate_rank.py`: only two or more distinct, unambiguously owned directed output connectors are encouraged to share their respective producer rows. Shared-producer fanout, single output, missing or ambiguous ownership, and bidirectional interfaces do not incur this score. Higher-priority electrical/proved legality, flow and side correctness, required grouping and material dislocation remain unchanged. Route-backtracking remains higher than ordinary single-output soft row drift, but independent output ownership is ranked before marginal backtracking. No fixture, component name, refdes or literal net dispatch is introduced.

Source-format commit `c9dab795aad22dec4151deb00edf1b91341dbc4b` and test-format commit `cfe740ffa07dfea4953a0a946c6adfb7c132531a` preserve this behavior. The exact-head Fast Validation [38448245986](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38448245986) **PASSED all three jobs**, including locked-runner complete pytest/current-source native regressions, hosted contracts and Ruff/static/format/diff. Pinned KiCad 10.0.6 toolchain diagnostic **PASSED** for this source. Added regressions cover independent outputs, shared-producer fanout exemption, one-output exemption, ambiguous ownership, and net/declaration-order metamorphics.

## Previous exact-source independent falsification

The preceding qualified production source `d0b6fffd628519277faf0a4a17b817cd2e0ecf3d` passed all three five-run suites and a 137-case/685-native-SVG normalized repeatability inventory but **FAILED** the independent 90-case [frozen comparative audit 38444802583](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38444802583): `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. U-detours were historical 691 versus fresh 857; branch inconsistency was 1529.08 versus fresh 1742.44 mm. That is **NOT** evidence the present new ranking resolves any criterion.

## Current qualification request

This documentation-only descendant explicitly requests all three locked-KiCad five-run workflows and a source-matched generic development composition probe from exact source `cfe740ffa07dfea4953a0a946c6adfb7c132531a`:

1. 56 positive base cases x5 with V3-8 negative.
2. All I1–I6 five-run interactions.
3. Nine structural-class five-run cases.
4. Source-neutral composition probe, including `i4__b2_mixed` selected/proved candidates, row ownership, route-backtracking, routing union and high-priority semantic obligations.

If these pass, transfer base and structural native renders, independently compare all 90 historical cases and the normalized 137-case x5 SVG inventory against evidence under `$HOME/m2h2-evidence/cfe740ffa07dfea4953a0a946c6adfb7c132531a/`, then inspect every distinct governed case. Do not infer aesthetic PASS from source checks, reranking, aggregate improvements, or successful generation.

Sections 15–21 of `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` remain unchecked, historic evidence and observer thresholds frozen; no source freeze, corpus.v7 or M3 work.
