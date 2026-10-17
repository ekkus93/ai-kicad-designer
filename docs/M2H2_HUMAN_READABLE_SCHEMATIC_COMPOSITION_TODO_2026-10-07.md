# M2h2 Human-Readable Schematic Composition TODO — 2026-10-07

**2026-10-17 exact-source I1–I5 qualifications PASS; I6 and final acceptance OPEN:** On production source `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`, I1 is **10/10**, I2 **9/9**, I3 **14/14**, I4 **9/9**, and I5 **9/9** accepted and reproducible ×5 in [Final Interactions run 39014637051](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637051). I reviewed the run-1 native SVG for every I3 case and recorded exact SVG SHA-256s, observed metrics, and case-level concerns in [`M2H2_I3_NATIVE_RENDER_INSPECTION_ee4c37a.md`](reviews/M2H2_I3_NATIVE_RENDER_INSPECTION_ee4c37a.md). I also inspected I4 `b2_mixed`; its left-to-right flow and right-side outputs are clear with no detached label-only connection, but it uses 21.7675% of the A4 page. Its SVG hash and exact metrics are in [`M2H2_I4_B2_MIXED_NATIVE_RENDER_INSPECTION_ee4c37a.md`](reviews/M2H2_I4_B2_MIXED_NATIVE_RENDER_INSPECTION_ee4c37a.md). I3 review findings include low page use in several simple/timer cases, uneven three-channel placement in some cases, and detached/label-mediated interface associations; the three-amplifier one-band case has clear repeated signal stages. These are engineering observations only, not visual acceptance. I6 is running; **3/21** cases are accepted and reproducible. The exact-source 56-base×5/V3-8-negative qualification [run 39014637046](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637046) is queued. The 90-case comparison, 137-case×5 normalized native-render inventory, remaining render inspection, and sections 15–21 final closure remain OPEN. Do not weaken frozen gates or infer aesthetic acceptance from qualification.

**2026-10-16 current-source exact-head validation PASSED; M2h2 remains INCOMPLETE:** The connector text-slot regression fix is committed at `0557c8c979a6334b24c91f220a739b123b72fc80`. Exact-head [Fast Validation 38885778613](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38885778613) passed all three jobs, including full pytest, locked V6-3/DP2 regressions, targeted connector-label and selected-triple five-run regressions, whole-band five-run regression, fresh-qualification regression builds, Ruff/static audits and hosted contracts. [Development Composition Probe 38885778567](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38885778567) and [locked-toolchain diagnostic 38885778540](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38885778540) also passed. Committed locked KiCad 10.0.6 development evidence records V6-3, DP2 and I4 B2 mixed accepted; DP2 VREF is 247.65 mm with one component and nine terminals. GitHub Actions artifact upload is unavailable because the repository storage quota is exhausted; detailed one-run evidence is preserved in `fixtures/m2h2/development_checks/connector_slot_alternatives_2d7eacc9/`. These results do not establish the 56-base×5/V3-8-negative, I1–I6×5, nine structural-class×5, independent 90-case comparison, 137-case×5 normalized render inventory, or case-by-case engineering inspection. Sections 15–21 and final acceptance remain open; do not weaken frozen gates or claim M2h2 complete.

**Historical 2026-10-16 review-branch checkpoint — branch pytest 874/875; later merged into master at `2d7eacc9`:** Behavior/regression source `0ac53915` on branch `review/m2h2-routing-visual-review-2026-10-15` adds three generic rules: single-port connector leads stay straight with long labels on droppable orthogonal label stubs (connector envelopes byte-identical to the prior revision); composition prunes a dropped label's stub and every other dead-end spur plus its junction marker, which repairs the ERC "unconnected wire endpoint" regression that label omission had introduced on 15 `test_m2b`/`test_m2c1` real builds; a fanout column stacks a reference-free sibling opposite the column's reference escapes with the signal row aligned to the reference-bearing siblings; and an `interface-frontier-combined` seed moves inputs and outputs together. I4 B2 mixed now routes both outputs with zero interface enclosures, zero crossings, RETURN 165.10 mm (was 203.20 mm), total 443.23 mm; the four review artifacts under `docs/reviews/m2h2-routing-review-2026-10-15/` were rebuilt with locked KiCad 10.0.6 at zero ERC violations each. Local full pytest: 874 passed, 1 failed — `test_measured_row_compaction_and_stagger_are_legal_structural_classes` (VMINUS `ROUTE_LENGTH_LOWER_BOUND`), which also failed on the unmodified branch head `c1bc5256`; that was an open review-branch regression at the time. The source-bound master suite now passes 875/875. Three frontier test expectations were updated for the branch's outer-edge output rule (one output-frontier candidate plus an optional staggered variant; the combined candidate is the one that shows both roles on their own sides). No locked five-run suites, independent 90-case comparison, native render inventory, or human visual review have been run for this source; sections 15–21, frozen tolerances, baselines and observers are unchanged.

**2026-10-14 generic vertical-interior distribution trunk — EXACT-SOURCE FAST PASS; three five-run qualification suites and probe REQUESTED (not acceptance):** Behavior/regression source `2c029336e135856419cde3c2ea0055e0c7701aff` searches one additional seed-connected legal vertical interior trunk, including a deterministic nearby clear lane when the vertical median is obstructed, within the existing eight-plan cap. New controls cover median availability, obstacle-checked fallback and cap retention. The old exact strategy-set contract was reconciled at that source without weakening any routing or observer gate. Exact-source [Fast Validation 38679796266](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38679796266) **PASSED all three jobs** (complete locked-runner pytest/current-source regressions, hosted contracts, Ruff/static); [pinned KiCad 10.0.6 diagnostic 38679796161](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38679796161) **PASSED**. This documentation-only descendant requests fresh 56-base×5/V3-8-negative, I1–I6×5, nine structural classes×5, and the generic composition probe for the unchanged production behavior. If all qualify, run the independent full 90-case historical comparison and 137-case×5 normalized native render inventory against one exact preserved evidence root. The latest independent comparison still **FAILED five frozen criteria**, and engineering visual inspection plus sections 15–21 remain OPEN. Do not infer V6-3 hard-defect closure or alter frozen baselines, observers, tolerances, or qualification toolchain from a passing fast gate.

**2026-10-14 typed distributive/feedback inferred-flow exclusions — FAST PASS; fresh five-run qualifications LAUNCHED (not acceptance):** Production/regression source `ff27d83239397ad5edcc447f575eb41f0e866005` repairs false forward-flow inference for distributive, feedback, power and support nets while preserving conservative unique passive-interface inference in lightweight test fixtures. Earlier `0fec8366` Fast Validation 38664220613 found three fixture AttributeErrors and source Ruff formatting, fixed in `26dd7bc9`; test Ruff formatting was then fixed at `ff27d83239397ad5edcc447f575eb41f0e866005`. Exact-source [Fast Validation 38671457275](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38671457275) **PASSED all three jobs**, including complete locked-KiCad pytest/current-source regressions, hosted contract tests and static/Ruff; [pinned toolchain diagnostic 38671457325](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38671457325) **PASSED**. This documentation-only descendant requests full locked KiCad 10.0.6 56-base×5/V3-8-negative, I1–I6×5, nine structural classes×5 and the generic composition probe from exact source `ff27d83239397ad5edcc447f575eb41f0e866005`. Await independent source-matched 90-case frozen historical comparison and 137-case×5 normalized native render inventory **only if all suites pass**. The last completed comparison FAILED five frozen criteria; visual/native engineering inspection and TODO sections 15–21 remain OPEN. Do not weaken thresholds, historical evidence, oracle/observer, or treat qualification as visual acceptance.


