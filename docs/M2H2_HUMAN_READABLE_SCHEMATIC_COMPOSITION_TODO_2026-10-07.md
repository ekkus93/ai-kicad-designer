# M2h2 Human-Readable Schematic Composition TODO — 2026-10-07

**Status:** IN PROGRESS / INCOMPLETE

Canonical executable checklist for the post-M2h2 human-readable schematic composition remediation.

Source-level reconciliation checkpoint: current implementation/observer/oracle evidence has been reconciled through the source state immediately preceding this TODO update. Fresh locked-KiCad qualification, native-render inspection, comparative closure, and final PASS remain open and authoritative.

Governing documents:

- `docs/M2_GENERALIZATION_REMEDIATION_SPEC.md`
- `docs/M2H2_FINALIZATION_SPEC_2026-09-27.md`
- `docs/M2H2_HUMAN_READABLE_SCHEMATIC_COMPOSITION_SPEC_2026-10-07.md`
- `fixtures/m2h2/STATUS.md`

Historical M2h2 PASS remains valid as the completed electrical/correctness baseline. This checklist adds a stricter human-readable composition gate; it must not rewrite or weaken historical PASS evidence.

A checkbox may be checked only from current-source evidence. “Implemented,” parse/generation success, a lower aggregate aesthetic score, one attractive screenshot, internal generator metrics, or stale pre-change renders are not sufficient evidence.

## 0. Scope, authority, and preservation

- [x] Confirm this is additive M2h2 composition hardening, not M3.
- [x] Confirm no corpus.v7 work.
- [x] Confirm no CP-SAT.
- [x] Confirm unchanged 210 × 140 mm spread gate.
- [x] Confirm unchanged 80 mm local-path gate.
- [x] Confirm unchanged 60 mm support/locality gate where applicable.
- [x] Confirm unchanged 250 mm canonical conductor-length gate.
- [x] Confirm ERC and independent emitted-artifact observation remain authoritative.
- [ ] Confirm DP1–DP4 topology/frozen expectations remain unchanged.
- [ ] Confirm all historical blind/evaluation and M2h2 finalization evidence is preserved.
- [x] Confirm `.local/` remains ignored.
- [x] Confirm `research/legacy_openclaw/` is not inspected or used.
- [x] Confirm locked KiCad 10.0.6 remains the governed real-tool version.
- [x] Confirm all GitHub/repository/CI reads and writes use Ralph Bridge.
- [x] Confirm direct-`master` exact-head compare-and-swap workflow.

## 1. Baseline freeze and composition characterization

- [ ] Record current `master` SHA and hashes of behavior-affecting M2 placement/routing/composition modules.
- [x] Record historical M2h2 final PASS authority without modifying it.
- [ ] Preserve/hash the final native-render archive used as the composition baseline.
- [x] Add a new human-composition baseline evidence root.
- [x] Define a versioned composition metric schema before behavior changes.
- [ ] Evaluate current final M2h2 renders using the initial independent observer.
- [ ] Produce a ranked per-case defect inventory.
- [x] Record `i4__b2_mixed` as a falsification seed.
  - [ ] output interfaces on visually inappropriate frontier are detected;
  - [ ] detached interface-to-owning-stage relationships are detected;
  - [ ] weak page utilization/edge bias is detected;
  - [ ] awkward branch/detour geometry is measured;
  - [ ] local label-mediated visual disconnection is measured where applicable.
- [ ] Identify at least one baseline example for each applicable archetype:
  - [ ] linear chain;
  - [ ] branch/fanout;
  - [ ] feedback;
  - [ ] repeated channels;
  - [ ] shared rail;
  - [ ] internal reference;
  - [ ] multi-output;
  - [ ] long-field text;
  - [ ] structural multi-band/one-band;
  - [ ] mixed interaction.
- [x] Confirm baseline failures do not alter historical M2h2 PASS status.

## 2. Independent semantic-flow observer

- [x] Implement independently authored semantic-flow graph reconstruction.
- [x] Distinguish signal, support, power, reference, return, and interface roles.
- [x] Derive directed primary-flow precedence independently of generator placement state.
- [x] Preserve sibling incomparability where topology does not order siblings.
- [x] Handle feedback cycles without incorrectly ordering feedback as forward flow.
- [x] Handle external terminal-backed signal sources.
- [x] Handle multiple final outputs.
- [x] Emit exact witnesses for stage-order violations.
- [x] Emit cumulative primary-flow reversal distance.
- [x] Add authored positive controls.
- [x] Add authored negative controls.
- [x] Add split/unsplit conductor metamorphic tests.
- [x] Add refdes/net rename metamorphic tests.
- [x] Add insertion/set-order metamorphic tests.

