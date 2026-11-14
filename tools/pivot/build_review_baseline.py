"""Build the brief-v10 baseline corpus, injected-defect labels and a blind rating page.

Reviewer loop spec R6.1 and R6.2 (P6-011l1). The automatic parts only:

* regenerate every corpus design under the brief (default v10) and render it;
* inject the four standard readability defects into each drawing, label each from its
  injection manifest, and verify the injection produced an observable change (the drawing
  and its rendered image both change, and the moved text or sheet moved at least one grid
  step). An injection that changes nothing visible is not a positive case;
* choose the stratified hand-check sample of injected labels (20 %, at least 2 per
  category, plus every ambiguous probe), recorded as PENDING for the owner;
* write a blind rating page for the baseline drawings, whose answers save as JSON.

No drawing is labelled good here: machine checks alone would only measure agreement with
our own checks. Ratings, historical labels and the hand check are owner work.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import shutil
import subprocess

from ai_kicad.pivot.schematic_review import file_hash, write_json
from ai_kicad.pivot.schematic_review_native import edit_schematic_text
from ai_kicad.pivot.schematic_review_service import NativeSchematicReviewService
from ai_kicad.sexpr import children, one, parse
from tools.pivot.experiment_paths import create_experiment_dir
from tools.pivot.qualify_visual_review import defect_actions
from tools.pivot.run_review_loop_corpus import CORPUS

ROOT = Path(__file__).resolve().parents[2]
GRID_MM = 1.27
SAMPLE_FRACTION = 0.2
SAMPLE_MINIMUM = 2


def design_name(path: Path) -> str:
    return path.parent.name if path.name == "design.json" else path.stem


def field_position(text: str, reference: str, unit: int, name: str) -> tuple[float, float]:
    for symbol in children(parse(text), "symbol"):
        props = {prop[1]: prop for prop in children(symbol, "property")}
        if (
            "Reference" in props
            and props["Reference"][2] == reference
            and int(one(symbol, "unit")[1]) == unit
            and name in props
        ):
            at = one(props[name], "at")
            return float(at[1]), float(at[2])
    raise KeyError(f"{reference} unit {unit} has no {name} field")


def injected_label(
    case: str, design: str, kind: str, action: dict, base: dict, after: dict, text: str
) -> dict:
    """The label of one injected defect, from its manifest, with its verification."""
    if action["operation"] == "move_field":
        part = {key: action[key] for key in ("reference", "unit", "field")}
        before = field_position(text, action["reference"], action["unit"], action["field"])
        moved = max(abs(action["x_mm"] - before[0]), abs(action["y_mm"] - before[1]))
        location = {"x_mm": action["x_mm"], "y_mm": action["y_mm"], "from_mm": list(before)}
    else:
        part = {"sheet": True}
        moved = max(abs(action["dx_mm"]), abs(action["dy_mm"]))
        location = {"dx_mm": action["dx_mm"], "dy_mm": action["dy_mm"]}
    revision_changed = after["revision"] != base["revision"]
    image_changed = after["image_sha256"] != base["image_sha256"]
    observable = revision_changed and image_changed and moved >= GRID_MM
    return {
        "case": case,
        "design": design,
        "defect_type": kind,
        "part": part,
        "location": location,
        "label_source": "injection_manifest",
        "injection_action": action,
        "base_revision": base["revision"],
        "injected_revision": after["revision"],
        "verification": {
            "revision_changed": revision_changed,
            "image_changed": image_changed,
            "moved_mm": round(moved, 3),
            "observable": observable,
            "checks_changed": sorted(
                name for name, value in after["checks"].items() if base["checks"].get(name) != value
            ),
        },
        "positive_case": observable,
    }


def hand_check_sample(labels: list[dict]) -> list[dict]:
    """A stratified 20 % sample (at least 2 per category) plus every ambiguous probe."""
    chosen: dict[str, str] = {}
    for kind in sorted({label["defect_type"] for label in labels}):
        group = sorted(
            (label for label in labels if label["defect_type"] == kind),
            key=lambda label: hashlib.sha256(label["case"].encode()).hexdigest(),
        )
        count = min(len(group), max(SAMPLE_MINIMUM, math.ceil(SAMPLE_FRACTION * len(group))))
        for label in group[:count]:
            chosen[label["case"]] = "stratified sample"
    for label in labels:
        verification = label["verification"]
        if not verification["observable"] or not verification["checks_changed"]:
            chosen[label["case"]] = "ambiguous probe: " + (
                "no observable change" if not verification["observable"] else "no check changed"
            )
    return [
        {"case": case, "reason": reason, "status": "PENDING_OWNER_CHECK"}
        for case, reason in sorted(chosen.items())
    ]


def rating_page(items: list[dict]) -> str:
    """A self-contained blind rating page; answers download as JSON."""
    cards = []
    for item in items:
        code = html.escape(item["code"])
        images = "".join(
            f'<img src="{html.escape(path)}" alt="drawing {code}">' for path in item["images"]
        )
        cards.append(
            f'<section class="card" data-code="{code}"><h2>Drawing {code}</h2>{images}'
            f'<fieldset><label><input type="radio" name="v-{code}" value="good"> Good</label>'
            f'<label><input type="radio" name="v-{code}" value="defects"> Has defects</label>'
            f"</fieldset><p>One defect per line: part (reference, unit, pin or net); "
            f"problem; location.</p><textarea rows=4></textarea></section>"
        )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Baseline Drawing Ratings</title>
<style>
:root {{ --bg: #fff; --fg: #1c1c1c; --line: #d0d0d0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg: #161616; --fg: #e8e8e8; --line: #444; }} }}
body {{ background: var(--bg); color: var(--fg); font: 15px/1.5 system-ui, sans-serif;
  margin: 0 auto; max-width: 1100px; padding: 16px; }}
.card {{ border: 1px solid var(--line); border-radius: 6px; margin: 16px 0; padding: 12px; }}
img {{ max-width: 100%; background: #fff; display: block; margin: 8px 0; }}
textarea, input[type=text] {{ width: 100%; box-sizing: border-box; }}
</style></head><body>
<h1>Baseline drawing ratings</h1>
<p>Rate each drawing on its own: is it a good, readable schematic of its circuit, or
does it have defects? Do not compare with other ratings. Codes hide the design order.</p>
<p><label>Rater <input type="text" id="rater" placeholder="owner or chatgpt"></label></p>
{"".join(cards)}
<button id="save">Save ratings as JSON</button>
<script>
document.getElementById("save").onclick = () => {{
  const rater = document.getElementById("rater").value.trim() || "unnamed";
  const ratings = [...document.querySelectorAll(".card")].map(card => {{
    const code = card.dataset.code;
    const picked = card.querySelector("input[type=radio]:checked");
    const defects = card.querySelector("textarea").value.split("\\n")
      .map(line => line.trim()).filter(Boolean);
    return {{code, verdict: picked ? picked.value : null, defects}};
  }});
  const data = {{schema_version: "baseline-ratings.v1", rater, ratings,
    saved_at: new Date().toISOString()}};
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)],
    {{type: "application/json"}}));
  link.download = `ratings-${{rater}}.json`;
  link.click();
}};
</script></body></html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--kicad-apprun", type=Path, required=True)
    parser.add_argument(
        "--review-brief",
        type=Path,
        default=ROOT / "fixtures/pivot/schematic_review_brief_v10.json",
    )
    parser.add_argument("--designs", nargs="*")
    args = parser.parse_args()
    root = create_experiment_dir(ROOT, args.experiment_id)
    service = NativeSchematicReviewService(
        args.kicad_apprun, "unused", review_brief=args.review_brief.resolve()
    )
    drawings, labels, failures = [], [], []
    for design in CORPUS:
        name = design_name(design)
        if args.designs and name not in args.designs:
            continue
        engine = service.engine(design)
        directory = root / "drawings" / name
        directory.mkdir(parents=True)
        try:
            source = engine.initial(directory)
            assessment = engine.assess(source, directory)
        except (OSError, RuntimeError, ValueError, KeyError) as error:
            failures.append({"design": name, "error": str(error)})
            print(name, "FAILED", error, flush=True)
            continue
        base = {
            "revision": assessment.revision,
            "image_sha256": assessment.image_hashes,
            "checks": assessment.report["checks"],
        }
        drawings.append(
            {
                "design": name,
                "design_file": str(design.relative_to(ROOT)),
                "schematic": str(source.relative_to(root)),
                "images": [str(path.relative_to(root)) for path in assessment.images],
                **base,
            }
        )
        text = source.read_text()
        for kind, action in defect_actions(text).items():
            case = f"{name}__{kind}"
            injected_dir = root / "injected" / case
            target = injected_dir / "project" / source.name
            target.parent.mkdir(parents=True)
            target.write_text(edit_schematic_text(text, [action]))
            injected = engine.assess(target, injected_dir)
            after = {
                "revision": injected.revision,
                "image_sha256": injected.image_hashes,
                "checks": injected.report["checks"],
            }
            labels.append(
                injected_label(case, name, kind, action.model_dump(mode="json"), base, after, text)
            )
        print(name, "checks", base["checks"], flush=True)
    order = sorted(drawings, key=lambda item: hashlib.sha256(item["revision"].encode()).hexdigest())
    blind = []
    (root / "blind").mkdir()
    for number, item in enumerate(order, start=1):
        item["code"] = f"B{number:02d}"
        # Copies named by code only, so the page's image paths do not name the design.
        copies = []
        for index, image in enumerate(item["images"], start=1):
            copy = root / "blind" / f"{item['code']}_{index}.png"
            shutil.copyfile(root / image, copy)
            copies.append(str(copy.relative_to(root)))
        blind.append({"code": item["code"], "images": copies})
    (root / "rating_page.html").write_text(rating_page(blind))
    write_json(
        root / "blind_key.json",
        {item["code"]: {"design": item["design"], "revision": item["revision"]} for item in order},
    )
    write_json(root / "injected_labels.json", {"labels": labels})
    write_json(root / "hand_check_sample.json", {"sample": hand_check_sample(labels)})
    (root / "ratings").mkdir()
    write_json(
        root / "manifest.json",
        {
            "schema_version": "review-baseline.v1",
            "source_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
            ).stdout.strip(),
            "review_brief": str(args.review_brief.resolve().relative_to(ROOT)),
            "review_brief_sha256": file_hash(args.review_brief),
            "drawings": order,
            "failures": failures,
            "injected_cases": len(labels),
            "injected_positive_cases": sum(label["positive_case"] for label in labels),
            "ratings": "PENDING: save rating_page.html answers as ratings/<rater>.json",
            "historical_labels": "PENDING: hand-written by the owner",
            "hand_check": "PENDING: owner checks hand_check_sample.json",
            "known_good_set": "PENDING: only drawings the raters mark good",
        },
    )
    print(json.dumps({"drawings": len(drawings), "injected": len(labels), "failures": failures}))


if __name__ == "__main__":
    main()