**2026-10-14 exact-source independent comparison RESULT — FAIL (five frozen criteria); normalized native inventory PASS:** The 90-case preserved-baseline [comparative audit 38658379513](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38658379513) independently evaluated the qualified `ab4b7d638f607af65e675388219fada2c831724a` evidence root and **FAILED** `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Historical→fresh totals: stage inversions **1→0**, interface-side violations **77→38**, functional fragmentation **14743.4342→14583.4162 mm**, edge-biased cases **64→54**, U-detours **691→880**, branch inconsistency **1529.08→1771.65 mm**. Specific newly worse hard witnesses include shared-rail local-label disconnections **1→2**, V4-7 interface violations **0→1**, and V6-3 interface violations **0→1**; `i4__b2_mixed` still has page edge bias and U-detours **2→7** despite output-interface improvements. The exact-source [persisted native-render inventory 38658379597](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38658379597) **PASSED** 137/137 cases, 685/685 native SVGs, all 137 normalized-geometry hashes equal across five runs (raw SVG hashes differ from volatile content); this does **not** establish visual acceptance. Prioritize source-neutral candidate generation and legal routing/selection fixes for V6-3, V4-7, shared-rail labels, repeated structure and branch/detour geometry, followed by fresh three-suite qualification and independent comparison. Keep frozen tolerances, historical evidence, observer/oracle, and sections 15–21 checkboxes unchanged; case-by-case native engineering inspection remains OPEN.


**2026-10-14 exact-source qualification complete; independent comparative audit and render inventory REQUESTED (not yet accepted):** Source `ab4b7d638f607af65e675388219fada2c831724a` passed the locked KiCad 10.0.6 56-base×5/V3-8-negative qualification (run 38653534588), I1–I6×5 interactions (38653534695), nine structural classes×5 (38653534661), pinned toolchain (38653534601), Fast Validation (38653534547), generic composition probe (38653534545), and source-matched base/structural native-render transfers (38656244884, 38654039663). All evidence is bound to the preserved `$HOME/m2h2-evidence/ab4b7d638f607af65e675388219fada2c831724a/` source root. This documentation-only descendant triggers the independent complete 90-case preserved-baseline comparison and 137-case×5 normalized native-render inventory against that exact root; outcomes are **PENDING** and may fail. The preceding independent comparison failed five frozen human-composition criteria; no frozen tolerance, historical baseline, observer/oracle, production behavior, or sections 15–21 acceptance checkbox changes. Engineering inspection remains OPEN.


**2026-10-14 bounded two-interior-corridor production fix — EXACT-SOURCE FAST PASS; three locked KiCad 10.0.6 five-run suites and generic probe REQUESTED (not yet qualified):** Source and regression commit `3fa6eafe8b97b95ff0787a2217dacab14b3d4b4c` keeps two distinct seed-connected legal interior trunk candidates within the existing eight-plan cap, including deterministic blocked-median clear-lane proof. The dependent route-tree return, pre-existing strategy-set contract and Ruff formatting were corrected before qualification. Exact-source [Fast Validation 38652437889](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38652437889) **PASSED all three jobs** (locked full pytest/current-source regressions, hosted contract pytest, static/Ruff/format checks); [pinned KiCad 10.0.6 diagnostic 38652437837](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38652437837) **PASSED**. This documentation-only descendant requests separate full 56-base×5/V3-8-negative, I1–I6×5, and nine structural-class×5 qualifications and a generic composition probe against its exact commit. If all three qualify, independently compare the exact persisted source-root to the unchanged frozen 90-case baseline, run the 137-case×5 normalized native-render inventory, and inspect engineering renders. Five historical comparative criteria still FAIL on the preceding qualified source, and sections 15–21 remain OPEN; do not alter frozen thresholds, historical evidence or observers or claim visual acceptance based on this fast gate.

**2026-10-14 blocked-median clear-lane regression repaired; exact-head Fast Validation PASS; three full locked-KiCad suites REQUESTED (not yet qualified):** `24c3520090ceb023fdcc8a3ef2554ef39dd78bc6` corrects the regression fixture's unrelated obstacle to actually cover the escaped-gateway median trunk at `-PITCH` and verifies the adjacent legal interior trunk at `0`, without modifying production routing behavior. Exact-source [Fast Validation 38532329003](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38532329003) **PASSED all three jobs**, including complete pytest, current-source V6-3/DP2 and five-run regressions, hosted contracts, Ruff/static and whitespace. [Pinned KiCad 10.0.6 diagnostic 38532329091](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38532329091) **PASSED**. This documentation-only descendant requests fresh 56-base×5/V3-8-negative, I1–I6×5, and nine structural classes×5 locked-runner qualification plus the generic composition development probe. Once the three suites pass, independently audit the exact new evidence root against the frozen 90-case historical baseline and normalized 137-case native-render inventory. The latest completed comparative audit still FAILS five frozen criteria; sections 15–21 remain unchecked. No frozen tolerance, historical baseline, or composition observer has changed.

**Status:** IN PROGRESS / INCOMPLETE

**2026-10-17 exact-source structural qualification PASS; final acceptance remains OPEN:** Structural Qualification [39014637072](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637072) passed all nine measured I3 structural classes ×5 on exact production source `ee4c37a711b1107085acaed5e58bf3e7ae78bd50`; all nine accepted, reproducible reports are persisted at `$HOME/m2h2-evidence/ee4c37a711b1107085acaed5e58bf3e7ae78bd50/structural/`. Engineering inspection of all nine source-matched native SVGs and their SHA-256 hashes is recorded in `docs/reviews/M2H2_STRUCTURAL_NATIVE_RENDER_INSPECTION_ee4c37a.md`. The inspection flags material upper-left page-use concerns in `a0_interleaved`, `a0_multiple`, and `a1_interleaved`; these renders are not aesthetic acceptance. Exact-source I1–I6 qualification [39014637051](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637051) remains in progress; I1 completed **10/10** accepted, reproducible cases and I2 completed **9/9**. Two I1 renders (`d1_b1`, `d3_b2`) and two I2 renders (`external_2`, `internal_2`) were inspected with their SVG hashes in `docs/reviews/M2H2_I1_NATIVE_RENDER_INSPECTION_ee4c37a.md` and `docs/reviews/M2H2_I2_NATIVE_RENDER_INSPECTION_ee4c37a.md`; low page use is recorded as an open complexity-banded concern. I3 is now running. Exact-source 56-base×5 qualification [39014637046](https://github.com/ekkus93/ai-kicad-designer/actions/runs/39014637046) remains queued. The independent 90-case comparison, 137-case×5 native-render inventory, full engineering inspection, and sections 15–21 final closure remain OPEN. Do not weaken thresholds or infer visual acceptance from structural/electrical pass.

**2026-10-14 exact-head three-suite qualification PASS; independent comparison and render inventory REQUESTED (not yet accepted):** Current unchanged behavior/qualification source `e0da993190fc51a1ad1249c7e9a22855319c9172` passed locked KiCad 10.0.6 five-run base 56/V3-8-negative ([38602260592](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602260592)), I1–I6 ([38602260383](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602260383)), and nine structural classes ([38602260751](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602260751)), plus exact-head Fast Validation ([38602260439](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602260439)), locked toolchain identity ([38602260921](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602260921)), and base/structural native-render transfers ([38605333444](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38605333444), [38602803801](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38602803801)). This documentation-only descendant requests independent full 90-case preserved-baseline artifact comparison and 137-case ×5 normalized native render inventory against exact persisted evidence root `$HOME/m2h2-evidence/e0da993190fc51a1ad1249c7e9a22855319c9172/`. Those audit results are PENDING; prior independent comparison still FAILS five frozen criteria, and case-by-case engineering inspection and sections 15–21 remain OPEN. No frozen tolerances, baseline evidence, observer/oracle or production behavior is modified.

**2026-10-13 generic route geometry balance — EXACT-SOURCE FAST QUALIFICATION PASS; full five-run suites LAUNCHED:** Production ranking source `4061a9e4384fa28a42313c792adeb337265dfc00` and Ruff-formatted test descendant `4d64b42ed26b29638df39ca4ab2faec73299b75c` now compare routed union length plus a generic eight-grid-pitch-per-bend cost after higher-priority semantic obligations and backtracking, rather than permitting one saved bend to dominate arbitrary conductor detours. New regression tests verify both a gross detour rejection and retention of low-turn/backtracking priorities. [Exact-head Fast Validation 38460169304](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38460169304) **PASSED all three jobs**, [locked KiCad 10.0.6 identity 38460169320](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38460169320) **PASSED**, and [development probe 38460169403](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38460169403) **PASSED**. V4-7 now selects equally flow/side-correct seed 2/round 0, saving **26.67 mm** routed union (697.23→670.56 mm) at one additional bend (19→20). V6-3 still has only one proved candidate and a remaining wrong-side interface violation; `i4__b2_mixed` still selects seed 1/round 0. This is a measurable generic candidate-selection improvement, **not** evidence of comparative or visual acceptance. This documentation-only commit requests new full base 56×5/V3-8, I1–I6×5, and structural×5 locked-KiCad qualification for unchanged exact production behavior. Re-audit the frozen 90-case historical comparison and native render inventory only after all three qualify. Sections 15–21 remain unchecked.

**2026-10-13 exact-source independent-output ranking audit RESULT — FAIL (five frozen criteria); normalized render inventory PASS; diagnostic expansion qualified:** Production/qualification source `0ae9c58fa79f018c182bccce1c0de0e72fce7906` passed locked-KiCad base 56×5/V3-8 negative [38449647614](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647614), I1–I6×5 [38449647145](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647145), structural×5 [38449647157](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647157), Fast Validation [38449647244](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647244), KiCad toolchain [38449647301](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647301), development probe [38449647351](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38449647351), and base/structural native render transfers [38453596594](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38453596594), [38450109039](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38450109039). Documentation audit trigger `2319230a7612cde03182f0da0f23687e417f2555` bound its subject to exact `0ae9c58`; the independent [90-case preserved-baseline comparison 38457583899](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38457583899) **FAILED** `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Historical→fresh totals: stage inversions 1→0, interface-side violations 77→44, fragmentation 14743.4342→14677.3962 mm, edge-biased cases 64→55, U-detours **691→865**, branch inconsistency **1529.08→1767.84 mm**. Mixed-case hard defects 4→1, page edge bias remains true, U-detours 2→7, fragmentation 73.6602→99.0602 mm. The exact-source [137-case×5 normalized native render inventory 38457584235](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38457584235) **PASSED**, not aesthetic acceptance. Generic development probe was expanded on `master` at `e83c1fc882fefc395cccb5d846e5b00b7c40d410` to include V4-3, V4-7 and V6-3; the [expanded probe 38458588420](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38458588420) **PASSED**, reporting V4-7 selected seed 2/round 1 with 697.23 mm routed union vs equal-flow alternative seed 2/round 0 at 670.56 mm, whose fewer-priority one-bend advantage defeats 26.67 mm of union reduction, and V6-3 with no equally-flow-correct reported alternative. These are **diagnostic facts, not demonstrated production fixes**. Prioritize a generic source-neutral legal-candidate generation/routing improvement, especially V6-3, shared-rail hard regressions, repeated structures, V4-7 and mixed dual outputs; do not alter thresholds, historical baselines, pinned KiCad identity or section 15–21 acceptance checkboxes until independently proved.


