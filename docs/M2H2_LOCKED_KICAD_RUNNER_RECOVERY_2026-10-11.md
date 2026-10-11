# M2H2 locked-runner KiCad toolchain recovery — 2026-10-11

**Status:** Infrastructure restoration required; this is not a composition PASS.

At source `fc8250ddb80c8574c4239a66a49797b1920f0001`, [Fast Validation 38117316726](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316726) failed the locked-runner identity check, and [base 38117316720](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316720), [I1–I6 38117316727](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316727), and [structural 38117316704](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38117316704) all failed before substantive acceptance. The runner reports all six pinned toolchain files **missing** (`actual_sha256: null`), rather than binary hash drift. The pinned paths are in `fixtures/m1a/toolchain.lock.json`:

- `/tmp/AppDir/AppRun`
- `/tmp/AppDir/shared/bin/kicad-cli`
- `/tmp/AppDir/sharun`
- `/tmp/AppDir/shared/lib/tmp/AppDir/usr/lib/x86_64-linux-gnu/libkicommon.so.10.0.6`
- `/tmp/AppDir/shared/lib/libwx_gtk3u_core-3.3.so.2.0.0`
- `/tmp/AppDir/shared/lib/libwx_baseu-3.3.so.2.0.0`

The `/tmp` prefix is volatile. A reboot, cleanup, or eviction can remove the entire locked KiCad AppDir without changing the repository.

**Restore procedure (on the designated locked self-hosted runner):**

1. Locate the **original exact byte-identical KiCad 10.0.6 AppDir** in a trusted preserved installation or backup. Do not substitute a merely version-matched AppImage, relock to a different binary, or ignore missing libraries; all pinned SHA-256 digests must still match.
2. Restore the intact AppDir to the lock's required `/tmp/AppDir` location, preserving executable permissions and nested library paths. Consider storing an independently verified persistent **backup** outside `/tmp` for future recovery. Do not silently rewrite `fixtures/m1a/toolchain.lock.json`.
3. On that runner, from the current repository working tree run `python tools/check_m2h2_locked_toolchain.py`. It must exit 0 with `"ok": true` and an empty mismatch list. The check validates all pinned paths and SHA-256 values, platform identity, and the exact `10.0.6` CLI version probe.
4. Only after the preflight succeeds, launch new **exact-source** base 56×5 plus V3-8 negative, I1–I6×5, nine structural classes×5, native-render and independent comparative-audit workflows. Never count failed infrastructure runs as evidence of either success or a production defect.

**Source status:** The base `2a112223d70bb882277351be909464efcd17b46f` passes prior exact-head electrical and render audits, but the independent [comparative artifact audit 38115751629](https://github.com/ekkus93/ai-kicad-designer/actions/runs/38115751629) still fails six composition criteria. New source at `5b0443db2129be45e9e654bad4a112b4b8e06264` has not completed the required locked qualification. Continue functional-composition work and do not mark section 15–21 TODO items closed without new evidence.
