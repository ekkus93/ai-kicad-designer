# M2H2 Gateway-Median Independent Audit Request — 2026-10-13

This documentation-only checkpoint requests an independent frozen historical 90-case composition comparison against exact persisted qualification source `2b28f3d3535b6acf4296b310d701269a6e648c84`.

The exact source completed the three required locked-KiCad 10.0.6 five-run qualification suites: base 56 positives and V3-8 negative (run 38510201425), I1–I6 (run 38510201373), and nine structural classes (run 38510201351). The source-matched base/structural render transfers also passed (runs 38511684094 and 38513117316). Its Fast Validation static job failed solely because Ruff requested a formatting change to the gateway-row median test; this was corrected without production behavior changes in descendant `bc7d2a72d5d8198ddf3738579c8f6f9cda1029f0` and its exact-head Fast Validation is pending.

This request does not claim visual acceptance. Preserve the frozen historical corpus, independent observer thresholds, locked KiCad hashes, all previous evidence and open TODO sections 15–21. Review the independent audit results before any new acceptance claim.
