# sallen_key-bandpass-072

## Why this is a useful positive reference

- Canonical op-amp filter/feedback topology whose readability depends on preserving recognizable analog structure.
- Useful for evaluating left-to-right signal flow, feedback placement, and compact passive-component grouping.
- Provides a strong contrast against generic node/edge graph placement.

## Lessons for the generator

- Keep op-amp feedback and filter elements visually close to the active device.
- Preserve conventional analog signal flow and power presentation.
- Score layouts for topology recognizability in addition to crossings, bends, and total wire length.
- Treat this as positive evidence for organization, not as a coordinate template.

## Provenance

- Source: KiCad source repository, `demos/simulation/sallen_key/`
- Upstream: https://gitlab.com/kicad/code/kicad/
- Author/project: KiCad project contributors
- License: CC BY-SA 4.0
- Redistribution status: KiCad's `LICENSE.README` states that all demo files under `demos/*` are licensed under CC BY-SA 4.0.
