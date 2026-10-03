# Exact native and audit archive for candidate 585a4f7c

This candidate is **falsified for native long-passive-field readability**, not final M2h2 PASS. Machine audit PASS does not close the render gate. See `long_passive_field_falsification_585a4f7c.json` and the canonical TODO.

Qualification producer: `585a4f7c96b185c3a4e9db73fa13960388ea411b`. Frozen production: `f161672f761559e0e8ae7294f1c4df39fa24bebb`. Audit run: `37129767688`. All archive bytes were reconstructed from completed CI logs and SHA-256 checked before preservation. The 90 original KiCad 10.0.6 SVGs are gzip+base64 inside ten JSON bundles. Report parts contain one split gzip+base64 stream; retain index order.

Restore outside tracked evidence paths; verify every native SHA and the complete report SHA. This script needs only Python standard libraries:

```python
import base64, gzip, hashlib, json
from pathlib import Path
root = Path("fixtures/m2h2/finalization_checks")
out = Path("/tmp/m2h2-candidate-585a4f7c-restored")
out.mkdir(exist_ok=True)
for bundle in sorted((root / "final_native_585a4f7c").glob("part*.json")):
    for record in json.loads(bundle.read_text())["renders"]:
        raw = gzip.decompress(base64.b64decode(record["data"]))
        assert hashlib.sha256(raw).hexdigest() == record["svg_sha256"]
        (out / (record["case"] + ".svg")).write_bytes(raw)
parts = sorted((json.loads(p.read_text()) for p in (root / "final_audit_585a4f7c").glob("part*.json")), key=lambda p: p["index"])
assert [p["index"] for p in parts] == list(range(4))
raw = gzip.decompress(base64.b64decode("".join(p["data"] for p in parts)))
assert len(raw) == 15826956
assert hashlib.sha256(raw).hexdigest() == "c60e7b5c9e73cad42c54888ef676a239524111a4766041aedb5837ceb9adf2f3"
(out / "REPORT.json").write_bytes(raw)
```

The unmodified report intentionally retains `M2h2: INCOMPLETE`: coverage, native inspection, and checklist closure are separate gates. This archive preserves historical evidence and the actual falsification. It must not be reused as final-source evidence after the production field repair.