**2026-10-13 qualified-source independent visual audit RESULT — FAIL; native engineering review PARTIAL:** Exact-source 54eeb3c66112448c46eaaea9bd68ec0bd8941b35 [full 90-case comparative audit 38379445241](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379445241) completed and **FAILED five frozen criteria** (hard-defect closure, individual hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and `i4_specific_improvement`). The [137-case five-run normalized native inventory 38379445528](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379445528) **PASSED**; one source-matched `i4__b2_mixed` native SVG preview was independently inspected ([transfer 38379954922](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38379954922)). The generic development probe 38373962147 shows selected seed 4 vs proved seed 1: lower row drift 68→28 and shorter union 335.28→287.02 mm come with worse frontier 46→61 and backtracking 78→88. See `docs/M2H2_NATIVE_ENGINEERING_REVIEW_2026-10-13.md` and the separate mixed-case inspection record. Candidate tradeoff diagnostics are **not** a production selection change or aesthetic acceptance. Keep sections 15–21 open, thresholds frozen, and all-case native inspection pending.

**2026-10-13 exact-source five-run locked-KiCad qualification PASS / independent visual audit LAUNCH:** Source `54eeb3c66112448c46eaaea9bd68ec0bd8941b35` passed the full [56 base positives ×5 and V3-8-negative 38373962344](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962344), [I1–I6 interactions ×5 38373962280](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962280), [structural classes ×5 38373962437](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962437), [Fast Validation 38373962143](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962143), [KiCad 10.0.6 pinned toolchain 38373962397](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962397), and [generic development probe 38373962147](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38373962147). Exact-head qualifications are separate from aesthetic acceptance. This documentation-only descendant requests the independent full 90-case historical comparative artifact audit and the 137-case five-run normalized native-render inventory from preserved source-matched evidence root `$HOME/m2h2-evidence/54eeb3c66112448c46eaaea9bd68ec0bd8941b35/` using the repository's validated push markers and explicit source binding. Neither audit is claimed passed at launch. Previous qualified source audit 38344818593 still FAILS the five frozen criteria: hard-defect closure, individual nonworsening, routing aesthetics, repeated-structure tolerance and `i4__b2_mixed` improvement. Do not alter historical evidence or thresholds or check final sections 15–21 without new source-matched independent evidence and engineering visual inspection.

**2026-10-13 full source-matched locked-KiCad requalification LAUNCH (not acceptance):** Latest `master` documentation-only descendant of behavior source `bab8a5f033b5ada900389def1d3642c987a30ba8` passed [Fast Validation 38371452448](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38371452448) and [locked toolchain diagnostic 38371452273](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38371452273), all exact-head. The earlier `bab8a5f` fix is not full native visual acceptance. This checkpoint explicitly launches all three *separate* locked-runner five-run qualification workflows via their repository-supported commit-message markers: 56 base positives/V3-8 negative, I1–I6, and nine structural classes, plus the generic development composition probe. Their results are **PENDING**; no result is pre-claimed. If all three pass, run the independent full-90-case frozen historical comparison and 137-case normalized native render inventory against the exact new qualification SHA, followed by engineering visual inspection. The prior five frozen comparative failures remain unresolved, sections 15–21 remain unchecked, and no frozen threshold or historical artifact changes are authorized.

**2026-10-13 uniquely inferred passive-terminal repeated-stage context FIX / FAST-VALIDATION PASS (not composition acceptance):** Behavior and regression source `bab8a5f033b5ada900389def1d3642c987a30ba8` adds uniquely inferred passive-terminal signal links to repeated-stage structural signatures, deduplicating authored signal/branch and inferred relations, preserving ambiguous shared passive net exemptions, and testing matched/unmatched output interfaces, net renames, and declaration order. Exact-head [Fast Validation 38370298212](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38370298212) **PASSED all three jobs**, including complete pytest, locked real-tool V6-3/DP2, connector-label/selected-triple and whole-band five-run regressions, fresh-qualification regression builds, hosted contracts, Ruff/static/format/diff. [Locked KiCad toolchain diagnostic 38370298298](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38370298298) **PASSED**. This proves the targeted source/regression gates only. Full current-source base 56×5/V3-8-negative, I1–I6×5, structural×5, independent 90-case historical comparison, native-render inventory, engineering case-by-case visual inspection, and sections 15–21 final reconciliation are still **OPEN**: all corresponding push workflows were skipped, and the only completed independent audit (38344818593, older source) failed five frozen criteria. Ralph Bridge validation dispatch requires a configured, approved profile; attempted `m2h2_base` was rejected by bridge. No frozen tolerance, protected historical evidence, or acceptance checkbox was changed.

**2026-10-13 generic junction and repeated-stage context checkpoint (NOT visual acceptance):** The direct-`master` behavior change `7a0756f8c11a7e7d25952401c10be8e48c3c18d4` excludes fanout and convergence junctions from mandatory serial-stage row alignment, even for explicitly typed signal stages, with declaration-order invariant negative controls; full restored/format-corrected regression source `eaa4ee91152d5d65faa6665ab039b7693db46e1a` passed all three [Fast Validation jobs 38364251095](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38364251095). Follow-on behavior change `5169e32b8d9b597b1f1a7d849ad536edd34ed8b3` normalizes explicit signal/branch and inferred precedence links in repeated-stage semantic signatures, deduplicates equivalent annotations, and groups corresponding stages of precedence-only parallel chains without falsely aligning different stage depths. Format-corrected exact source `1de9d384b02e1b95e3e57c2c5dfc54587ef9e84d` passed all three [Fast Validation jobs 38365495815](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38365495815) and the [locked KiCad toolchain diagnostic 38365495945](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38365495945). These source tests are NOT five-run base/I1–I6/structural qualification and NOT independent native-render comparison. Latest complete 90-case historical audit [38344818593](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38344818593) still FAILS five frozen comparative criteria: hard-defect closure, per-case nonworsening, routing aesthetics, repeated-structure tolerance, and `i4__b2_mixed` improvement. Do not weaken thresholds, modify baseline artifacts, or check sections 15–21. Ralph Bridge attempts to dispatch a requested `m2h2_base` validation profile and run a `pytest` local profile returned `INVALID_ARGUMENT`; the available allowed profile names are not exposed by these errors. Exact-source three-suite dispatch, independent historical comparison, native-render inventory, engineering inspection, and final closure remain OPEN pending approved validation access and affirmative evidence.

**2026-10-13 inferred serial-stage row alignment qualification launch:** Generic placement-ranking source `83b98950a32409b901c849b2306b29575546df91` permits inferred one-in/one-out passive signal stages to share a row while excluding fanout, convergence, interfaces, and single-ended stages; regression source `6157ec5f2d9820a0c08e9b9828f24472351f2cb0` adds precedence-order, row-drift, fanout and single-ended controls; formatting-only descendant `b4980d2b1a57dc3bcfdbba4592747160a6ca785e` passed all three exact-head [Fast Validation jobs (38351990625)](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38351990625) and [locked KiCad 10.0.6 diagnostic (38351990680)](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38351990680). This documentation-only commit launches new full locked-KiCad five-run base/V3-8-negative, I1–I6, and structural qualification for the unchanged production behavior. The latest independent 90-case comparison still FAILS five frozen human-composition criteria; full current-source comparison, native-render engineering inspection, and sections 15–21 remain OPEN. No frozen tolerances, historical evidence, or visual-acceptance checkboxes change.

**2026-10-13 exact-source qualification PASS; independent visual audit launched:** Source `f909475058724c190dce26a66e0943866d72f62f` passed all three locked KiCad 10.0.6 five-run suites: [56-base/V3-8-negative 38341411894](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341411894), [I1–I6 38341411990](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341411990), and [structural 38341411880](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341411880), plus [pinned-toolchain identity 38341411989](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341411989), [structural native-render audit 38341672220](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341672220), and [development composition probe 38341411972](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341411972). At this checkpoint [Fast Validation 38341412097](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38341412097) remains in progress and [base native-render audit 38343164560](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38343164560) is queued; do not claim those passed. This documentation-only descendant requests an independent full-90-case historical comparative artifact audit and normalized 137-case five-run native-render inventory against the exact persisted qualification root `$HOME/m2h2-evidence/f909475058724c190dce26a66e0943866d72f62f/`. The latest prior independent comparison still FAILED five frozen criteria: hard-defect baseline closure, per-case hard-defect nonworsening, routing aesthetics, repeated-structure tolerance, and `i4__b2_mixed` improvement. Source-matched audit results and case-by-case engineering inspection remain required; sections 15–21 stay UNCHECKED, thresholds unchanged, and this is NOT overall PASS.

**2026-10-12 source-matched route-return ranking qualification launch:** Generic behavior source `71dde0da8741e39bd779cb01219a556c4129cdd6` moves independently measured return-leg/backtracking preference ahead of soft directed-interface row/support-axis refinements, after signal order, interface-side, frontier, feedback/support, branch, repetition, and fragmentation obligations. Synthetic regressions prove a short detour may win over minor connector-row drift but cannot buy a wrong-side/reversed signal flow. Exact-source [Fast Validation 38340647721](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38340647721) PASSED all three hosted, locked-runner and static/Ruff jobs; [locked toolchain 38340647701](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38340647701) PASSED. The corrected self-hosted [development probe 38340326613](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38340326613) succeeded and exposed a mixed-output candidate that traded connector row drift 55→68 grid units against reduced route backtracking 79→78, routing union 350.52→335.28 mm, and page edge bias 67→1. That is prequalification candidate evidence, NOT a native aesthetic acceptance result. Request five-run base/V3-8-negative, I1–I6, structural and a current-source development probe. The five frozen failing visual/comparative criteria, final native engineering inspection, and sections 15–21 remain unchecked until independent source-matched audit proves closure; frozen thresholds and historical evidence are unchanged.

