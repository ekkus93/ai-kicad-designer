# Baseline schematic ratings: drawings for review

**Date:** 2026-11-14. Branch `mcp`, baseline `review_baseline_v10_2026-11-14_run1` (generated at commit `25a319c9` with review brief v10).

## What this is

An AI KiCad designer generates schematics from an intended circuit (parts and nets). An automatic review loop then has a local model (Qwen) critique and edit them. Before the reviewer can be judged, we need an **independent judgment of which generated drawings are actually good**. Automatic checks can't supply it: all 15 drawings below pass every check (KiCad ERC, netlist equivalence with the intended circuit, and the layout and readability checks), and passing those checks is exactly what needs testing.

Please rate each drawing **on its own**:
- **good:** a clear, readable schematic of its intended circuit that you would accept from a careful engineer, or
- **defects:** list each problem.

## How to judge

Things to look at:
- **Electrical correctness:** does the drawing visibly match the intended circuit (parts, values, nets)?
- **Node traceability:** can you follow each net? Rails may be drawn with power symbols (supply arrows, ground glyphs); same-named power symbols are connected.
- **Power section:** are the supply rails, decoupling capacitors and op-amp power unit clear?
- **Text association:** does every reference and value sit clearly by its own part, without overlapping a wire, symbol, pin number or other text?
- **Arrangement:** are functional blocks grouped and is signal flow readable, without long detours or wires hugging the page edge?
- **Page:** is the drawing reasonably placed on the page?

Each drawing has two images: the full A4 page and a close-up of the drawing. Ignore the title block.

## Reply format

Reply with JSON in this format, one entry per drawing. Write each defect as `part (reference, unit, pin or net); problem; location`:

```json
{"schema_version": "baseline-ratings.v1", "rater": "chatgpt",
 "ratings": [
   {"code": "B01", "verdict": "good", "defects": []},
   {"code": "B02", "verdict": "defects",
    "defects": ["R2; value 10k reads as U1A's; above U1A's input wire"]}
 ]}
```

Short notes on why are welcome after the JSON.

## The drawings

### B01

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B01_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B01_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Conn_01x05
- **Nets:** IN (J1.1, U1.3); OUT (J1.2, U1.1, U1.2); VPLUS (J1.3, U1.8, C1.1); VMINUS (J1.4, U1.4, C2.2); REF (J1.5, U1.5, C1.2, C2.1); PARK (U1.6, U1.7)
- **Power rails:** REF, VMINUS, VPLUS

### B02

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B02_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B02_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Conn_01x05; R1 100k; R2 10k
- **Nets:** IN (J1.1, U1.3); OUT (J1.2, U1.1, R1.2); VPLUS (J1.3, U1.8, C1.1); VMINUS (J1.4, U1.4, C2.2); REF (J1.5, U1.5, C1.2, C2.1, R2.2); PARK (U1.6, U1.7); FB (U1.2, R1.1, R2.1)
- **Power rails:** REF, VMINUS, VPLUS

### B03

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B03_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B03_2.png

Intended circuit:

- **Parts:** U1 L7805; C1 330n; C2 100n; J1 Supply input; J2 Regulated output; J3 Return
- **Nets:** VIN (J1.1, U1.1, C1.1); VOUT (U1.3, C2.1, J2.1); REF (U1.2, C1.2, C2.2, J3.1)
- **Power rails:** REF, VIN

### B04

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B04_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B04_2.png

Intended circuit:

- **Parts:** R123 12.4k precision; D24 Amber indicator LED; J1 Input; J2 Return
- **Nets:** VPLUS (J1.1, R123.1); MID (R123.2, D24.2); REF (D24.1, J2.1)

### B05

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B05_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B05_2.png

Intended circuit:

- **Parts:** U1 NE555D; R1 10k; R2 47k; C1 10u; C2 10n; J1 Supply; J2 Pulse output; J3 Return; R3 1k; D1 WP7113ID
- **Nets:** VCC (J1.1, U1.8, U1.4, R1.1, R3.1); DISCH (R1.2, R2.1, U1.7); TIMING (R2.2, C1.1, U1.2, U1.6); OUT (U1.3, J2.1, D1.1); REF (U1.1, C1.2, C2.2, J3.1); CONT (U1.5, C2.1); LED_A (R3.2, D1.2)
- **Power rails:** REF, VCC

### B06

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B06_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B06_2.png

Intended circuit:

- **Parts:** R1 10k; C1 10n; J1 Input; J2 Output; J3 Return
- **Nets:** IN (J1.1, R1.1); OUT (R1.2, C1.1, J2.1); REF (C1.2, J3.1)

