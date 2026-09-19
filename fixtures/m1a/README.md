# M1 divider qualification fixtures

divider.json is the reviewed three-pin divider from docs/CIRCUIT_IR_SPEC.md
section 7. divider_nc.json keeps its three connected nets and uses
Connector_Generic:Conn_01x04; J1 pin 4 has an explicit intentional NC reason
and evidence. The strict M1 profile accepts these two divider forms and rejects
future circuit families and capability fields.

The symbol files are exact definitions from the official KiCad 10.0.6 full
Linux x86-64 AppImage. Their source library is CC-BY-SA-4.0. The asset locks
record source and SHA256 for each definition. They are embedded into generated
schematics, not imported as application source code.

The local qualification executable is the official full AppImage published at
https://mirrors.mit.edu/kicad/appimage/stable/kicad-10.0.6-x86_64.AppImage.tar.
The archive SHA256 is
723b6890c60a5da962d3f4d07e0dba0f3dd2f3deb50d303f06a3d8a2ab7cf7f5.
Extract it in /tmp with tar -xf and run the extracted AppImage with
--appimage-extract there. The resulting /tmp/AppDir/AppRun, kicad-cli,
selected bundled runtime libraries, configuration and CPU/platform are checked
against toolchain.lock.json. Nothing is installed system-wide.

Create Python 3.12 .venv, install this package and the exact versions in
requirements.lock, then run either fixture with one command:

    .venv/bin/python -m ai_kicad build fixtures/m1a/divider.json \
      --target schematic \
      --assets-lock fixtures/m1a/assets.lock.json \
      --toolchain-lock fixtures/m1a/toolchain.lock.json \
      --policy-lock fixtures/m1a/policy.lock.json \
      --out build/divider

    .venv/bin/python -m ai_kicad build fixtures/m1a/divider_nc.json \
      --target schematic \
      --assets-lock fixtures/m1a/assets_nc.lock.json \
      --toolchain-lock fixtures/m1a/toolchain.lock.json \
      --policy-lock fixtures/m1a/policy.lock.json \
      --out build/divider_nc

The lock describes this fixed local Linux x86-64 environment. Recreate the
exact /tmp/AppDir path and pinned dependencies before building. A binary,
library, asset, policy, Python version or platform mismatch blocks a build.
tests/test_m1b.py runs real artifact mutations and three clean reproducibility
builds per fixture. Raw KiCad reports and SVGs retain run-specific timestamps;
the test compares their electrical content and normalized SVG geometry/text.
