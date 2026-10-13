# Parallel-output signal-lineage frontier qualification checkpoint — 2026-10-13

Status: **BEHAVIOR CANDIDATE; NATIVE COMPARATIVE ACCEPTANCE NOT PROVED**.

Production behavior commit `d7d21ea42017f13de71ab3934e005da98ea995b9` scopes multi-output interface-frontier ranking to each directed signal producer lineage rather than the rightmost unrelated parallel chain. Single-output global-frontier semantics remain unchanged. Source-level tests cover separate output chains, reversed outputs, net/declaration permutation, and the single-output exemption. No fixture, refdes, or case-name dispatch is introduced.

Format-only descendants `9c37cf645c0a68caf128f99596f089280212acbc` and `380aff3bd86188ecff719177c0f3822ab8120bd0` preserve production behavior. Fast Validation 38391248174 passed the locked-runner complete pytest/current-source real-tool regressions and hosted contract pytest but failed only the new test's Ruff-format check. The second descendant applies the exact Ruff diff; its exact-head Fast Validation is pending at this checkpoint.

This documentation-only descendant requests all three source-matched five-run locked-KiCad qualification suites (56 base positives plus V3-8 negative, I1–I6 interactions, nine structural classes) and the bounded generic development composition probe. Passing them would establish source qualification, **not** native aesthetic acceptance. Afterward independently compare all 90 preserved historical cases and all 137 normalized five-run native renders, then inspect every distinct governed case. Do not change the frozen observer, thresholds, historical evidence, or electrical invariants.

The last completed independent comparison failed five frozen criteria: baseline hard-defect closure, per-case hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and `i4__b2_mixed` improvement. Sections 15–21 of `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_TODO_2026-10-07.md` remain **UNCHECKED** until affirmative current-source evidence closes each obligation.
