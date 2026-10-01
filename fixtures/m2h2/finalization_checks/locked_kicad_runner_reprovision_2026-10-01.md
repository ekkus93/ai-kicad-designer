# Locked KiCad runner reprovision trigger — 2026-10-01

The self-hosted runner was externally reprovisioned with the KiCad 10.0.6 AppImage extracted at `/tmp/AppDir` after exact-head run `36826283840` demonstrated that the AppDir was absent.

Before this commit, the operator verified that all six files required by `fixtures/m1a/toolchain.lock.json` exist and their SHA-256 values match the current lock exactly:

- `/tmp/AppDir/AppRun`: `5587d7de2c45df07c3de73f4679dba77f73020a30d8e8a651a0779ceb08d86de`
- `/tmp/AppDir/shared/bin/kicad-cli`: `1108ea3589e75aa274ad754275709da326f89614a9c6ce6fc456a430ef1a4b`
- `/tmp/AppDir/sharun`: `18d970f56eca2c527ffd3993b161b6bc340055129db14b394a77cb67d8bbfff9`
- `/tmp/AppDir/shared/lib/tmp/AppDir/usr/lib/x86_64-linux-gnu/libkicommon.so.10.0.6`: `d54242838ca9d3aefe71be3231b2cc48325b7f7ea923275425b1b354db92bb58`
- `/tmp/AppDir/shared/lib/libwx_gtk3u_core-3.3.so.2.0.0`: `d8793fd9231492e7f1c345a1c73ec2d1ab94a61e4712b749f8287a671d525775`
- `/tmp/AppDir/shared/lib/libwx_baseu-3.3.so.2.0.0`: `66008083d2c349c078280a573443a2c246724e26e938a18256337dfea3c68645`

This note is not qualification evidence. Its purpose is to record the external runner-state transition and trigger exact-head CI, whose locked-runner result remains authoritative for current-source pytest and M2h2 real-tool evidence.
