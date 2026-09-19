# Curated Positive KiCad Reference Set

This directory contains the publicly redistributable positive reference corpus
for the initial AI KiCad Designer architecture/evaluation work.

These are evidence of useful schematic/PCB organization, not coordinate templates.

| Example | Primary reason included | License |
|---|---|---|
| `Class-D` | Mixed analog/power organization and functional signal flow | CC BY-SA 4.0 |
| `sallen_key-bandpass-072` | Op-amp/filter topology and feedback organization | CC BY-SA 4.0 |
| `SensorProject_t16-pcb-main` | Hierarchy, MCU, sensors/interfaces, custom libraries, and a real PCB | GPL-3.0 |

## Local-only supplementary references

These were removed from the public corpus because redistribution provenance/license
has not been established:

- `555bip`
- `FullAdd`
- `LM2576`
- `LM3886`

When present locally they live under:

`.local/examples-good-unverified/`

Do not recommit them until their source and redistribution status are verified.
