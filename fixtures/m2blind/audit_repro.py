"""Compare five clean outputs using the documented nonsemantic normalization."""

import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent


def normalized(path):
    value = path.read_text()
    if path.suffix == ".svg":
        value = re.sub(r"<title>.*?</title>", "<title/>", value, flags=re.DOTALL)
    elif path.name == "netlist.xml":
        value = re.sub(r"<source>.*?</source>", "<source/>", value)
        value = re.sub(r"<date>.*?</date>", "<date/>", value)
    elif path.name == "erc.json" and path.parent.name == "reports":
        data = json.loads(value)
        data.pop("date", None)
        value = json.dumps(data, sort_keys=True)
    elif path.parent.name == "raw" and path.suffix == ".json":
        value = re.sub(r"/runs/H[1-8]/run[1-5]\.staging/", "/runs/<RUN>/", value)
    return value.encode()


def main():
    result = json.loads((HERE / "automated_results.json").read_text())
    evidence = {
        "normalization_allowlist": [
            "KiCad SVG nonrendered title",
            "KiCad XML export source path and date",
            "KiCad ERC date",
            "raw CLI command staging path",
        ],
        "cases": {},
    }
    for key, case in result["cases"].items():
        if case["automated_status"] != "pass":
            continue
        runs = [HERE / record["output"] for record in case["runs"]]
        paths = sorted(
            str(p.relative_to(runs[0]))
            for p in runs[0].rglob("*")
            if p.is_file() and "config" not in p.parts
        )
        comparison = {}
        for relative in paths:
            if relative == "reports/manifest.json":
                continue
            hashes = [hashlib.sha256(normalized(run / relative)).hexdigest() for run in runs]
            comparison[relative] = {
                "normalized_sha256": hashes[0],
                "five_equal": len(set(hashes)) == 1,
            }
        manifests = [json.loads((run / "reports/manifest.json").read_text()) for run in runs]
        for manifest, run in zip(manifests, runs, strict=True):
            manifest["artifacts"] = [
                {**a, "sha256": hashlib.sha256(normalized(run / a["path"])).hexdigest()}
                for a in manifest["artifacts"]
            ]
        manifest_equal = all(item == manifests[0] for item in manifests[1:])
        evidence["cases"][key] = {
            "files": comparison,
            "normalized_manifest_equal": manifest_equal,
            "pass": all(item["five_equal"] for item in comparison.values()) and manifest_equal,
        }
    (HERE / "reproducibility.json").write_text(json.dumps(evidence, indent=2) + "\n")
    print({key: item["pass"] for key, item in evidence["cases"].items()})


if __name__ == "__main__":
    main()