**2026-10-12 source-matched comparison FAIL / fragmentation improvement:** Independent [historical artifact audit 38325045279](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38325045279) evaluated the complete 90-case preserved baseline against qualified source `de0d651396d6cb5e56d223750ffdd8ea7c7f42e1`. **Five frozen criteria still FAIL**: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. **Functional fragmentation now PASSES** its corpus-wide nonworsening criterion, 14743.4342→14677.3961 mm. Other historical→fresh totals: stage inversions 1→0, interface-side violations 77→44, edge-biased cases 64→55, low-utilization cases 2→0; routing remains worse, U-detours 691→870 and branch inconsistency 1529.08→1746.25 mm. Independent [normalized native render inventory 38325045318](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38325045318) PASSED: 137/137 cases, 685/685 native SVGs, identical normalized geometry in all five runs (raw SVG bytes vary from volatile titles). The new generic development composition probe is requested to diagnose hard per-case regressions, detours, branch inconsistency, and `i4__b2_mixed` without special-casing fixtures or changing frozen thresholds. The five failing criteria and sections 15–21 final acceptance remain UNCHECKED; this is NOT overall PASS.

**2026-10-12 exact-source completed qualification and independent audit launch:** Exact `master` source `de0d651396d6cb5e56d223750ffdd8ea7c7f42e1` passed all three locked-KiCad 10.0.6 five-run suites: 56 base positives plus V3-8 negative ([38320102874](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38320102874)), I1–I6 interactions ([38320102893](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38320102893)), and nine structural classes ([38320102802](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38320102802)). Exact-head Fast Validation ([38320102829](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38320102829)), locked toolchain ([38320103150](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38320103150)), base native-render transfer ([38323794358](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38323794358)), and structural native-render transfer ([38322240721](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38322240721)) also passed. This documentation-only descendant requests the **independent historical 90-case comparative artifact audit** and **normalized five-run native-render inventory** against the preserved exact-source root `$HOME/m2h2-evidence/de0d651396d6cb5e56d223750ffdd8ea7c7f42e1/`. The six previously failing frozen comparative visual criteria, engineering visual inspection, final source freeze, and sections 15–21 acceptance remain OPEN until independently proven. Do not relax historical tolerances, alter historical evidence, or infer aesthetic PASS from electrical/structural qualification.

**2026-10-12 exact-source three-suite qualification relaunch:** Production behavior and regression source `3d780313103ecb70c8107dc20aae3dd0257c129d` passed all three jobs of [Fast Validation 38319282152](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38319282152): locked KiCad 10.0.6 full pytest and current-source real-tool regressions, hosted contracts, and Ruff/static/whitespace. The immediately preceding failed run 38318418927 was a test-only Ruff formatting issue corrected at this source. This **documentation-only** descendant requests fresh exact-commit locked-KiCad five-run base 56/V3-8 negative, I1–I6 interactions, and nine structural classes. It does not claim visual acceptance: the six frozen historical-comparative gates, source-matched independent native-render engineering inspection, and sections 15–21 remain open. Do not weaken thresholds or mark any acceptance checkbox until qualified source-matched evidence proves it.

**2026-10-12 ranking priority qualification launch:** Exact behavior source `0309592eb2cb3d93303ac6ef9cbc257aad641293` demotes nearest directed-interface owner proximity from hard semantic-side priority to soft local signal-neighbor preference, preserving wrong-side interface defect priority. Synthetic tests cover fanout, directed input/output, exemptions and fragmentation priority. Earlier behavior source `7ae73b8d275c67316bec2c6c9e360e1608e9e21f` passed locked-runner pytest and hosted contracts but failed Ruff formatting, corrected without behavior changes in the exact source. Request full five-run base, I1-I6, and structural locked-KiCad qualification. The latest prior independent comparative audit still fails six frozen visual gates, and engineering inspection, sections 15-21, and final acceptance remain open. No thresholds or historical baselines change.

**2026-10-12 independently audited five-run exact-source closure launch:** Latest `master` `df4246b0edee10bb738eaf5f1e15756ae2ff061f` has passed locked KiCad 10.0.6 five-run base 56 positives + V3-8 negative ([38307071925](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38307071925)), I1-I6 ([38307071959](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38307071959)), structural ([38307071976](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38307071976)), all three Fast Validation jobs ([38307071992](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38307071992)), pinned toolchain ([38307071907](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38307071907)), and source-matched base and structural render transfers ([38308986205](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38308986205), [38311572471](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38311572471)). This documentation-only descendant triggers the independent 90-case historical comparative artifact audit and five-run normalized native-render inventory against **exact** persisted qualification root `$HOME/m2h2-evidence/df4246b0edee10bb738eaf5f1e15756ae2ff061f/`. Prior six frozen failing comparative visual criteria remain OPEN until this audit independently demonstrates closure. No source behavior, electrical gates, frozen visual thresholds, historical evidence, or sections 15-21 acceptance checkboxes are changed.

**2026-10-12 inferred fanout and interface-owner locality qualification launch:** Behavior commit `3761ffa00f6a67020d3c595de8b3b30023403d10` extends generic fanout scoring to terminal-/precedence-inferred signal relations without double-counting mixed annotations. Behavior commit `e6331b693bdacf468838af3601416135d1944676` prefers short producer/consumer corridors for correctly sided directed signal interfaces, exempts bidirectional and power-only interfaces, and uses the nearest owner for fanout; source-format descendant `66fce3380000d2ec3867f4ac39a52be79f0cee55` preserves behavior. Exact-head [Fast Validation 38305850348](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38305850348) **PASSED** all three jobs (locked-runner pytest and current-source regressions, hosted contracts, and static/Ruff). This documentation-only descendant requests the locked KiCad 10.0.6 five-run 56-base/V3-8-negative, I1–I6 interaction, and structural qualifications for **exact behavior source** `66fce3380000d2ec3867f4ac39a52be79f0cee55`. Electrical qualification does not close any of the six independently failing comparative criteria. Final native-render engineering inspection, baseline comparative closure, and sections 15–21 remain unchecked until independently verified. No historical evidence or frozen thresholds are changed.

**2026-10-12 directed-row source independent audit FAILED; development probe requested:** [Source-matched independent audit 38302271002](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38302271002) of qualified `794d864c6bf4956e7b786c0229a7b6d38d6d08c3` confirmed 90/90 comparative cases, but the same six frozen visual criteria remain **FAILED**: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `functional_fragmentation_nonworsening`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Historical→fresh totals: stage inversions 1→0, interface violations 77→44, fragmentation 14743.4342→14745.9761 mm, edge-biased cases 64→56, low-utilization cases 2→0, U-detours 691→870, and branch inconsistency 1529.08→1746.25 mm. Source-matched [native render inventory 38302271233](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38302271233) passed, establishing availability and reproducibility, **not** engineering visual acceptance. The diagnostic shows new per-case hard regressions (for example `base__v6-3` and `structural__a0_interleaved` gained one interface violation; `base__m2f2-two_signal_chains_shared_rail` gained one local label disconnect). This documentation-only descendant triggers the generic bounded development composition probe for seed/routing/branch diagnosis; it does not change behavior, waive visual defects, or close any sections 15–21 checkboxes.

**2026-10-12 source-matched 90-case comparative audit launch:** All three full locked KiCad 10.0.6 qualifications of **exact** source `794d864c6bf4956e7b786c0229a7b6d38d6d08c3` PASSED: 56 base cases ×5 plus V3-8 negative [38295854710](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38295854710), I1–I6 interaction cases ×5 [38295854693](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38295854693), and structural cases ×5 [38295854706](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38295854706). Exact-source Fast Validation [38295854701](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38295854701) passed all locked-runner, hosted contract, and static jobs. This **documentation-only** descendant requests an independent 90-case historical comparative audit and five-run normalized native-render inventory of the preserved exact-source qualification root `$HOME/m2h2-evidence/794d864c6bf4956e7b786c0229a7b6d38d6d08c3/`. These must verify the behavior change in inferred directed interface row alignment without treating qualification as aesthetic closure. The previously FAILED six comparative gates, engineering inspection, and final acceptance checkboxes remain open pending measured source-matched results; no tolerances have been relaxed.

**2026-10-12 directed connector row alignment qualification launch:** Generic candidate scoring now aligns inferred signal-input/output interfaces with the nearest owning signal row using the same directed semantic relations as interface-frontier scoring, while preserving exemptions for ambiguous bidirectional or power/reference-only interfaces. Behavior commit `46356e172452713d81dcdc7e7a6d13b08b2eeb84`, source-only formatting correction `4c5edf69cba1fbefbfd83a85b3ca42a7733c4fe3`, and regression-format descendant `da969c6812eaf5aebec4a2def65281e93744b712`. The exact-head [Fast Validation 38294439599](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38294439599) PASSED all three jobs (locked-runner complete pytest and real-tool regressions, hosted contract pytest, Ruff/static). This documentation-only descendant requests fresh locked KiCad 10.0.6 five-run base, I1–I6, and structural qualifications for the same production behavior; successful fast tests do **not** establish visual/comparative acceptance. The six previously failing comparative criteria, native-render engineering inspection, and sections 15–21 remain unchecked until source-matched independent evidence closes them.

