"""Native KiCad + local vision-model schematic review service for the workflow controller."""

from __future__ import annotations

import json
from pathlib import Path

from .schematic_review import OllamaSchematicReviewer, run_schematic_review
from .schematic_review_brief import (
    brief_allows_power_symbol_rails,
    brief_requires_field_ownership,
    brief_requires_page_balance,
    brief_requires_level_power_block,
    brief_requires_power_block,
    brief_requires_text_and_ground_checks,
    brief_requires_readability_checks,
    resolve_review_brief,
)
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
        output_tokens: int = 2048,
        model_timeout_seconds: float = 180,
        think: bool = False,
        svg_source: bool = False,
        description_source: bool = False,
        withhold_checks: bool = False,
    ):
        self.launcher = launcher
        self.model = model
        self.context_tokens = context_tokens
        self.output_tokens = output_tokens
        # Let the model reason before answering; its reasoning counts against output_tokens.
        self.think = think
        # Review the SVG source as text instead of the PNG renders.
        self.svg_source = svg_source
        # Review a plain-text description of the drawing instead of images.
        self.description_source = description_source
        # Withhold check verdicts from the reviewer; the checks still gate acceptance.
        self.withhold_checks = withhold_checks
        self.model_timeout_seconds = model_timeout_seconds
        self.max_field_distance_mm, self.brief_text = resolve_review_brief(review_brief, None)
        self.power_symbol_rails = brief_allows_power_symbol_rails(review_brief)
        self.readability_checks = brief_requires_readability_checks(review_brief)
        self.page_balance = brief_requires_page_balance(review_brief)
        self.field_ownership = brief_requires_field_ownership(review_brief)
        self.text_and_ground_checks = brief_requires_text_and_ground_checks(review_brief)
        self.power_block = brief_requires_power_block(review_brief)
        self.level_power_block = brief_requires_level_power_block(review_brief)
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
            power_symbol_rails=self.power_symbol_rails,
            readability_checks=self.readability_checks,
            page_balance=self.page_balance,
            field_ownership=self.field_ownership,
            text_and_ground_checks=self.text_and_ground_checks,
            power_block=self.power_block,
            level_power_block=self.level_power_block,
        )
        reviewer = OllamaSchematicReviewer(
            self.model,
            context_tokens=self.context_tokens,
            output_tokens=self.output_tokens,
            timeout_seconds=self.model_timeout_seconds,
            think=self.think,
            svg_source=self.svg_source,
            description_source=self.description_source,
            withhold_checks=self.withhold_checks,
            **({"review_brief": self.brief_text} if self.brief_text else {}),
        )
        return run_schematic_review(engine, reviewer, output, **self.budgets)
