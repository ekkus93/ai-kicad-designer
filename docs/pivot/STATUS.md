# MCP architecture pivot status

**Working branch:** `mcp`  
**Branch start:** `f14a02c3140fd455ded8391ea65b8416b5d6e170`  
**Plan:** [`../MCP_ARCHITECTURE_TODO.md`](../MCP_ARCHITECTURE_TODO.md)  
**Architecture:** [`../MCP_ARCHITECTURE_SPEC.md`](../MCP_ARCHITECTURE_SPEC.md)

## Current state

The pivot has completed branch/toolchain preflight, preservation inventory,
repository mapping, source-linked upstream capability inventory, evidence
contract, and the first fixed reference-circuit corpus. The original M2b suite
passed 22 tests against locked KiCad 10.0.6. The new 5 V NE555 astable with a
current-limited LED has a native schematic, zero ERC diagnostics, exact
pin-net equivalence, a hashed BOM and footprint set, calculated behavior
bounds, and a conservative two-layer board profile. Its PCB is not placed or
routed.

The evidence contract has seven focused passing tests. `tools/pivot/preflight.py`
and `tools/pivot/bootstrap.sh` are implemented and the host manifest records
Python 3.12, locked KiCad 10.0.6, Ollama, and the available GPU. Ollama is
available. In a structured reference review, Qwen3.5 9B mapped reset pin 4 to
the wrong net and returned 139 Hz instead of about 1.39 Hz. After an explicit
unit correction prompt it still returned incorrect timing. Both raw outputs
and comparisons are retained; they are not accepted as engineering evidence.
No candidate MCP has yet been invoked on the reference POC, and no backend has
been selected.

Fixture manifest verification, tamper detection, repository path-escape
checks, write-once experiment path allocation, and benchmark trial/scoring
contracts are implemented. Nineteen focused pivot tests pass, along with Ruff
lint and format checks. The reference fixture manifest includes its symbol
library table and verifies successfully.

P0-004 is complete: three isolated Konnect/Ollama runs were recorded, and the
tracked M2H2 tree audit found zero worktree or index differences across the
22,544-file baseline. Pre-existing untracked M2H2 evidence remains untouched.
P0-005 now has a reusable local Ollama-to-MCP stdio runner with tool allowlists,
budget/path guards, source-mutation and tool-use gates, and hashed outputs. The
direct Ollama run failed three engineering checks. Runs 1–3 initially produced
no tool calls because the runner forced JSON mode during tool selection. An
isolated probe confirmed Qwen can emit tool calls. Run 4 executed all four
required Konnect tools but exhausted its generation limit before returning
structured JSON. Run 5 used all four tools and returned valid JSON; tool use
and source immutability passed, while the three engineering checks failed:
unnamed net identities were collapsed, timing was about 404 Hz instead of
1.39 Hz, and LED current was reported as 20 mA instead of the expected 3.1 mA
nominal / 5.527 mA conservative upper bound. A second local model, Qwythos
Codex, made the same four tool calls and failed the same gates, returning about
8,176 Hz and 20 mA. Exact trial records are
`fixtures/pivot/experiments/konnect_qwen_inspect_2026-10-22_run5/trial.json`
and `fixtures/pivot/experiments/konnect_qwythos_inspect_2026-10-22_run1/trial.json`.
A direct `get_component_nets` call for U1 confirmed Konnect returns `null` for all four unnamed nets (pins 2, 5, 6, 7); see `fixtures/pivot/experiments/konnect_component_nets_direct_2026-10-22_run1/result.json`.
The runner and evidence are under `tools/pivot/benchmark_runner.py` and
`fixtures/pivot/experiments/konnect_qwen_inspect_2026-10-22_run1` through
`run7`, `konnect_qwen_component_nets_2026-10-22_run1`, plus
`ollama_toolcall_probe_2026-10-22_run1`.

P0-006 has a real pinned Konnect build and CLI-backed MCP calls for project
inspection, net summaries, ERC, and netlist generation. ERC and independent
netlist equivalence passed with the merged symbol table. Konnect’s net summary
omitted unnamed partitions, collapsing separate nets to `~`; its named-net
listing showed only three of the seven independent physical partitions. PCB,
footprint, DRC, Gerber/drill, rollback, and live editor/IPC probes remain open.
The direct component-net API call returned null for unnamed nets, establishing a concrete readback gap. The host has no KiCad IPC socket or display, so GUI-dependent operations need a display-enabled runner.

## M2H2 preservation boundary

M2H2 remains **INCOMPLETE** as recorded by `fixtures/m2h2/STATUS.md`. The pivot
does not replace its governing specification or qualify any of its historical
evidence. Tracked fixture and source identities are in the pivot protection
inventory. Pre-existing untracked M2H2 evidence remains in place and is not
included in that baseline.

## External actions

No board has been ordered or manufactured. The workflow stops at
`PACKAGE_READY_FOR_REVIEW`; any later purchasing or physical testing remains a
separate owner-authorized task as specified in the architecture document.