**2026-10-12 independent comparative FAIL / development diagnosis:** The exact preserved qualification root for source `ffac87b0e6d5cc9d788fbfb28048c436743a952a` was audited by [run 38290616419](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38290616419) after all three locked KiCad five-run suites passed. Complete historical 90-case coverage was proved, but **six of twelve visual comparative criteria FAILED**: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `functional_fragmentation_nonworsening`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Historical→fresh totals: stage-order inversions 1→0, interface-side violations 77→44, edge-biased cases 64→54, low-utilization cases 2→0, fragmentation 14743.4342→14743.4361 mm, U-detours 691→858, and sibling-branch inconsistency 1529.08→1714.5 mm. The previous hard visual failures remain open without waivers. Source-matched native-render inventory [38290616413](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38290616413) PASSED; it establishes evidence availability, not aesthetic acceptance or engineering visual inspection. A format-only fix `a1cbd22948f57c77a875b58dd357916db0e5ddb6` and this documentation-only audit-launch descendant `8694fa977faba5b32a6b3ea8a01f9ba6c78acaea` preserve production behavior. Fast Validation [38290616357](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38290616357) PASSED all hosted contracts, locked-runner pytest/current-source regressions, and static checks. The next generic development composition probe is requested to diagnose choice of candidates and route/branch penalties without weakening frozen tolerances or special-casing any benchmark.

**2026-10-12 independent qualified-source audit launch:** Exact source `ffac87b0e6d5cc9d788fbfb28048c436743a952a` passed locked KiCad 10.0.6 base 56×5/V3-8-negative ([38257222455](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38257222455)), I1–I6×5 ([38257222464](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38257222464)), structural×5 ([38257222777](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38257222777)), and source-matched base and structural render transfers ([38259407140](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38259407140), [38261359388](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38261359388)). Fast Validation [38257222487](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38257222487) failed solely Ruff test formatting; unchanged-behavior descendant `a1cbd22948f57c77a875b58dd357916db0e5ddb6` corrects it, with new Fast Validation [38289895469](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38289895469) started. Request the independent 90-case comparative audit and normalized native-render inventory against persisted **exact-source** evidence root `$HOME/m2h2-evidence/ffac87b0e6d5cc9d788fbfb28048c436743a952a/`. Keep all six previously failed comparative visual criteria and sections 15–21 acceptance unchecked until the new audit and engineering inspection prove closure.

Canonical executable checklist for the post-M2h2 human-readable schematic composition remediation.

Source-level reconciliation checkpoint: current implementation/observer/oracle evidence has been reconciled through the source state immediately preceding this TODO update. Fresh locked-KiCad qualification, native-render inspection, comparative closure, and final PASS remain open and authoritative.

**2026-10-12 bounded-frontier remediation and qualification launch:** Independent artifact audit [38222075080](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38222075080) of qualified source `1520b40d8d4b655da8e0b63156e279ea03c9f788` still FAILS the same six comparative criteria: hard defects, individual nonworsening, fragmentation, route aesthetics, repeated alignment, and `i4__b2_mixed`. Baseline→fresh totals: stage inversions 1→0; interface violations 77→53; fragmentation 14743.4342→14759.9463 mm; U-detours 691→841; branch inconsistency 1529.08→1699.26 mm. Behavior commit `78cfcd557100fb780d141b13b33883bc75fa2fe0` corrects saturated eight-seed retention so both directed interface-frontier alternatives precede optional branch alternatives even when distribution, partial-beam, and repeated-structure slots are occupied. Regression descendant `7ab3b95a84a036d2e8b4d00a05513c7f584001c7` passed exact-head Fast Validation [38227198093](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38227198093). This checkpoint launches all three five-run locked-KiCad qualification suites for that new source. No visual/comparative acceptance is claimed; sections 15–21 remain open until source-matched independent audit and native engineering inspection pass.

**2026-10-12 current-source qualification/audit handoff:** Production and regression source `d6ed65a6ea92c5f0a91b949ee258671762c8ef05` passed locked KiCad 10.0.6 five-run base 56+V3-8-negative (run 38210636588), I1–I6 (38210636686), and structural (38210636624) qualifications, plus locked-toolchain diagnostics (38210637591). Source-matched base/structural render transfers passed (38213108120, 38213970555). Its Fast Validation (38210636612) passed locked-runner full pytest, current-source regressions, hosted contracts, lint, and structural audit, but failed only Ruff formatting for a missing blank line in `tests/test_m2_route_backtracking.py`. The exact one-line test-only format fix is commit `7289b247ea2693ae182370659dd76855265109a0`; its Fast Validation must pass independently. This documentation-only descendant requests the independent final-artifact comparative audit and normalized native-render inventory against **exact** persisted qualification source `d6ed65a6ea92c5f0a91b949ee258671762c8ef05`. Qualification success does not establish any section 15–21 visual or comparative acceptance; preserve all six previously failing gates and their checkboxes until independently disproved by current native evidence.


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
- [x] Confirm DP1–DP4 topology/frozen expectations remain unchanged (all eight authored input/expectation Git blobs match historical production source `79a36b17`; see `fixtures/m2h2/human_composition_baseline_2026-10-08/dp_frozen_inputs_audit_2026-10-08.json`).
- [x] Confirm all historical blind/evaluation and M2h2 finalization evidence is preserved.
  - Exact-head preservation audit: `docs/M2H2_COMPOSITION_PRESERVATION_AUDIT_2026-10-08.md`. Historical evidence unchanged since frozen baseline `4d892285` (complete 107-path Ralph Bridge comparison, zero protected evidence changes); no current-source qualification credit is implied.
- [x] Confirm `.local/` remains ignored.
- [x] Confirm `research/legacy_openclaw/` is not inspected or used.
- [x] Confirm locked KiCad 10.0.6 remains the governed real-tool version.
- [x] Confirm GitHub, repository, and CI operations run through authenticated `gh`/`git` on the project's self-hosted runner.
- [x] Confirm direct-`master` exact-head compare-and-swap workflow.

## 1. Baseline freeze and composition characterization

- [x] Record current `master` SHA and hashes of behavior-affecting M2 placement/routing/composition modules.
  - Baseline snapshot `c57f91d8253933abf319e4c116e176bdc334ac81` with 50 distinct M2 Python source Git blob SHA-1 identities in `fixtures/m2h2/human_composition_baseline_2026-10-08/m2_source_git_blob_checkpoint_2026-10-08.json`. This is a prequalification baseline for the listed M2 modules, NOT a final source freeze; final SHA-256 source hash closure remains unchecked in section 16.
- [x] Record historical M2h2 final PASS authority without modifying it.
- [x] Preserve/hash the final native-render archive used as the composition baseline.
  - `fixtures/m2h2/human_composition_baseline_2026-10-08/native_render_archive_manifest_42ab8452.json` records the preserved ten-part archive and its individual part SHA-256 and Git blob SHA-1 digests; the immutable archive contains 90 SVGs with independently verified SHA-256s and a sorted case inventory digest `759f49bf715da357d70f4fb4ae5513594328acb3ba8612031866ac6788a21fe0`. All ten archived files are present on current `master`. This preserves historical baseline evidence only, not current-source native render acceptance.
- [x] Add a new human-composition baseline evidence root.
- [x] Define a versioned composition metric schema before behavior changes.
- [x] Evaluate current final M2h2 renders using the initial independent observer.
- [x] Produce a ranked per-case defect inventory.
  - Exact-head baseline characterization evidence: `tools/analyze_m2h2_historical_composition.py` hash-verifies all 90 preserved final M2h2 native SVGs, reconstructs authored semantics independently of production scores, emits per-case interface/page/routing witnesses plus a deterministic defect-oriented `ranked_case_ids` inventory, and explicitly claims no current-source qualification. `tests/test_m2h2_historical_composition_analysis.py::test_full_historical_report_is_complete_ranked_and_archetype_covered` requires all 90 cases, unique one-to-one ranking, and zero missing/ambiguous semantic occurrences. Exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`: Fast Validation run `38012665368`, locked-runner full pytest step PASS; all governed regression/build steps 7-10 also PASS. The workflow conclusion is failure solely because artifact upload hit storage quota; hosted jobs failed before exposing steps/logs. Historical SVG geometry-only screening remains supplementary evidence, not final qualification.
- [x] Record `i4__b2_mixed` as a falsification seed.
  - [x] output interfaces on visually inappropriate frontier are detected;
  - [x] detached interface-to-owning-stage relationships are detected;
  - [x] weak page utilization/edge bias is detected;
  - [x] awkward branch/detour geometry is measured;
  - [x] local label-mediated visual disconnection is measured where applicable.
    - The generic falsification-seed test on exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b` requires both `OUTPUT_1`/`OUTPUT_2` right-frontier violations, >60 mm owner detachments, edge bias, at least one U-shaped detour, nonzero sibling-branch geometry inconsistency, and an `INPUT` local label-mediated disconnect; locked-runner pytest PASS in run `38012665368`.