## 3. Functional-block and visual-ownership observer

- [x] Independently derive functional blocks from semantics/connectivity.
- [x] Derive visual ownership for feedback/support/package-local structures.
- [x] Derive shared ownership for supply/reference infrastructure.
- [x] Report functional-block dispersion.
- [x] Report functional-block fragmentation.
- [x] Report support-to-owner distance.
- [x] Report interface-to-owning-stage distance.
- [x] Report feedback-loop span and unrelated-block intrusion.
- [x] Add negative mutation: isolate one support component.
- [x] Add negative mutation: move feedback network away from owner.
- [x] Add negative mutation: detach output interface from final producer.
- [x] Verify observer does not consume production layout scores as proof.

## 4. Interface-side and signal-flow composition

- [x] Add generic semantic frontier model for external interfaces.
- [x] Prefer directed inputs on left frontier.
- [x] Prefer directed outputs on right frontier.
- [x] Place power-input interfaces with supply infrastructure rather than primary signal flow.
- [x] Exempt genuinely bidirectional/undirected interfaces using semantic evidence, not names.
- [x] Add deterministic penalties for unjustified interface-side violations.
- [x] Add deterministic penalties for primary stage-order inversions.
- [x] Add deterministic penalties for primary-flow backtracking distance.
- [x] Preserve valid incomparable sibling ordering freedom.
- [ ] Add targeted regression for `i4__b2_mixed`.
- [x] Add a renamed/permuted equivalent of the same semantic archetype to prove generic behavior.
- [x] Add negative mutation: final output connector moved to input frontier.
- [x] Verify no case/fixture/refdes/literal-net dispatch is introduced.

## 5. Functional grouping and locality composition

- [x] Add generic intra-block cohesion objective.
- [x] Add generic inter-block separation objective.
- [x] Keep local feedback structures with their owner.
- [x] Keep package-local support with its owner where hard constraints permit.
- [x] Preserve shared infrastructure as explicitly shared rather than arbitrarily attaching it to one block.
- [x] Prefer natural electrical ordering of passive series chains.
- [ ] Prevent isolated stage members connected only through distant labels when a legal local arrangement exists.
- [x] Record exact grouping penalties in candidate evidence.
- [x] Preserve existing 60 mm support/locality hard requirements.
- [x] Add small synthetic exhaustive grouping cases.
- [x] Add dominated-candidate oracle checks.

## 6. Branch, fanout, and feedback readability

- [x] Model branch points explicitly in composition evidence.
- [ ] Prefer visually identifiable branch origins.
- [x] Prefer consistent sibling-branch geometry.
- [ ] Penalize unnecessary branch crossings/detours.
- [x] Keep branch outputs attributable to source.
- [x] Model forward-path versus feedback-path roles.
- [x] Prefer compact feedback loops around owning stage.
- [ ] Penalize feedback routes through unrelated functional blocks.
- [x] Add branch/fanout positive and negative oracle cases.
- [x] Add feedback positive and negative oracle cases.
- [x] Add passive two-level fanout regression.
- [x] Add amplifier/filter feedback regression.

## 7. Power and reference composition

- [x] Add shared-rail/reference visual-coherence metrics.
- [x] Report supply/reference infrastructure dispersion.
- [x] Keep internal reference producer/support visually coherent.
- [x] Keep package-local decoupling/support local where semantics permit.
- [x] Prevent supply/reference infrastructure from dominating primary signal rows.
- [x] Preserve no-fake-external-reference behavior.
- [x] Add two-signal-chains/shared-rail regression.
- [x] Add V6-3 internal-reference regression.
- [x] Add multi-consumer supply/reference regression.
- [x] Add dual-regulator/mixed-load regression.
- [x] Verify all existing canonical graph and conductor-length gates remain unchanged.

## 8. Repeated-structure composition

- [x] Detect repeated semantic channels/stages generically.
- [x] Report row alignment variance.
- [x] Report column alignment variance.
- [x] Report corresponding-symbol displacement variance.
- [x] Report orientation variance.
- [x] Report pitch variance.
- [x] Prefer a consistent repeated-channel visual grammar.
- [x] Keep equivalent channel order deterministic.
- [x] Add declaration-order permutation tests.
- [x] Add mirrored naming/refdes metamorphic tests.
- [x] Add three-amplifier one-band regression.
- [ ] Add multi-band/repeated-channel regression.
- [ ] Freeze repeated-structure acceptance tolerances from general corpus evidence.

