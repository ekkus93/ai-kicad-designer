"""Native KiCad + local vision-model schematic review service for the workflow controller."""

from __future__ import annotations

import json
from pathlib import Path

from .schematic_review import OllamaSchematicReviewer, file_hash, run_schematic_review
from .schematic_review_brief import (
    brief_allows_power_symbol_rails,
    brief_requires_field_ownership,
    brief_requires_page_balance,
    brief_requires_level_power_block,
    brief_requires_power_block,
    brief_requires_text_and_ground_checks,
    brief_requires_readability_checks,
    brief_review_profile,
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
        with_images: bool = False,
        max_actions: int = 1,
        experimental_free_form_edits: bool = False,
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
        # With a text source, also send the PNG renders.
        self.with_images = with_images
        # Edits per review; above one they are applied and checked one at a time.
        self.max_actions = max_actions
        self.model_timeout_seconds = model_timeout_seconds
        self.max_field_distance_mm, self.brief_text = resolve_review_brief(review_brief, None)
        self.power_symbol_rails = brief_allows_power_symbol_rails(review_brief)
        self.readability_checks = brief_requires_readability_checks(review_brief)
        self.page_balance = brief_requires_page_balance(review_brief)
        self.field_ownership = brief_requires_field_ownership(review_brief)
        self.text_and_ground_checks = brief_requires_text_and_ground_checks(review_brief)
        self.power_block = brief_requires_power_block(review_brief)
        self.level_power_block = brief_requires_level_power_block(review_brief)
        # Brief v10: a versioned reviewer-loop profile selects the reviewer settings, the
        # edit mode and the report-only R2 thresholds (spec R0, R5).
        self.review_brief = review_brief
        self.profile = brief_review_profile(review_brief)
        self.quality_thresholds = None
        self.edit_mode = "free_form"
        if self.profile is not None:
            chosen = self.profile.reviewer.model_dump()
            defaults = {
                "svg_source": False,
                "with_images": False,
                "think": False,
                "withhold_checks": False,
                "max_actions": 1,
            }
            for name, default in defaults.items():
                passed = getattr(self, name)
                if passed != default and passed != chosen[name]:
                    raise ValueError(f"{name}={passed!r} conflicts with the brief's v10 profile")
                setattr(self, name, chosen[name])
            self.quality_thresholds = dict(self.profile.quality.thresholds)
            self.edit_mode = self.profile.edit_mode
        if experimental_free_form_edits:
            if self.profile is None:
                raise ValueError("experimental free-form edits need a brief v10 profile")
            self.edit_mode = "free_form_experimental"
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
            quality_thresholds=self.quality_thresholds,
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
            with_images=self.with_images,
            max_actions=self.max_actions,
            **({"review_brief": self.brief_text} if self.brief_text else {}),
        )
        run_record = {
            "review_brief": str(self.review_brief) if self.review_brief else None,
            "review_brief_sha256": (
                file_hash(self.review_brief)
                if self.review_brief and self.review_brief.is_file()
                else None
            ),
            "review_profile": self.profile.profile_id if self.profile else None,
            "edit_mode": self.edit_mode,
            "model": self.model,
            "model_digest": reviewer.identity.get("digest"),
            "options": {
                "context_tokens": self.context_tokens,
                "output_tokens": self.output_tokens,
                "think": self.think,
                "svg_source": self.svg_source,
                "description_source": self.description_source,
                "withhold_checks": self.withhold_checks,
                "with_images": self.with_images,
                "max_actions": self.max_actions,
                "model_timeout_seconds": self.model_timeout_seconds,
            },
            "toolchain": getattr(engine, "toolchain", None),
        }
        return run_schematic_review(
            engine,
            reviewer,
            output,
            **self.budgets,
            quality_thresholds=self.quality_thresholds,
            run_record=run_record,
        )
