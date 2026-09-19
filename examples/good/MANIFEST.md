# Curated Positive KiCad Reference Set

These projects are positive reference material for schematic and PCB organization.
They are **not** coordinate templates. The design system should infer reusable
engineering/layout principles rather than reproduce any example literally.

The initial Astra architecture pass should inspect these examples selectively,
starting from this manifest and each project's `NOTES.md`.

| Example | Primary reason included |
|---|---|
| `555bip` | Recognizable timing/feedback topology |
| `Class-D` | Mixed analog/power organization |
| `FullAdd` | Dense digital logic and repeated connectivity |
| `LM2576` | Switching-regulator / power topology |
| `LM3886` | Analog/audio amplifier signal flow |
| `SensorProject_t16-pcb-main` | Hierarchy, MCU, sensors, interfaces, and a real PCB |
| `sallen_key-bandpass-072` | Op-amp/filter topology and feedback network |

## Guidance for AI analysis

When inspecting these examples:

- identify functional blocks and their visual organization;
- identify recurring signal-flow and power-presentation conventions;
- distinguish direct wiring from sensible use of labels/buses;
- examine component orientation and grouping;
- examine how recognizable circuit motifs are made visually obvious;
- for PCB examples, examine mechanical/fixed interfaces, clustering, and
  electrically constrained placement;
- do not infer that exact coordinates, page sizes, or component spacing should
  become fixed universal rules.

## Provenance

Before redistributing any third-party design, record its original source and
license in the corresponding `NOTES.md`. A publicly visible repository does not
by itself grant redistribution permission.
