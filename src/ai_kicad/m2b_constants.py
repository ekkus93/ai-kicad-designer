"""Shared constants and public type aliases for the facade."""

EXTRA = {
    "Device:R": "R",
    "Device:LED": "LED",
    "Connector_Generic:Conn_01x01": "Conn_01x01",
    "Regulator_Linear:L7805": "L7805",
    "Timer:NE555D": "NE555D",
}


LOCKED_PIN_ROLES = {
    "Regulator_Linear:L7805": {"1": "IN", "2": "GND", "3": "OUT"},
    "Timer:NE555D": {
        "1": "GND",
        "2": "TRIG",
        "3": "OUT",
        "4": "~{RST}",
        "5": "CONT",
        "6": "THRES",
        "7": "DISCH",
        "8": "VCC",
    },
}


POWER_STAGE_ASSETS = {
    "Regulator_Linear:L7805": {
        "polarity": "positive",
        "roles": {"input": "IN", "output": "OUT", "reference": "GND"},
    },
}