- [x] Identify at least one baseline example for each applicable archetype:
  - [x] linear chain;
  - [x] branch/fanout;
  - [x] feedback;
  - [x] repeated channels;
  - [x] shared rail;
  - [x] internal reference;
  - [x] multi-output;
  - [x] long-field text;
  - [x] structural multi-band/one-band;
  - [x] mixed interaction.
  - `build_report()["archetype_examples"]` records exact case IDs from generic semantic/native geometry features. The exact-head corpus test requires keys for linear, branch/fanout, feedback, repeated channels, shared rail, internal reference, multi-output, long-field text, structural multi-band, structural one-band, and mixed interaction, and requires every selected example to be a member of the hash-verified 90-case ranked inventory. Locked-runner pytest PASS: `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`, run `38012665368`.
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
- [x] Add targeted regression for `i4__b2_mixed`.
  - Exact-head source `fec1a3f0c6ac54d7ce278c7b64a23f964abce8d4`: `tools/run_m2h2_current_regressions.py` includes the original mixed-branch design, with a lock/version check, independent electrical/ERC and serialized-scene verification, and independent human-composition observation. `tests/test_m2h2_current_regressions.py` prevents accidental loss of coverage. Locked KiCad 10.0.6 one-build case accepted (fast-validation run `37970772914`; `655 passed` in full pytest; all three CI jobs PASS). This checks inclusion and the single-run source regression only, **not** section 15's native-render aesthetic acceptance or section 17's five-run final qualification.
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
- [x] Prevent isolated stage members connected only through distant labels when a legal local arrangement exists.
  - Current-source exact-head evidence: `src/ai_kicad/m2_pack.py::_local_signal_proximity_candidates` searches direction-preserving adjacent vertical corridors when the aligned local slot is obstructed, while retaining measured hard-placement gates and bounded deterministic search. `tests/test_m2_composition_signal_locality.py` covers blocked-corridor recovery and semantic-order invariance. On exact source `fca44525387837ef869a891d9b0fcbab68e52518`, Fast Validation run `38005894006` completed full pytest plus locked-KiCad 10.0.6 V6-3/DP2, connector-label/selected-triple five-run, whole-band five-run, and fresh regression-build steps successfully; the workflow failure is solely the later artifact-upload quota failure and does not invalidate those completed steps. Native-render/final qualification remains open.
- [x] Record exact grouping penalties in candidate evidence.
- [x] Preserve existing 60 mm support/locality hard requirements.
- [x] Add small synthetic exhaustive grouping cases.
- [x] Add dominated-candidate oracle checks.

## 6. Branch, fanout, and feedback readability

- [x] Model branch points explicitly in composition evidence.
- [x] Prefer visually identifiable branch origins.
  - Production `m2_composition_candidate_rank._branch_readability_penalty` now groups ordinary signal and explicit branch fanout by semantic source/net, deduplicates targets, and penalizes off-center origins, uneven sibling depth, and backwards branches. Authored controls in `tests/test_m2_composition_candidate_rank.py` cover centered vs detached origins, signal-edge equivalence, renames/permutations, and unrelated-net exclusions; hosted contract and static checks passed for source `74f5d59b4f62b1e55dd46e078431e07dd02ee419`. Native render acceptance remains separately unchecked.
- [x] Prefer consistent sibling-branch geometry.
- [x] Penalize unnecessary branch crossings/detours.
  - Production uses both the generic fanout corridor penalty and the post-route lexicographic routing tier: among semantically equivalent fully proved candidates, actual canonical union length, worst-net length, and bend count are minimized before compactness/aesthetic tie-breakers. Cross-net physical intersections are a hard `prove_no_cross_net_contacts`/geometry-certificate failure rather than a tradable aesthetic cost. Exact source `3a5f282b95329c221c1478e3d3ec450030b2e806` additionally gates locked current-source V6-3, DP2, and `i4__b2_mixed` regressions on `unrelated_wire_crossing_count == 0` and records that emitted-route clearance evidence. Fast Validation run `38013448553`: full pytest and all locked real-tool regression/build steps 7-10 PASS; only artifact upload fails from storage quota.
- [x] Keep branch outputs attributable to source.
- [x] Model forward-path versus feedback-path roles.
- [x] Prefer compact feedback loops around owning stage.
- [x] Penalize feedback routes through unrelated functional blocks.
  - Generic `_feedback_corridor_intrusions` penalizes placements whose two shortest feedback elbows both traverse unrelated functional geometry while exempting feedback/support/package relatives. Actual emitted routing is stricter: body traversal is a hard geometry-certificate failure, so a selected feedback conductor cannot pass through an unrelated block body. Exact source `3a5f282b95329c221c1478e3d3ec450030b2e806` gates current-source real-tool regressions on `wire_through_body_count == 0` and records the certified field; full pytest and locked-KiCad regression/build steps 7-10 PASS in run `38013448553`. Final native-render engineering inspection remains separately open.
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
- [x] Add multi-band/repeated-channel regression.
- [x] Freeze repeated-structure acceptance tolerances from general corpus evidence.
  - Exact-head evidence `8a71ef7ec76980c251382293f2fd90c998954617`: the independent historical analyzer applies the already-frozen generic complexity-band limits (tiny 5.0 mm, small 4.0 mm, medium 3.0 mm, dense 2.5 mm) to every applicable incomparable semantic-peer pair across the hash-verified 90-case native baseline, records pass/fail counts and worst observed drift by band, and forbids case-specific retuning. `tests/test_m2h2_historical_composition_analysis.py::test_repeated_structure_tolerances_are_bound_to_full_corpus_without_retuning` passed in full pytest. Fast Validation run `38014022964` also passed locked-KiCad current-source regressions, connector/selected-triple five-run regressions, whole-band five-run, and fresh regression builds; artifact upload alone failed because Actions storage quota is exhausted.

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
- [x] Prefer common baseline/centerline for sequential active stages where practical.
- [x] Prefer role-consistent passive alignment.
  - Source-level semantic terminal-role alignment for local reference/shunt legs is implemented in `m2_composition_candidate_rank._passive_reference_axis_alignment_penalty`, including explicit exemptions for ambiguous/shared ownership. Three authored controls verify axis preference, refdes/port-order invariance, and shared-leg exclusions. Exact source `f1e9392efec0569c05e5a89f1446fa82bbc25f19`, hosted contract and complete static PASS in run `37908086300`. Native-render acceptance remains unchecked.
- [x] Align connectors with the signal rows they serve where practical.
- [x] Align local support structures rather than leaving arbitrary offsets.
  - Source-level alignment checkpoint: generic sequential signal and directed connector-row penalties in `src/ai_kicad/m2_composition_candidate_rank.py` and explicit support/package ownership axis penalty were exercised by authored positive, negative, fanout, feedback, and ordering controls in `tests/test_m2_composition_candidate_rank.py`. Hosted contract tests and complete static checks PASS on exact source `de219e0129d7814326517de1f71cb49c73ab0da5`, run `37906474016`. This supports the three checked source preferences only; locked KiCad 10.0.6, native route/render evidence, and final composition acceptance remain unchecked.
- [x] Preserve KiCad-compatible grid placement.
- [x] Make reference/value orientation consistent for comparable roles.
  - Generic symbol-relative reference/value field-slot consistency is now a late aesthetic tie-breaker in `m2_composition_candidate_rank._field_slot_consistency_penalty`. It compares matching functional kinds, terminal-role footprints and symbol rotations; exempts interfaces, different orientations, and missing text geometry; and never outranks routing or whitespace. Four authored controls cover preference, routing priority, renaming/declaration order, role/rotation exclusions and missing fields. Source `4a4c2d4742ddaa2ffa100caf87b5ef25f593281b`; hosted contract/static PASS in run `37909980631`. This source-level preference is not native-render field acceptance.
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
  - Independent observer refinement: count unique orthogonal intersection coordinates, invariant to wire serialization splits, reversals, and duplicates; preserve endpoint-on-interior unrelated-net conflict witnesses. Authored controls cover a split at the intersection and overlapping strokes. This is observer correctness, not a current-source native-render PASS.
- [x] Detect unnecessary U-shaped/rectangular detours.
- [x] Detect route excursions through unrelated blocks.
- [x] Report sibling-branch geometry inconsistency.
- [x] Detect label-mediated local disconnects.
- [x] Prefer direct visible local connectivity when legal and clearer.
- [x] Prefer labels for genuinely global/shared distribution when clearer.
  - Current-source routing evidence: `m2_route._optional_local_visible_edges` admits only unique two-fragment local signal-interface relations within the existing 80 mm locality bound and `route_between_fragments` adds a best-effort obstacle-checked conductor while preserving the 250 mm canonical-length gate. Distant, distributive/shared, ambiguous, power/reference, blocked, and over-length cases remain label/distribution governed. `tests/test_m2_terminal_interface_flow.py` covers both local visible routing and distant/distributive label retention. Exact source `97542c4cd1ca1a6e46afb050cf6bac5a23540c0b`, locked-runner full pytest PASS in run `38012665368`; final native-render acceptance remains open.
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
- [x] Search meaningful interface-frontier alternatives.
- [x] Search meaningful semantic block-order alternatives.
- [x] Search meaningful repeated-channel row/column alternatives.
  - Current-source 28428470c8d4bd4672e8fe94fe24ac6577be8bbe: generic bounded row and column generation plus explicit final eight-seed retention and deduplication, with regression coverage; hosted static and contract PASS in run 37835474849. This establishes source implementation only; native KiCad qualification and render acceptance remain open.
- [x] Search meaningful support-placement alternatives.
- [x] Search meaningful field-slot alternatives.
  - Current-source `eff40b3e4f6d4bf0e34e28cbf106ab65095a8550`: independent measured text-slot variants, bounded field-kind variant proposals, explicit final eight-seed retention, and dedicated generic regressions. Hosted static/contract validation PASS in run `37840687842`; native KiCad qualification remains open because the self-hosted runner lacks pinned `/tmp/AppDir` files.
