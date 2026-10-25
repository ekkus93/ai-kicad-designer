"""Create an immutable RC input with a removed wire and overlapping J1 fields."""
import json
from pathlib import Path

from ai_kicad.pivot.schematic_review import MoveField, file_hash, write_json
from ai_kicad.pivot.schematic_review_native import (
    NativeSchematicEngine, _top_level_forms, edit_schematic_text,
)
from ai_kicad.sexpr import children, one, parse

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
DESIGN = ROOT / 'fixtures/pivot/experiments/ai_topology_holdout_2026-10-24_devstral_v4_run1/native/ai_rc_lowpass_m2b.json'
LAUNCHER = Path('/home/phil/Applications/kicad-10.0.6/AppDir/AppRun')

def main():
    intended = json.loads(DESIGN.read_text())
    write_json(HERE / 'intended_rc.json', intended)
    engine = NativeSchematicEngine(intended, LAUNCHER)
    pristine_dir = HERE / 'pristine_rc'
    pristine_dir.mkdir()
    pristine = engine.initial(pristine_dir)
    text = pristine.read_text()
    start, end, removed = next(form for form in _top_level_forms(text) if form[2][0] == 'wire')
    text = text[:start] + text[end:]
    text = "\n".join(line.rstrip() for line in text.splitlines()) + "\n"
    j1 = next(s for s in children(parse(text), 'symbol') if any(
        p[1:3] == ['Reference', 'J1'] for p in children(s, 'property')
    ))
    value = next(p for p in children(j1, 'property') if p[1] == 'Value')
    at = one(value, 'at')
    action = MoveField(operation='move_field', reference='J1', unit=1, field='Reference',
                       x_mm=float(at[1]), y_mm=float(at[2]), angle=int(at[3]))
    broken = HERE / 'corrupted_rc.kicad_sch'
    broken.write_text(edit_schematic_text(text, [action]))
    write_json(HERE / 'input_defects.json', {
        'pristine_sha256': file_hash(pristine), 'corrupted_sha256': file_hash(broken),
        'removed_wire': removed, 'overlap_action': action.model_dump(mode='json'),
        'purpose': 'Deliberate test input only. The review loop must autonomously repair and re-review it.',
    })

if __name__ == '__main__':
    main()
