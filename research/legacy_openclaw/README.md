# Legacy OpenClaw KiCad Reference Snapshot

This directory is a deliberately curated reference from the earlier `openclaw_kicad_pcb` project.

It is **not** the source tree of the new application and must not be treated as the governing architecture. It exists so architecture/reimplementation work can reuse proven low-level ideas and tests without inheriting the old system wholesale.

Included because they are potentially reusable or diagnostically valuable:

- KiCad S-expression parsing/serialization
- schematic and PCB document manipulation primitives
- legacy Circuit IR schema and semantic validation
- electrical-equivalence checking
- symbol/library helpers
- schematic readability metrics
- corpus/evaluation machinery
- focused tests documenting those behaviors
- selected design notes

Intentionally omitted from the new project bootstrap:

- FastAPI/React web application
- LLM provider clients and wizard/session persistence
- Graphviz layout engine
- old schematic router/placement implementation
- AI visual-refinement loop
- OpenClaw skill/CLI scaffolding
- accumulated hardening/TODO/review documents
- generated CI/review artifacts

The omission is intentional: Astra should be free to design a better EDA architecture rather than being anchored to the old layout implementation.

The copied reference code retains the license from the source project; see `LICENSE` in this directory.