## 9. Page utilization and whitespace

- [x] Report content bounding-box width.
- [x] Report content bounding-box height.
- [x] Report content bounding-box area.
- [x] Report occupied-area ratio against 210 × 140 mm composition envelope.
- [x] Report content-centroid offset / edge bias.
- [x] Report horizontal whitespace imbalance.
- [x] Report vertical whitespace imbalance.
- [x] Report largest accidental internal empty corridor/void.
- [x] Define semantic complexity bands using block count, visible symbol count, and semantic edge count.
- [x] Exempt genuinely tiny probes from minimum utilization while still checking needless dispersion.
- [x] Freeze small/medium/dense complexity-aware utilization tolerances before final qualification.
- [x] Add negative mutation: shift a non-tiny circuit into a tiny upper-left patch.
- [x] Add negative mutation: introduce a large avoidable internal void.
- [x] Verify compactness pressure never violates hard spread/locality/readability gates.

## 10. Alignment, grid, and field composition

- [x] Add meaningful alignment-line detection.
- [ ] Prefer common baseline/centerline for sequential active stages where practical.
- [ ] Prefer role-consistent passive alignment.
- [ ] Align connectors with the signal rows they serve where practical.
- [ ] Align local support structures rather than leaving arbitrary offsets.
- [x] Preserve KiCad-compatible grid placement.
- [ ] Make reference/value orientation consistent for comparable roles.
- [x] Preserve long-field alternate-slot behavior.
- [x] Preserve existing field/body/wire/label independent checks.
- [x] Add field-alignment metrics.
- [x] Add long-field regression cases.
- [x] Add negative mutation: repeated component with inconsistent field orientation.

## 11. Routing clarity and label discipline

- [x] Report route bend count.
- [x] Define normalized bend excess against a legal semantic-local baseline.
- [x] Report canonical routed length.
- [x] Define normalized routed-length excess against a legal semantic-local baseline.
- [x] Report unrelated wire crossings.
- [x] Detect unnecessary U-shaped/rectangular detours.
- [x] Detect route excursions through unrelated blocks.
- [x] Report sibling-branch geometry inconsistency.
- [x] Detect label-mediated local disconnects.
- [ ] Prefer direct visible local connectivity when legal and clearer.
- [ ] Prefer labels for genuinely global/shared distribution when clearer.
- [x] Ensure label discipline never creates electrical ambiguity.
- [x] Add direct-vs-label synthetic oracle cases.
- [x] Add detour negative mutations.
- [x] Freeze routing-aesthetic tolerances before final qualification.

## 12. Production search/objective integration

- [x] Encode the lexicographic objective hierarchy:
  - [x] electrical correctness;
  - [x] existing hard M2h2 invariants;
  - [x] semantic readability;
  - [x] routing clarity;
  - [x] compactness/whitespace;
  - [x] aesthetic tie-breakers.
- [x] Ensure no weighted aggregate can trade away a higher-priority invariant.
- [x] Add candidate metrics for interface placement.
- [x] Add candidate metrics for stage ordering.
- [x] Add candidate metrics for grouping.
- [x] Add candidate metrics for repeated structures.
- [x] Add candidate metrics for whitespace/utilization.
- [x] Add candidate metrics for routing clarity.
- [ ] Search meaningful interface-frontier alternatives.
- [ ] Search meaningful semantic block-order alternatives.
- [ ] Search meaningful repeated-channel row/column alternatives.
- [ ] Search meaningful support-placement alternatives.
- [ ] Search meaningful field-slot alternatives.
- [ ] Search meaningful branch/route alternatives where already bounded.
- [x] Preserve exact attempt/budget counters.
- [x] Deduplicate repeated states.
- [x] Preserve best rejected candidate and full metric vector.
- [x] Make all tie-breakers deterministic.
- [x] Keep search bounded; no unbounded combinatorial expansion.

## 13. Tiny exhaustive placement and graph oracles

- [x] Implement independent tiny-grid exhaustive placement oracle.
- [x] Cover connector-side semantics.
- [x] Cover linear stage order.
- [x] Cover incomparable siblings.
- [x] Cover grouping.
- [x] Cover repeated alignment.
- [x] Cover whitespace/compactness.
- [x] Cover branch geometry where tractable.
- [x] Compare production result against non-dominated legal oracle candidates.
- [ ] Require evidence when bounded production search legitimately misses oracle optimum.
- [x] Implement independent graph-order oracle.
- [x] Falsify signal vs power/reference precedence separation.
- [x] Add exact-boundary tests for each frozen composition tolerance.
- [x] Add off-by-one-grid tests around each boundary.

