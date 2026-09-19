# M1a divider qualification fixture

`divider.json` is copied verbatim from `docs/CIRCUIT_IR_SPEC.md` section 7. The
only supported input in M1a is this exact reviewed profile. The two `.kicad_sym`
files are the official `Device:R` and `Connector_Generic:Conn_01x03` definitions
from the KiCad 10.0.6 full Linux x86-64 AppImage. Their source library is
CC-BY-SA-4.0; the lock records each file hash and origin. They are embedded in
the generated schematic, not imported as application source code.

The local qualification executable is the official full AppImage published at
`https://mirrors.mit.edu/kicad/appimage/stable/kicad-10.0.6-x86_64.AppImage.tar`.
The archive SHA256 is
`723b6890c60a5da962d3f4d07e0dba0f3dd2f3deb50d303f06a3d8a2ab7cf7f5`.
Extract it in `/tmp` with `tar -xf` and run the extracted AppImage with
`--appimage-extract` there. The resulting `/tmp/AppDir/AppRun` and underlying
`kicad-cli` binary are independently hashed in `toolchain.lock.json`.
Nothing is installed system-wide. The locked configuration registers only the
two standard libraries in the isolated KiCad config directory.

Create Python 3.12 `.venv`, install this package and the exact versions in
`requirements.lock`, then run:

```sh
.venv/bin/python -m ai_kicad build fixtures/m1a/divider.json \
  --target schematic \
  --assets-lock fixtures/m1a/assets.lock.json \
  --toolchain-lock fixtures/m1a/toolchain.lock.json \
  --policy-lock fixtures/m1a/policy.lock.json \
  --out build/m1a
```

The lock describes this local Linux x86-64 environment. Recreate the exact
`/tmp/AppDir` path and pinned dependencies before using it. A build rejects a
binary, asset, policy, or Python version mismatch.
