"""Shared constants and public type aliases for the facade."""

from pathlib import Path

PITCH = 1_270_000


ROOT = Path(__file__).resolve().parents[2]


ASSETS = ROOT / "fixtures/m2a/assets"


FILES = {
    "Amplifier_Operational:NE5532": ("NE5532.kicad_sym", "LM2904.kicad_sym"),
    "Device:C": ("C.kicad_sym",),
    "Connector_Generic:Conn_01x05": ("Conn_01x05.kicad_sym",),
    "power:PWR_FLAG": ("PWR_FLAG.kicad_sym",),
}