## 14. Anti-overfitting and metamorphic audits

- [x] Extend literal anti-overfitting audit for composition production modules.
- [x] Extend structural anti-overfitting audit for composition production modules.
- [x] Reject fixture/case-ID control flow.
- [x] Reject qualification-group control flow.
- [x] Reject literal benchmark net-name control flow.
- [x] Reject refdes-specific control flow.
- [x] Reject exact-inventory special cases.
- [x] Reject topology-hash special cases.
- [x] Reject per-case coordinate maps.
- [x] Reject precomputed target-image dimensions/coordinates.
- [x] Scan data tables as well as obvious conditional branches.
- [x] Pass refdes-renaming metamorphics.
- [x] Pass net-renaming metamorphics.
- [x] Pass insertion-order metamorphics.
- [x] Pass equivalent-wire-segmentation metamorphics.
- [x] Pass repeated-channel declaration-order metamorphics.

## 15. Targeted composition regression suite

- [ ] `i4__b2_mixed` reads left-to-right with output interfaces associated with final outputs.
- [ ] `i4__b2_mixed` no longer exhibits pathological upper-left page packing for its complexity.
- [ ] `i4__b2_mixed` branch geometry has no avoidable dominant empty rectangle/detour.
- [ ] two-signal-chains/shared-rail remains electrically correct and becomes visually coherent.
- [ ] V6-3 remains electrically correct and its internal reference/support reads coherently.
- [ ] three-amplifier one-band remains electrically correct and repeated stages align consistently.
- [ ] passive two-level fanout remains traceable.
- [ ] amplifier-to-filter chain has obvious forward flow.
- [ ] feedback cases show local recognizable feedback.
- [ ] multi-output cases place final interfaces near final producers.
- [ ] long-field cases retain readability without unnecessary dispersion.
- [ ] timer/control cases retain readable control/feedback structure.
- [ ] package-shared cases retain package/support association.
- [ ] mixed interaction cases do not collapse into label-only disconnected visual islands.
- [ ] all targeted regressions pass native KiCad 10.0.6 generation/inspection.

## 16. Source stabilization

- [ ] Finish all behavior-affecting composition implementation changes.
- [ ] Run complete pytest.
- [ ] Run scoped Ruff lint.
- [ ] Run scoped Ruff format check.
- [ ] Run `git diff --check`.
- [ ] Run scoped whitespace checks.
- [ ] Run applicable link checks.
- [ ] Run historical preservation audit.
- [ ] Run literal anti-overfitting audit.
- [ ] Run structural anti-overfitting audit.
- [ ] Confirm CP-SAT remains absent.
- [ ] Run current-source V6-3 real-tool regression.
- [ ] Run current-source DP2 real-tool regression.
- [ ] Record final behavior-affecting source hashes.
- [ ] Freeze composition observer/oracle schema and hashes.
- [ ] Create fresh final human-composition qualification root.
- [ ] Declare later behavior-affecting source changes qualification-invalidating.

## 17. Fresh locked-KiCad qualification

- [ ] Run all 56 positive M2h2 base cases ×5 from stabilized final source.
- [ ] Require locked KiCad 10.0.6 for all governed runs.
- [ ] Require exact package/unit/pin identity.
- [ ] Require independent electrical partitions.
- [ ] Require zero unexpected ERC violations.
- [ ] Require serialized-scene verification.
- [ ] Require existing spread/locality/conductor-length gates.
- [ ] Require independent composition-observer pass.
- [ ] Require frozen composition metrics/tolerances.
- [ ] Require deterministic composition class across runs.
- [ ] Require deterministic metric vector after documented normalization.
- [ ] Confirm historical V3-8 remains rejected.
- [ ] Run all required I1–I6 interaction cases ×5.
- [ ] Run all required structural classes ×5.
- [ ] Run targeted composition regressions ×5 where reproducibility applies.
- [ ] Preserve all failures and best-candidate witnesses; do not overwrite evidence.

## 18. Native-render engineering inspection

