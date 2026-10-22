# Reproduce the reference design-to-fabrication review package

This demonstration starts from the hash-locked native KiCad fixture at
`fixtures/pivot/reference_555_led_flasher_v6/native_project/`. It keeps v1 as
an immutable record of the label-only external-port layout and v2 as the
connector-redraw iteration. In v3, J1, J2 and J3 sit at their circuit nodes,
and the R3/LED branch is moved beside the 555 and wired directly into the VCC
bus and output run. v4 centers the drawing, and v5 draws shared REF and VCC
rails, and v6 moves reference/value fields closer to the matching symbols. The redraws preserve the v1 pin-to-net partition. The
phase-gated workflow runs
through the local logical MCP server, calls the pinned KiCad CLI for ERC, DRC,
netlist and Gerber/drill export, independently inspects native connectivity
and fabrication geometry, and creates a review ZIP. It does not place an
order or claim physical acceptance.

## Host setup

Use Ubuntu with Python 3.12, `uv`, and the official KiCad 10.0.6 AppImage
extracted at `/home/phil/Applications/kicad-10.0.6/`. The checked-in
`uv.lock` pins the Python environment. No Docker or Podman is used.

```sh
uv sync --locked --python 3.12 --extra dev
uv run --locked --python 3.12 python tools/pivot/preflight.py
uv run --locked --python 3.12 python -m tools.pivot.verify_native_project \
  --fixture fixtures/pivot/reference_555_led_flasher_v6/native_project
```

The environment manifest records tool and asset hashes. If the AppImage is at
another path, pass the corresponding `kicad-cli` executable explicitly.

## Run the POC

Experiment directories are write-once. Choose a new identifier on every run:

```sh
uv run --locked python -m tools.pivot.run_reference_poc \
  --experiment-id reference_poc_manual_run1 \
  --fixture fixtures/pivot/reference_555_led_flasher_v6 \
  --cli /home/phil/Applications/kicad-10.0.6/kicad-cli
```

Render a close schematic preview from that output before finalizing a review
package:

```sh
uv run --locked python -m tools.pivot.render_schematic_preview \
  --cli /home/phil/Applications/kicad-10.0.6/kicad-cli \
  --schematic fixtures/pivot/experiments/reference_poc_manual_run1/editable_project/Reference555LedFlasher.kicad_sch \
  --output fixtures/pivot/experiments/reference_poc_manual_run1/previews/schematic.png \
  --metadata fixtures/pivot/experiments/reference_poc_manual_run1/reports/schematic-preview.json
```

The command prints the experiment directory under
`fixtures/pivot/experiments/`. Review `reports/verification_report.json`,
`fabrication_manifest.json`, `review-package.zip`, `package.sha256`, and the
top/bottom renders in `previews/`. The package verifier extracts the ZIP into a
clean directory and checks its hashes and revision identity.

Run the fixed placement probe independently when reviewing the placement
stage. It uses `placement-plan.v1.json`, checks the exact source-board hash and
design revision, applies the coordinates to a candidate copy, verifies native
readback and runs real KiCad DRC. Its unrouted source intentionally has open
nets, so it is not a routing or release test.

```sh
uv run --locked python -m tools.pivot.run_deterministic_placement \
  --experiment-id deterministic_placement_manual_run1
```

## Repeated-run report

Runs 19, 20, and 21 are the three retained clean repetitions against the final readiness gate. Their semantic
outputs and renders match; the elapsed time and ZIP checksum vary and are
recorded per run. Regenerate the comparison with:

```sh
uv run --locked python -m tools.pivot.summarize_reference_runs \
  --runs 19 20 21 \
  --output fixtures/pivot/experiments/reference_poc_repeatability_2026-10-22_run19-21.json
```

The clean ZIP was also opened with locked KiCad 10.0.6, then independently compared to schematic, board, Gerber and drill observations in `fixtures/pivot/experiments/reference_poc_review_2026-10-22_run2/reports/clean-extract-validation.json`. The verification report distinguishes measured KiCad checks from the
profile's order-dependent assumptions. The board remains `PACKAGE_READY_FOR_REVIEW`;
human electrical review, manufacturer acceptance, fabrication, assembly and
physical behavior require their own evidence.
