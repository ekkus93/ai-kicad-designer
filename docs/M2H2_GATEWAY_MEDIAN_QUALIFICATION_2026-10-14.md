# Gateway-row median distribution qualification — 2026-10-14

The previous interior-trunk source `a99961536645648582916b198cdf8fb30093f750`
passed locked KiCad 10.0.6 base (38506725053), interactions (38506725065),
structural (38506725041), development probe (38506725054), and source-matched
base/structural render transfers (38508216624, 38508485460).
Its independent 90-case comparison (38509937311) **FAILED** the same five
frozen criteria: baseline hard-defect clearance, individual hard-defect
nonworsening, routing aesthetics, repeated-structure tolerance, and mixed-case
improvement. Historical→fresh: interface violations 77→44; U-detours
691→865; branch inconsistency 1529.08→1758.95 mm. Native normalized
render inventory (38509937299) **PASSED**. No visual acceptance is claimed.

Behavior source `4f677bba22e2da49d7add36386236547fdb88b1d`
now chooses the median gateway row, clamped to an interior grid lane, instead
of the extrema midpoint for the single bounded horizontal distribution-trunk
alternative. This minimizes the sum of vertical distances to gateway rows
without expanding the eight-plan search budget or weakening obstacle,
connectivity, and canonical conductor-length checks. Metamorphic skewed-row
permutations, blocked-trunk and flat-row regressions passed locally; a broader
28-test local contract subset passed. The locked toolchain identity check
(38510122236) passed, but full source qualification and independent comparison
have **not** been established.

This documentation-only descendant requests fresh exact-source locked-KiCad
56-base/V3-8-negative ×5, I1–I6 ×5, nine structural classes ×5, and a
development composition probe. After all suites pass, repeat the independent
90-case comparison and normalized 137-case native-render inventory, then
case-by-case engineering inspection. Preserve all frozen criteria and keep
TODO sections 15–21 unchecked until independently proved.