- [x] Search meaningful branch/route alternatives where already bounded.
  - Bounded `m2_pack._branch_fanout_repack_candidates` searches a source-centered fanout and sibling-depth alignment, checks all candidates through `_measured_repack` hard placement/terminal constraints, and protects both legal variants from the final eight-seed retention cap. Five authored controls cover centering, sibling-depth correction, net rename/declaration permutation, retention, and unrelated-net exemption; these are included in hosted contract CI. Source `d4752e40855d64e15fcc0f383b480b4375d5f20c`; hosted contract/static PASS in run `37911027488`. Actual emitted-wire route clarity and native KiCad qualification remain unchecked in sections 6, 11, 15–21.
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
- [x] Require evidence when bounded production search legitimately misses oracle optimum.
  - `m2_tiny_grid_composition_oracle.verify_tiny_search_budget_witness` and `m2_tiny_grid_oracle_miss_evidence.require_bounded_search_miss_evidence` reject an unexplained dominated candidate, disclose candidate/attempt budgets and unvisited optimum witnesses, and reject hidden better attempted candidates. Authored positive/negative/boundary controls in `test_m2_tiny_grid_composition_oracle.py` and `test_m2_tiny_grid_oracle_miss_evidence.py` passed (34 tests in local source-level validation on 2026-10-08). This source-level reconciliation does not imply locked KiCad qualification.
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

Source-level checkpoint: `cdcfd445be09712f8a12d30068d3a23509cb7684`, fast-validation run `37829859944` (hosted contract pytest and static checks PASS; locked KiCad job queued). New functionality and authored regressions support the checked implementation items; no native-render or final-source PASS is claimed.

## 15. Targeted composition regression suite

**Latest exact-head acceptance audit (2026-10-10; qualification source `ea154c78b8f0ca7348159d3d068fc62d8630f337`):** the 56×5 plus V3-8 negative workflow (38075923683), I1–I6×5 workflow (38075923724), and nine structural-class×5 workflow (38075923789) completed successfully. Fast Validation (38075923711) completed all jobs successfully. Preserved evidence resides at `$HOME/m2h2-evidence/ea154c78b8f0ca7348159d3d068fc62d8630f337/` on the locked runner; GitHub artifact uploads are unavailable because artifact quota is exhausted. The independent final-artifact audit, run 38080254766 on documentation-only descendant `095d99ff5ffbd687cc94cd134ef478dead9fcd96`, **failed six comparative gates**: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `functional_fragmentation_nonworsening`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. All 90 historical cases were matched, but 89 remained in the independent regression diagnostic inventory. The seed `i4__b2_mixed` improves from two interface-side violations and one label disconnection to zero of each, yet still has page edge bias, and measured U-detours (2→6), branch inconsistency (21.59→29.21 mm), and fragmentation (73.6602→99.0602 mm) worsen. **Do not mark targeted visual acceptance or comparative closure as passed.** An artifact-independent persisted native-render inventory, run 38080478852, found/hashes 685 renders for 137 distinct qualified cases; all require normalized-geometry and engineering visual inspection because raw SVG byte hashes differ across runs. This is an unresolved engineering issue, not a waiver of any hard gate.

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

**KiCad restoration requalification checkpoint — 2026-10-11:** The user reports that KiCad is installed again. Re-run the full locked-KiCad qualification for the current production candidate, preserving the exact original `fixtures/m1a/toolchain.lock.json` byte hashes and platform identity. The prior failure was the runner's disappearance of all six pinned `/tmp/AppDir` files; successful installation alone is not evidence until the current runner passes byte-identical toolchain validation and current-source builds. This checkpoint launches fresh base 56×5 plus V3-8, I1–I6×5, and structural class×5 workflows using an unchanged behavior-affecting source at `5b0443db2129be45e9e654bad4a112b4b8e06264`. Retain unchecked acceptance checkboxes pending successful runs and independent comparative audit; do not count prior-source evidence toward new visual composition closure.

**2026-10-11 locked-runner infrastructure checkpoint:** The latest behavior-affecting source is `5b0443db2129be45e9e654bad4a112b4b8e06264` (generic crowded-seed page-centering priority). Its full base, I1–I6, and structural workflows [38117316720](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316720), [38117316727](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316727), and [38117316704](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316704) failed because the self-hosted runner lost **all six byte-pinned KiCad 10.0.6 executables/libraries under `/tmp/AppDir`**, not because measured composition acceptance failed. Fast Validation [38124891073](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38124891073) passed its static and hosted jobs, including all four new locked-toolchain preflight tests, but failed the locked-runner job at the KiCad identity check. Restore exact original locked files following `docs/M2H2_LOCKED_KICAD_RUNNER_RECOVERY_2026-10-11.md` before any fresh native qualification; do not weaken or re-lock hashes/tolerances. The independent comparative audit of preceding source `2a112223d70bb882277351be909464efcd17b46f`, [38115751629](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38115751629), **still fails six hard/visual comparative acceptance criteria** despite `i4__b2_mixed` reaching zero observer hard defects. None of sections 15–21 may be marked passed based solely on source tests, infrastructure failures, or prior-source visual evidence.

Qualification launch checkpoint (2026-10-10): all three locked-KiCad five-run qualification workflows passed against the exact production-source ancestor `e95ce90b70dcac8a0b20044bf5310a5b71a99618`: base 56×5 and V3-8 negative [run 38020960775](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38020960775), all I1–I6 interaction cases [run 38020960772](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38020960772), and all nine structural classes [run 38020960769](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38020960769). Subsequent commit `5d2058b4adffc32acd19a32737733b1d08093da3` changed only pytest import configuration; Fast Validation [run 38021133728](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38021133728) passed all three jobs on that head. The current documentation-only commit starts **fresh exact-head base, interaction, and structural qualifications** so the same source state can be bound to final evidence. This paragraph is an execution checkpoint, not qualification of the documentation commit, composition-observer closure, render inspection, or final PASS. Do not promote any section 15–21 acceptance checkbox until its corresponding exact evidence is independently checked.

Exact-source validation checkpoint (not final qualification or a source freeze): behavior-affecting Python source at `69b27128625e71caae704707b396071046c029f9` passed all three jobs of [M2h2 Fast Validation run 38017902850](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38017902850). The locked KiCad runner completed full pytest, current-source V6-3/DP2 generation and independent electrical/scene regressions, the connector/selected-triple and whole-band five-run regression subsets, and fresh regression-build steps. Hosted contracts, Ruff lint and scope-specific formatting, structural anti-overfitting, `git diff --check`, and scoped trailing-whitespace checks passed. The eight items checked below are **only** those directly supported by this exact-source run; it is not evidence for the full 56×5, I1–I6×5, structural-class×5, native-render engineering inspection, comparative closure, or final PASS. Any subsequent behavior-affecting change requires revalidation of the affected gates.

- [ ] Finish all behavior-affecting composition implementation changes.
- [x] Run complete pytest.
- [x] Run scoped Ruff lint.
- [x] Run scoped Ruff format check.
- [x] Run `git diff --check`.
- [x] Run scoped whitespace checks.
- [ ] Run applicable link checks.
- [ ] Run historical preservation audit.
- [ ] Run literal anti-overfitting audit.
- [x] Run structural anti-overfitting audit.
- [ ] Confirm CP-SAT remains absent.
- [x] Run current-source V6-3 real-tool regression.
- [x] Run current-source DP2 real-tool regression.
- [ ] Record final behavior-affecting source hashes.
- [ ] Freeze composition observer/oracle schema and hashes.
- [ ] Create fresh final human-composition qualification root.
- [ ] Declare later behavior-affecting source changes qualification-invalidating.

## 17. Fresh locked-KiCad qualification

**2026-10-12 generic passive-interface flow integration checkpoint:** Behavior-affecting source `794e992397374463c54ac22f8479049a2d7c5302` extends bounded measured frontier alternatives to terminal-backed and precedence-inferred directed signal relationships, without treating ambiguous shared passive interfaces as directed. Its Fast Validation [38256018062](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38256018062) failed only Ruff source formatting and an obsolete V4-7 assertion that incorrectly required the selected candidate's **last** packing-attempt label to be shelf `:pass:measured=`; 775 other tests passed. Exact descendant `0351b38198e0eae9047ad94056631d172ebd908d` fixes Ruff formatting and requires that measured packing evidence be present among the selected candidate's recorded attempts without rejecting a valid `interface-frontier-output` placement. The locked-toolchain check is unchanged. This documentation-only qualification launch requests fresh base 56×5/V3-8, I1–I6×5, and nine structural classes×5. These new source tests and run requests do not discharge the six failed historical-comparative visual criteria, nor justify checking sections 15–21. Re-run the independent full-90-case audit and native-render inspection if and only if the new source passes qualification.

**2026-10-12 multi-interface frontier remediation checkpoint:** The previous exact-source `cccc968f90b6a739d226f63b9a76c95d765bed8e` passed the base 56×5/V3-8, interaction I1–I6×5, structural-class×5, Fast Validation, pinned KiCad diagnostic, and base/structural render-transfer workflows. That evidence is for the preceding source only, and **does not establish composition acceptance**. The current behavior-affecting source `14571870ce89cb2c1b1edfc11e232c43c12d7b4b` repairs multiple independently reversed output interfaces in a single bounded, measured frontier candidate instead of using the sole output alternative on one connector; generic declaration-order regression coverage is included. Its immediate predecessor passed locked-runner complete pytest and current-source regressions plus hosted contracts in [Fast Validation 38248835798](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38248835798), which failed **only** the Ruff formatting check. The subsequent source commit applies the exact Ruff-recommended formatting; new exact-head Fast Validation is required. This documentation-only checkpoint triggers all three full locked-KiCad five-run suites for the unchanged behavior source. All comparative gates, native visual inspection, and sections 15–21 acceptance remain **unchecked** until the new source proves them; do not weaken thresholds or claim that a routing/fragmentation regression is resolved without a source-matched independent audit.

