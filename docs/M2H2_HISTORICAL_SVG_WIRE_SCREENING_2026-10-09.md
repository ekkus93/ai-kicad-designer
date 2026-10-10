# Historical SVG wire screening

The committed analyzer `tools/inspect_m2h2_historical_svg_routes.py` verifies all 90 preserved historical native SVGs, then reports physical green-wire length, bounding box, bends, and branches. The tests are in `tests/test_m2h2_historical_svg_route_screening.py`.

Run from repository root:

```bash
PYTHONPATH=src:. python tools/inspect_m2h2_historical_svg_routes.py --out /tmp/historical_wire_geometry.json
PYTHONPATH=src:. pytest -q tests/test_m2h2_historical_svg_route_screening.py
```

The historical `i4__b2_mixed` SVG has a 93.98 by 52.07 mm wire bounding box, 177.8 mm of unique visible wire ink, five bends, and three branch points. The geometry review rank is 9/90 by ascending wire bounding-box area. This is only a historical screening signal: it excludes symbol/field geometry and semantic net identities, and **does not establish current-source composition acceptance or final PASS**. Retain all pending baseline, native-render, and final qualification checkboxes.
