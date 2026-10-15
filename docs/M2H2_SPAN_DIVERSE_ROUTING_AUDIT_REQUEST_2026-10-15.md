# Independent M2h2 span-diverse routing audit request — 2026-10-15

Source-matched qualification root: `1d3d97f3711daf063507ede327ca6b46c75b19e8`.
The 56-base five-run qualification (38747939763), I1–I6 five-run interactions (38747939561), and nine structural-class five-run qualification (38747939632) all passed at this exact source. The pinned KiCad 10.0.6 diagnostic (38747939665), development probe (38747939567), base native-render transfer (38751149076), and structural native-render transfer (38753627003) passed as well.

Fast Validation (38747939917) failed the Ruff source formatting check, not electrical or native qualification. The source formatting was corrected in `5234d4c767e548a9f1b8570de9cc1ee09d1b0cf4`; the subsequent Fast Validation (38756204749) exposed an additional Ruff-only test formatting failure. Do not claim all CI green, or treat an audit PASS as final engineering visual acceptance.

Request the independent original 90-case preserved-baseline comparison and 137-case × five-run normalized native-render inventory against the **exact existing qualified evidence root** `$HOME/m2h2-evidence/1d3d97f3711daf063507ede327ca6b46c75b19e8/`. This is a diagnostic request; the last comparison failed five frozen criteria. Do not modify historical baselines, thresholds, observers, or TODO sections 15–21. Retain all per-case witnesses and metric vectors.
