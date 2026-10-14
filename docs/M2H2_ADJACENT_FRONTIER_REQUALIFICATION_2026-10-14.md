# M2h2 adjacent-lane frontier exact-source qualification — 2026-10-14

**Production source:** `8ca3571f89603b16fa5627ab93ca7b5ae44ec375`

## Source correction and fast gates

The preceding source changes addressed two independent development issues:
- `7d4c1ef2` scores only distinct neighboring return intervals on multiway conductor trunks, rather than charging nested pairwise spans.
- `a35e139d` introduces measured adjacent vertical lanes for directed interface placement when aligned slots are obstructed.
- `666ba534` preserves aligned-slot preference ahead of adjacent fallback, fixing two existing frontier-search tests, and formats new regressions.
- `8ca3571f` applies Ruff-required formatting in the bounded frontier search.

Exact production SHA `8ca3571f89603b16fa5627ab93ca7b5ae44ec375` passed all three jobs in [Fast Validation run 38600456106](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38600456106): locked-runner full pytest/current-source native regressions, hosted contracts, and Ruff/static/diff checks.

The preceding source `a35e139d` failed two frontend row-alignment assertions and Ruff formatting in [run 38553799924](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38553799924); those failures are corrected above. The development composition probe ran successfully at `8ca3571f`, but it is diagnostic only.

## Three-source matched locked KiCad gates

Request fresh exact-source runs for:

1. Fifty-six positive base cases ×5 and historical V3-8 negative.
2. All I1–I6 interaction cases ×5.
3. Nine structural-class cases ×5.

Keep the original byte-locked KiCad 10.0.6 identity, hard spread/locality and conductor-length gates, electrical partition/ERC checks, independent observer and frozen aesthetic thresholds. Do not change `corpus.v7`, start M3, or mark sections 15–21 PASS.

Following successful terminal qualification, launch the independent original 90-case comparison and native 137-case×5 reproducibility inventory from the exact persisted `$HOME/m2h2-evidence/8ca3571f89603b16fa5627ab93ca7b5ae44ec375/` source. The last historical comparator [38549388901](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38549388901) failed five criteria; no evidence yet establishes that the new source fixes them.

**Exact qualification trigger:** `[m2h2-final-qualification] [m2h2-interaction-qualification] [m2h2-structural-qualification]`.
