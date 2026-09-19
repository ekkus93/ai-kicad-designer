# SensorProject_t16-pcb-main

## Why this is a useful positive reference

- Real multi-sheet KiCad project with MCU, sensors/interfaces, power, radio, custom symbols/footprints, and an actual PCB.
- Useful for hierarchy, repeated channels, interface organization, mechanical constraints, and PCB placement.
- The upstream project describes the hardware as a working prototype.

## Lessons for the generator

- Treat hierarchy and repeated functional channels as first-class design concepts.
- Separate logical schematic organization from physical PCB placement constraints.
- Preserve fixed/semi-fixed interfaces and electrically constrained component relationships explicitly in the IR.

## Provenance

- Source: https://github.com/pdgilbert/SensorProject_t16-pcb
- Author/project: pdgilbert / SensorProject_t16-pcb
- License: GPL-3.0
- Redistribution status: Upstream repository explicitly declares GPL-3.0; retain attribution and license material when redistributing.