- [ ] Generate final native KiCad renders from stabilized source.
- [ ] Archive hashes for every inspected render.
- [ ] Inspect at least one representative render for every distinct governed case.
- [ ] Explicitly inspect all mixed/high-density cases.
- [ ] Explicitly inspect all repeated-channel cases.
- [ ] Explicitly inspect all branch/fanout cases.
- [ ] Explicitly inspect all feedback cases.
- [ ] Explicitly inspect all shared-rail/reference cases.
- [ ] Explicitly inspect all long-field cases.
- [ ] Explicitly inspect all structural band-class cases.
- [ ] For every applicable inspected case, record:
  - [ ] primary signal entry is obvious;
  - [ ] primary signal progression is obvious;
  - [ ] final outputs are associated with final producers;
  - [ ] branch/fanout source attribution is obvious;
  - [ ] feedback is recognizable;
  - [ ] power/reference infrastructure is coherent/subordinate;
  - [ ] support ownership is obvious;
  - [ ] repeated structures are consistent;
  - [ ] compactness is appropriate;
  - [ ] whitespace is intentional;
  - [ ] fields/labels are aligned/readable;
  - [ ] no obvious unmodelled computer-generated layout defect remains.
- [ ] Record inspection as engineering/agent inspection, not user approval.
- [ ] Any hard visual defect falsifies the candidate and reopens affected qualification.

## 19. Comparative baseline closure

- [ ] Re-run composition observer over the original baseline corpus.
- [ ] Produce before/after per-case metric comparison.
- [ ] Show every baseline hard composition defect fixed or evidence-backed as unavoidable.
- [ ] Show `i4__b2_mixed` specifically improved without case-specific code.
- [ ] Show no material regression on previously strong cases.
- [ ] Show corpus-wide stage-order metrics improve or remain zero.
- [ ] Show corpus-wide interface-side metrics improve.
- [ ] Show functional-block fragmentation improves.
- [ ] Show page-utilization/edge-bias metrics improve for applicable complexity bands.
- [ ] Show routing-aesthetic metrics improve without violating hard routing gates.
- [ ] Show repeated-structure alignment improves or remains within frozen tolerance.
- [ ] Confirm aggregate metrics are not used to hide individual hard defects.

## 20. Final reproducibility and audit closure

- [ ] Verify five-run deterministic project bytes where already governed.
- [ ] Verify deterministic semantic composition class.
- [ ] Verify deterministic normalized native-render geometry.
- [ ] Verify deterministic observer metric vectors.
- [ ] Verify deterministic candidate/tie-break decisions.
- [ ] Run complete final pytest.
- [ ] Run final Ruff lint.
- [ ] Run final Ruff format check.
- [ ] Run final `git diff --check`.
- [ ] Run final whitespace checks.
- [ ] Run final link checks as applicable.
- [ ] Run final historical-preservation audit.
- [ ] Run final literal anti-overfitting audit.
- [ ] Run final structural anti-overfitting audit.
- [ ] Confirm CP-SAT absent.
- [ ] Reconfirm unchanged 210 × 140 / 80 / 60 / 250 mm hard gates.
- [ ] Reconfirm ERC/independent observer not weakened.
- [ ] Reconfirm DP1–DP4 and historical evidence unchanged.

## 21. Final reconciliation and PASS

- [ ] Create final closure record binding exact production source, qualification source, observer/oracle hashes, toolchain, and evidence roots.
- [ ] Record final base-case count and five-run outcomes.
- [ ] Record final interaction-case count and five-run outcomes.
- [ ] Record final structural-class count and five-run outcomes.
- [ ] Record final targeted-composition regression outcomes.
- [ ] Record worst composition metrics and exact witnesses.
- [ ] Record before/after baseline comparison.
- [ ] Record native-render inspection totals.
- [ ] Update `fixtures/m2h2/STATUS.md` only when final material status changes.
- [ ] Reconcile every checkbox in this TODO from exact current-source evidence.
- [ ] Confirm no unchecked item remains.
- [ ] Mark this TODO **COMPLETE / PASS**.
- [ ] Stop; do not create corpus.v7 and do not begin M3.

## Completion rule

Do not finish merely because placement “looks better,” a handful of screenshots look good, aggregate metrics improve, or the targeted `i4__b2_mixed` regression is repaired.

Completion requires:

- all existing M2h2 correctness guarantees preserved;
- generic semantic composition behavior;
- independent observer and oracle evidence;
- anti-overfitting/metamorphic evidence;
- full current-source locked-KiCad qualification;
- reproducibility;
- native-render engineering inspection;
- complete audits;
- every checkbox above checked with exact evidence.

Until then, status remains **INCOMPLETE**.
