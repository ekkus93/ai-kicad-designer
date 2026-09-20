# M2c2 trace reference — release after responses

## Review A

VPLUS → R1 → VREF → R2 → VMINUS. U1A buffers VREF to OUT by direct negative feedback. VPLUS, VMINUS, VREF, and OUT remain separate nets; C1/C2 support the split supply.

## Review B

IN → C3 (series coupling) → FILTER → U1A non-inverting input → amplifier output OUT. R3 returns FILTER to REF; R1/R2 form local negative feedback and gain setting. C1/C2 decouple split rails.
