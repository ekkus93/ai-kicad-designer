"""Keep the reference and value fields of the rotated LED horizontal."""

from __future__ import annotations

import argparse
from pathlib import Path


def orient_led_fields(source: Path, destination: Path) -> None:
    text = source.read_text(encoding="utf-8")
    for field, value, y in (("Reference", "D1", "92.71"), ("Value", "WP7113ID", "95.25")):
        old = f'(property "{field}" "{value}" (at 167.64 {y} 0)'
        new = f'(property "{field}" "{value}" (at 167.64 {y} 90)'
        if text.count(old) != 1:
            raise ValueError(f"expected one D1 {field} field at the pinned position")
        text = text.replace(old, new, 1)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8", newline="")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    orient_led_fields(args.source, args.destination)


if __name__ == "__main__":
    main()
