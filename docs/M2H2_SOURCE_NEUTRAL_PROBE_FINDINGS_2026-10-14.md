# M2h2 source-neutral candidate probe: routing and search witnesses (2026-10-14)

This note records the exact-source [development composition probe 38620150514](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38620150514), which **PASSED** on diagnostic-documentation commit `c4b8b7825c35654400c129c016c5211007be5a18`. The behavior is unchanged from qualified source `e0da993190fc51a1ad1249c7e9a22855319c9172`. These are bounded development witnesses, **not** independent native aesthetic acceptance.

## Observations

- **V6-3:** only **one proved candidate** out of eight seeds; selected seed 1/round 2 still reports one stage inversion and one wrong-side interface. The probe logged 31 rejected attempts. Reordering candidate scores cannot fix the absence of a better proved layout; prioritize legal candidate generation, gateway escape, placement and route rejection evidence.
- **V5-3:** also only one proved candidate and 31 rejected attempts. Treat as a generic search-diversity regression control, not a fixture-specific workaround.
- **Shared rail:** four proved candidates, 28 rejected attempts; selected seed 5/round 3. Same-flow/side alternative seed 0/round 3 has identical backtracking (309) and routed union (866.14 mm), but worse support-distance preference and one more bend. This does not show a viable score-only repair for the independent local-label-disconnect regression.
- **Mixed I4 B2:** selected seed 1/round 0 has zero stage inversions and wrong-side interfaces, backtracking 88, routed union 287.02 mm and independent-output row drift 15. Four proved alternatives improve backtracking to 78 but increase routed union to 335.28 mm and independent-output row drift to 54. The first blocking production key is independent-output row drift at index 17. Do not promote the alternative without proving net visual improvement against frozen criteria.
- **V4-7:** selected seed 6/round 0 reports one inversion and one wrong-side interface; its same-flow/side alternative is worse on routed geometry cost. Generic legal search and flow repair take precedence over aesthetic tie-breakers.

## Implications for the next implementation

The latest [independent historical audit 38611663994](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38611663994) still fails five frozen criteria. The [native inventory 38611663887](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38611663887) passes. Address **candidate-generation completeness and shared-rail routing/label attribution first**, then measure route topology and repeated structure on all 90 cases. A bounded second legal interior-trunk corridor is one generic design to investigate, but it has **not** been committed, tested or qualified. Do not claim it as a fix.

Keep the KiCad pin, original baseline, observer/oracle, thresholds and TODO acceptance checkboxes unchanged. Re-run exact-source qualification and both independent audits after a production behavior change.
