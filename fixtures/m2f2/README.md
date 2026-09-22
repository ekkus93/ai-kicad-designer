# M2f2 repair evidence

This directory contains development and known-regression evidence for
**M2f2 — typed packing projection and parallel-consumer layout repair**.

The historical corpus.v4 blind result remains immutable under
`fixtures/m2blind_v4/`: 7/8 accepted at frozen implementation commit
`5d3083ed83e699dbfd9da8b7226c4f4314de54be`. M2f2 treats those inputs as known
regressions and does not relabel the blind result.

Contents:

- `ir/`: two new development probes authored from already-supported assets and
  relationship vocabulary;
- `qualification/`: 69 fresh builds through pinned KiCad 10.0.6, including five
  clean builds of every V4 case and both new probes;
- `qualification/results.json`: normalized electrical, ERC, layout,
  composition, render, manifest, reproducibility, source, lock, and preservation
  evidence;
- `SUMMARY.md`: repair decision and qualification results;
- `HASHES.sha256`: hashes for the authoritative repair inputs/results and the
  preserved V4 evidence inspected during diagnosis.

`tools/make_m2f2_probes.py` deterministically authors the two IRs.
`tools/run_m2f2_qualification.py` refuses to overwrite a nonempty evidence
directory and reruns the bounded qualification.

The three Python scripts under `fixtures/m2blind_v4/` retain their historical
Ruff-format result and are excluded only by selecting active source, tests, and
new M2f2 tooling explicitly for the active formatting gate. No global Ruff rule
or formatting policy is disabled.