**2026-10-11 generic mid-run junction ranking checkpoint:** Behavior-affecting source `997437237acbb0769a0ef9b27d65f550414b705f` corrects the generic route-backtracking metric to count return legs on a coalesced continuous run even when other conductor branches join its interior. Earlier vertex-splitting approach `591d899462a75c09c32aeb63b0b746d3e4ba2ab4` was falsified by the existing segment-splitting/serialization metamorphic test and was reverted before the corrected implementation. Current exact-source [Fast Validation 38204743461](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38204743461) passes all three jobs (locked-runner complete pytest/current-source regressions, hosted contract tests, Ruff/static audit). This documentation-only qualification launch requests fresh base 56×5/V3-8, I1–I6×5, and nine structural classes×5. This is **not** acceptance of the routing-aesthetic comparative gate: all six prior comparative failures remain open until source-matched persisted native evidence and independent engineering inspection are positive. Do not mark sections 15–21 complete from fast validation or test-only geometry controls.

**2026-10-11 exact-source requalification / independent-audit launch:** repaired behavior-affecting source `4887dc44d1b7d0cf7cbb5027e2fcdf6de1817416` and regression-test descendant `9938aa4be5d4ab15507f307cfa2465f65010e17a` passed Fast Validation [38168404548](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38168404548), locked-toolchain identity [38168404550](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38168404550), 56×5 and V3-8-negative [38168404656](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38168404656), I1–I6×5 [38168404663](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38168404663), and structural-class×5 [38168404684](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38168404684). Source-matched base [38170544030](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38170544030) and structural [38171244470](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38171244470) render-transfer workflows passed. Persistent runner qualification root is `$HOME/m2h2-evidence/9938aa4be5d4ab15507f307cfa2465f65010e17a/`; GitHub Actions upload-artifact storage quota is exhausted, so audit from persisted evidence rather than fabricating downloadable artifacts. This documentation-only follow-up requests the independent comparative artifact audit and normalized native-render inventory for **exact** `9938aa4be5d4ab15507f307cfa2465f65010e17a`. **Neither visual comparison, case-by-case engineering inspection, final source freeze, nor overall PASS is established** by these automated qualification results. Retain sections 15–21 acceptance boxes unchecked until the independent audits and engineering inspection provide affirmative case-level evidence.

**2026-10-11 restored locked-KiCad three-suite qualification evidence:** exact source `44d0dfa437f060e234792fec2e6285e5b10cc4b9` passed [56 base cases×5 with V3-8 negative, run 38131967086](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38131967086), [I1–I6×5 interactions, run 38131967113](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38131967113), and [nine structural classes×5, run 38131967196](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38131967196). The isolated [locked-toolchain diagnostic 38131967136](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38131967136) independently passed byte-pinned KiCad 10.0.6 identity. This is exact-source **electrical/structural/generation qualification evidence**, not final human-composition PASS. Trigger native-render inventory, base and structural inspection transfer, and independent comparative audit against the persisted `$HOME/m2h2-evidence/44d0dfa437f060e234792fec2e6285e5b10cc4b9/` root. Keep visual acceptance, new-source metric reproducibility, and final sections 18–21 unchecked until full independent audit and engineering inspection. The previous six comparative deficiencies remain open until this audit disproves them from current evidence.

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
- [x] Archive hashes for every inspected render.
  - The nine exact-source structural-class render hashes are recorded in `docs/reviews/M2H2_STRUCTURAL_NATIVE_RENDER_INSPECTION_ee4c37a.md`; final 137-case render hashes remain outstanding.
- [ ] Inspect at least one representative render for every distinct governed case.
- [ ] Explicitly inspect all mixed/high-density cases.
- [ ] Explicitly inspect all repeated-channel cases.
- [ ] Explicitly inspect all branch/fanout cases.
- [ ] Explicitly inspect all feedback cases.

- [ ] Explicitly inspect all shared-rail/reference cases.
- [ ] Explicitly inspect all long-field cases.
- [x] Explicitly inspect all structural band-class cases.
  - All nine exact-source structural-class SVGs were inspected; findings and unresolved page-use concerns are recorded in `docs/reviews/M2H2_STRUCTURAL_NATIVE_RENDER_INSPECTION_ee4c37a.md`.
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
- [x] Record inspection as engineering/agent inspection, not user approval.
  - The cited record explicitly identifies this as Codex engineering inspection and documents its limited scope.
- [ ] Any hard visual defect falsifies the candidate and reopens affected qualification.


## 19. Comparative baseline closure

**2026-10-12 independent comparison FAILED — multi-output frontier candidate did not close visual gates:** The source-matched [artifact audit 38254601281](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38254601281) evaluated all 90 historical native cases against fully qualified `4883d4174bad6021e2f0f34cc40962f1a6791d7e`. It failed six of twelve criteria: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `functional_fragmentation_nonworsening`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Stage inversions: 1→0; interface violations: 77→53; fragmentation: 14743.4342→14759.9463 mm; U-detours: 691→841; branch inconsistency: 1529.08→1699.26 mm. For `i4__b2_mixed`, observer hard defects improve 4→0, but U-detours 2→6, branch inconsistency 21.59→29.21 mm, and fragmentation 73.6602→99.0602 mm; the selected source geometry remains a `centroid-balanced-page` seed, not the new frontier-repair candidate. [Normalized native render inventory 38254601443](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38254601443) passed. This documentation-only update requests the existing generic development composition probe for seed-selection/ranking diagnosis. No source behavior is modified; do not count the frontier repair as a comparative closure or mark sections 15–21 complete.

**2026-10-12 multi-output frontier source-matched qualification / independent audit launch:** Exact repaired production source `14571870ce89cb2c1b1edfc11e232c43c12d7b4b` with documentation-only qualifying descendant `4883d4174bad6021e2f0f34cc40962f1a6791d7e` has passed all three mandatory locked KiCad 10.0.6 five-run suites: 56 base positives ×5 plus V3-8 negative ([38250175239](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38250175239)), I1–I6 interaction cases ×5 ([38250175241](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38250175241)), and nine structural classes ×5 ([38250175348](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38250175348)). Base native-render transfer [38252138862](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38252138862) passed. Preserved exact-source evidence root: `$HOME/m2h2-evidence/4883d4174bad6021e2f0f34cc40962f1a6791d7e/` on the locked runner. This documentation-only follow-up requests the **independent comparison against the entire 90-case historical baseline and normalized 137-case native render inventory** for that exact source, using persisted evidence, not stale older reports. The prior six comparative failures remain unresolved unless the newly generated source-matched audit discharges them. In particular, qualification tests do not establish U-detour, fragmentation, repeated-structure, or `i4__b2_mixed` visual PASS; sections 15–21 remain unchecked pending engineering inspection and complete audit closure.

**2026-10-11 independent current-source audit — still FAILED:** [run 38196730438](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38196730438) independently evaluated all 90 historical native SVG cases against exact successful qualification source `9938aa4be5d4ab15507f307cfa2465f65010e17a`. Six of twelve comparative criteria FAIL: `baseline_hard_defects_cleared`, `individual_hard_defects_never_worsen`, `functional_fragmentation_nonworsening`, `routing_aesthetics_nonworsening`, `repeated_structure_within_frozen_tolerance`, and `i4_specific_improvement`. Improvements: stage inversions 1→0, interface violations 77→53, edge-biased cases 64→55. Regressions: fragmentation 14743.4342→14759.9463 mm, U-detours 691→845, branch inconsistency 1529.08→1717.04 mm. `i4__b2_mixed` hard defects 4→0 and edge bias true→false, but U-detours 2→6 and branch inconsistency 21.59→29.21 mm. Prioritize generic route-backtracking, branch geometry, repeated structure, and residual per-case hard-defect remediation; do not relax observer thresholds. Native render hashes for 137 cases ×5 passed normalized comparison in [inventory 38196730492](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38196730492), but required engineering inspection remains incomplete. Generic route-backtracking ranking candidate `a2209341f3e83d828a4698dc165347f921a8a53e` is a new behavior-affecting source and requires fresh five-run qualification and a new independent audit before any acceptance checkbox is marked complete.


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

Reproducibility evidence checkpoint (2026-10-10): source `ea154c78b8f0ca7348159d3d068fc62d8630f337` has **137/137 distinct qualified cases with identical normalized native KiCad SVG SHA-256 across all five runs**, verified independently from 685 preserved SVG files using governed normalization of volatile SVG `<title>` elements. Runner-native manifest v2: `$HOME/m2h2-evidence/ea154c78b8f0ca7348159d3d068fc62d8630f337/audit/native_render_inventory_v2_ea154c78b8f0ca7348159d3d068fc62d8630f337.json`; [Persisted Native Render Inventory run 38081853532](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38081853532) PASS. Raw hashes differ for all 137 cases, as expected when volatile titles vary; this does not weaken the normalized geometry requirement. All case SVGs have exact per-run hashes in the v2 manifest. The independent visual/aesthetic acceptance audit remains FAILED (run 38080254766); this checkpoint supplies only reproducibility evidence, not visual inspection, source stabilization, or final PASS.

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
