"""Native KiCad + local vision-model schematic review service for the workflow controller."""

from __future__ import annotations

import json
from pathlib import Path

from .schematic_review import OllamaSchematicReviewer, run_schematic_review
from .schematic_review_brief import resolve_review_brief
from .schematic_review_native import NativeSchematicEngine


class NativeSchematicReviewService:
    """Generate, check, render, review, edit and re-review one supported M2b design."""

    def __init__(
        self,
        launcher: Path,
        model: str,
        *,
        review_brief: Path | None = None,
        max_reviews: int = 8,
        max_seconds: float = 1800,
        max_model_tokens: int = 120_000,
        context_tokens: int = 16384,
    ):
        self.launcher = launcher
        self.model = model
        self.context_tokens = context_tokens
        self.max_field_distance_mm, self.brief_text = resolve_review_brief(review_brief, None)
        # The loop checks its wall-clock budget between operations; one KiCad or model call
        # may still be running when it expires.
        self.timeout_seconds = max_seconds + 600
        self.budgets = {
            "max_reviews": max_reviews,
            "max_seconds": max_seconds,
            "max_model_tokens": max_model_tokens,
        }

    def review(self, design: Path, output: Path) -> dict:
        engine = NativeSchematicEngine(
            json.loads(design.read_text()),
            self.launcher,
            maximum_field_distance_mm=self.max_field_distance_mm,
        )
        reviewer = OllamaSchematicReviewer(
            self.model,
            context_tokens=self.context_tokens,
            **({"review_brief": self.brief_text} if self.brief_text else {}),
        )
        return run_schematic_review(engine, reviewer, output, **self.budgets)
