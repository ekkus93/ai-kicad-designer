# Product Goal

Build an AI-assisted electronic design system that can take a user from a natural-language circuit-design conversation to a validated, professional-quality KiCad project and ultimately to manufacturing and assembly artifacts.

The architectural boundary is intentional:

```text
user intent / engineering conversation
        -> LLM reasoning
        -> structured Circuit IR
        -> deterministic EDA pipeline
        -> KiCad project
        -> ERC / DRC / review
        -> fabrication + assembly outputs
```

The LLM may reason about requirements, circuit topology, component selection, functional blocks, electrical semantics, constraints, and revisions to Circuit IR. It must not be responsible for directly emitting final KiCad S-expressions or thousands of raw schematic/PCB coordinates.

The immediate priority is the EDA core, especially schematic quality. Generated schematics must be electrically faithful and should look intentionally drafted by a competent electrical engineer: recognizable functional blocks, sensible signal flow, conventional power presentation, coherent grouping, readable spacing, minimal unnecessary crossings, and disciplined use of wires and labels.

PCB placement is a separate optimization problem. The system must eventually represent and enforce mechanical, electrical, signal-integrity, thermal, manufacturing, and assembly constraints without deriving PCB coordinates from schematic coordinates.

The final product should be able to produce normal KiCad project files plus fabrication and assembly deliverables such as Gerbers, drill files, BOM, and component-position data. Project-local symbol/footprint libraries should be generated only when genuinely necessary.

Do not prioritize a web UI, authentication, job infrastructure, or deployment until the deterministic EDA pipeline demonstrates strong schematic quality and a credible PCB-placement path.