The initial ProductOfAmerica 0.21.1 PCB synchronization probe created a board and seven nets, but skipped all ten components because the copied schematic did not yet have its BOM footprint assignments. Readback found zero footprints and DRC failed on the absent Edge.Cuts outline. The later configured footprint and routing retries are summarized below.

Seeed 3.4.11 passed independent netlist equivalence in the prior operation probe. An isolated `add_label` edit was serialized and then rejected by locked KiCad ERC because the label was dangling. The frozen source schematic remains byte-identical; only the disposable copy changed. The raw probe's `source_fixture_unchanged=false` flag describes that expected workspace-copy change, as clarified by the independent assessment. The copy is the rollback boundary. See `fixtures/pivot/experiments/seeed_edit_probe_2026-10-22_run1/independent_assessment.json`.

These experiments advance P0-007 and P0-008 but do not satisfy their full acceptance criteria. ProductOfAmerica still needs footprint assignment, valid outline, native save/open and export probes; Seeed still needs a valid net-connected edit and a tested rollback/readback cycle. The empty-board and dangling-label failures are retained as negative evidence.

## Cross-backend and inventory experiments (2026-10-22)

The initial ProductOfAmerica sync created a shell with seven nets but skipped
ten components because the copied schematic did not yet have its BOM footprint
assignments. Footprint readback was empty and DRC found no Edge.Cuts outline.
Java 25 and pcbnew bindings were later configured in isolated paths to run the
router. The initial failure remains at
`fixtures/pivot/experiments/productofamerica_pcb_probe_2026-10-22_run1/`.

Seeed 3.4.11's generated netlist passed exact terminal-partition equivalence
with exact remapping for exporter-generated net names. Its isolated `add_label`
edit serialized, then native ERC found one dangling-label error. The frozen
source schematic SHA remains `9d819329416ae990c9ba1b9feddc5eca91c6220650259ea740b8fdc38f31903f`;
only the candidate workspace copy changed. The candidate directory is the
rollback boundary; no backend transaction rollback API was exercised. See
`fixtures/pivot/experiments/seeed_edit_probe_2026-10-22_run1/independent_assessment.json`.

P0-010 is complete. Three Qwen repetitions each were run with 4 task-gated
tools, 57 schematic-phase tools, and all 236 Konnect tools. All used the same
fixture, model digest, and time/token/call budgets. Task gating completed all
required calls but failed engineering accuracy. Phase and full inventory runs
repeatedly called `get_project_info` with the invalid `project_dir` argument;
their engineering scores also failed. Mean recorded usage was 4,936 tokens and
37.91 s task-gated, 8,641 tokens and 8.08 s phase-gated, and 8,443 tokens and
5.28 s full-inventory. Exact records and full tool definitions are indexed in
`fixtures/pivot/experiments/tool_visibility_comparison_2026-10-22.json`. The
forged hidden-tool dispatch, workspace traversal and symlink tests pass. Ruff
lint/format pass and the pivot suite passes 21 tests. No mode qualifies the
model for autonomous engineering decisions.

For the KiCad development probe, the official Ubuntu Jammy nightly package
`202609150250+2291d3f224~189~ubuntu22.04.1` was extracted under `/tmp` without
installing system packages. Its embedded libraries identify the build as
KiCad 10.99.0 (`libkigal.so.10.99.0`). The CLI cannot start in this host because
wxGTK 3.2, GTK, protobuf and several related shared libraries are missing. This
is not yet a runnable KiCad 11 environment; KiCad 10.0.6 remains unchanged.

### ProductOfAmerica configured footprint and export retry

The first PCB sync had no footprint-library table in the disposable HOME, so
KiCad could not resolve its libraries. On a fresh copy, I set the isolated
KiCad 10 footprint table from the locked AppDir, applied every footprint from
the approved BOM through ProductOfAmerica's `set_component_property`, and
synced again. The backend returned all ten footprints and seven nets. An
independent parse of the saved `.kicad_pcb` matched every approved footprint
and exact `(refdes,pad,net)` partition against the frozen design. Four outline
segments matching the 50 × 35 mm reference profile were added; export generated
25 Gerber layers/files and a drill file.

The first configured sync still had 16 unconnected items. I installed Temurin
25 under `/tmp`, pointed the MCP server at KiCad 10's `pcbnew` Python bindings,
and ran the router on a second isolated board. It added 46 tracks and cleared
all 16 unconnected items, with one 0.15 mm width violation. On a new copy, the
backend's `set_trace_width` repaired five tracks on `Net-(U1-THRES)` to the
project's 0.20 mm minimum. Locked KiCad 10.0.6 then reported zero DRC violations
and zero unconnected items. An independent parser confirmed all seven expected
net partitions are copper-connected and all ten footprints match the approved
BOM. The final candidate's routing metrics and terminal checks are in
`fixtures/pivot/experiments/productofamerica_drc_repair_2026-10-22_run1/independent_assessment.json`.

Gerber export from the repaired board generated the required copper, mask,
silkscreen, outline and fabrication files, plus one drill file. The outputs
remain a preview: no separate Gerber/drill geometry parser or human review has
been run, and the profile is not fabricator-approved. All candidate files are
isolated under `fixtures/pivot/experiments/productofamerica_*`.