### B07

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B07_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B07_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Conn_01x05; R1 100k; R2 10k
- **Nets:** IN (J1.1, R2.1); OUT (J1.2, U1.1, R1.2); VPLUS (J1.3, U1.8, C1.1); VMINUS (J1.4, U1.4, C2.2); REF (J1.5, U1.5, C1.2, C2.1, U1.3); PARK (U1.6, U1.7); SUM (U1.2, R2.2, R1.1)
- **Power rails:** REF, VMINUS, VPLUS

### B08

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B08_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B08_2.png

Intended circuit:

- **Parts:** R1 1k; D1 LED; J1 Reference; J2 Negative supply
- **Nets:** LOCAL_REF (J1.1, R1.1); MID (R1.2, D1.2); VNEG (D1.1, J2.1)

### B09

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B09_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B09_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Conn_01x05; R1 10k; C3 10n
- **Nets:** IN (J1.1, R1.1); OUT (J1.2, U1.1, U1.2); VPLUS (J1.3, U1.8, C1.1); VMINUS (J1.4, U1.4, C2.2); REF (J1.5, U1.5, C1.2, C2.1, C3.2); PARK (U1.6, U1.7); FILTER (R1.2, C3.1, U1.3)
- **Power rails:** REF, VMINUS, VPLUS

### B10

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B10_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B10_2.png

Intended circuit:

- **Parts:** U1 NE555D; R1 10k; R2 47k; C1 10u; C2 10n; J1 Supply; J2 Pulse output; J3 Return
- **Nets:** VCC (J1.1, U1.8, U1.4, R1.1); DISCH (R1.2, R2.1, U1.7); TIMING (R2.2, C1.1, U1.2, U1.6); OUT (U1.3, J2.1); GND (U1.1, C1.2, C2.2, J3.1); CONT (U1.5, C2.1)
- **Power rails:** GND, VCC

### B11

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B11_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B11_2.png

Intended circuit:

- **Parts:** R1 1k; D1 LED; J1 Input; J2 Return
- **Nets:** VPLUS (J1.1, R1.1); MID (R1.2, D1.2); REF (D1.1, J2.1)

### B12

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B12_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B12_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Dual rail interface; R1 10k; R2 10k
- **Nets:** IN (J1.1, U1.3); OUT (J1.2, U1.1, U1.2); VPLUS (J1.3, U1.8, C1.1, R1.1); VMINUS (J1.4, U1.4, C2.2, R2.2); VREF (J1.5, U1.5, C1.2, C2.1, R1.2, R2.1); PARK (U1.6, U1.7)
- **Power rails:** VMINUS, VPLUS

### B13

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B13_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B13_2.png

Intended circuit:

- **Parts:** C1 10n; R1 10k; J1 Input; J2 Output; J3 Return
- **Nets:** IN (J1.1, C1.1); OUT (C1.2, R1.1, J2.1); REF (R1.2, J3.1)

### B14

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B14_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B14_2.png

Intended circuit:

- **Parts:** U1 NE5532; C1 100n; C2 100n; J1 Conn_01x05; R2 10k; C3 10n; R1 10k; C4 10n
- **Nets:** IN (J1.1, R1.1); OUT (J1.2, U1.1, U1.2, C4.2); VPLUS (J1.3, U1.8, C1.1); VMINUS (J1.4, U1.4, C2.2); REF (J1.5, U1.5, C1.2, C2.1, C3.2); PARK (U1.6, U1.7); FILTER (R2.2, C3.1, U1.3); INTERMEDIATE (R1.2, R2.1, C4.1)
- **Power rails:** REF, VMINUS, VPLUS

### B15

- Full page: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B15_1.png
- Close-up: https://raw.githubusercontent.com/ekkus93/ai-kicad-designer/mcp/fixtures/pivot/experiments/review_baseline_v10_2026-11-14_run1/blind/B15_2.png

Intended circuit:

- **Parts:** U1 NE555D; R1 10k; R2 47k; C1 10u; C2 10n; J1 Supply; J2 Pulse output; J3 Return
- **Nets:** VCC (J1.1, U1.8, U1.4, R1.1); DISCH (R1.2, R2.1, U1.7); TIMING (R2.2, C1.1, U1.2, U1.6); OUT (U1.3, J2.1); REF (U1.1, C1.2, C2.2, J3.1); CONT (U1.5, C2.1)
- **Power rails:** REF, VCC
