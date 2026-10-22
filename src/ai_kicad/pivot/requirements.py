"""Conservative natural-language intake for electrical design requirements."""

from __future__ import annotations

import re


_SUPPLY_CLAUSE = re.compile(
    r"\b(?:supply|input)\s+(?:voltage\s*)?[:=]\s*([^;\n]+)", re.IGNORECASE
)
_VOLTAGE_RANGE = re.compile(
    r"(\d+(?:\.\d+)?)\s*(?:-|–|to)\s*(\d+(?:\.\d+)?)\s*V\b", re.IGNORECASE
)
_MAX_CURRENT = re.compile(
    r"\b(?:maximum|max\.?\s+)?(?:LED|load|output)\s+current\s*[:=]?\s*"
    r"(\d+(?:\.\d+)?)\s*mA\b",
    re.IGNORECASE,
)
_PART_NUMBER = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b|\b[A-Z]{2,}\d+[A-Z0-9]*\b")


def assess_requirements(description: str) -> dict:
    """Extract only explicitly labeled facts and ask about missing or conflicting essentials."""
    if not description.strip():
        return {
            "schema_version": "requirement-assessment.v1",
            "status": "NEEDS_CLARIFICATION",
            "facts": {},
            "clarifying_questions": ["What should the circuit do, and what are its supply and load limits?"],
            "assumptions": [],
        }

    supply = [
        (float(match.group(1)), float(match.group(2)))
        for clause in _SUPPLY_CLAUSE.findall(description)
        for match in _VOLTAGE_RANGE.finditer(clause)
    ]
    currents = [float(match.group(1)) for match in _MAX_CURRENT.finditer(description)]
    parts = sorted(set(_PART_NUMBER.findall(description)))
    questions = []
    facts = {}
    if len(supply) == 1 and 0 < supply[0][0] <= supply[0][1]:
        facts["supply_voltage_min_v"], facts["supply_voltage_max_v"] = supply[0]
    elif len(supply) > 1:
        questions.append("Which supply-voltage range is authoritative? The description gives conflicting ranges.")
    else:
        questions.append("What are the minimum and maximum supply voltages? State the range explicitly.")
    if len(currents) == 1 and currents[0] > 0:
        facts["max_output_current_ma"] = currents[0]
    elif len(currents) > 1:
        questions.append("What is the maximum output or load current? The description gives multiple values.")
    else:
        questions.append("What is the maximum load/output current? It cannot be inferred from a nominal voltage.")
    if not parts or not re.search(r"\b(?:datasheet|pinout source)\b", description, re.IGNORECASE):
        questions.append("Which exact part numbers and datasheet or pinout sources define component pins and ratings?")
    else:
        facts["part_numbers"] = parts
        facts["pinout_source_mentioned"] = True

    return {
        "schema_version": "requirement-assessment.v1",
        "status": "NEEDS_CLARIFICATION" if questions else "READY_FOR_ENGINEERING_REVIEW",
        "facts": facts,
        "clarifying_questions": questions,
        "assumptions": [],
    }
