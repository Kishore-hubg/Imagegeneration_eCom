"""Pydantic models for jobs, shots, and API payloads."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    completed_with_flags = "completed_with_flags"
    failed = "failed"


class ShotStatus(str, Enum):
    pending = "pending"
    generating_scene = "generating_scene"
    checking = "checking"
    designing_overlay = "designing_overlay"
    rendering = "rendering"
    compositing = "compositing"
    scaling = "scaling"
    done = "done"
    needs_review = "needs_review"
    failed = "failed"


STATUS_LABELS: dict[ShotStatus, str] = {
    ShotStatus.pending: "Waiting",
    ShotStatus.generating_scene: "Generating scene",
    ShotStatus.checking: "Checking",
    ShotStatus.designing_overlay: "Adding brand layer",
    ShotStatus.rendering: "Drawing layout",
    ShotStatus.compositing: "Compositing",
    ShotStatus.scaling: "Sizing for channels",
    ShotStatus.done: "Done",
    ShotStatus.needs_review: "Needs review",
    ShotStatus.failed: "Failed",
}


class CreateJobRequest(BaseModel):
    sku: str


class ShotRecord(BaseModel):
    shot_id: str
    label: str
    type: str
    text_provenance: str
    status: ShotStatus = ShotStatus.pending
    status_label: str = "Waiting"
    attempts: int = 0
    # Which image model actually produced the scene. Never infer this from
    # configuration — a fallback may have served the shot instead.
    scene_provider: str | None = None
    scene_model: str | None = None
    scene_notes: list[str] = Field(default_factory=list)
    scene_reference_count: int = 0
    gate_verdicts: list[dict[str, Any]] = Field(default_factory=list)
    lint_results: list[dict[str, Any]] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
    error: str | None = None
    thumbnail_url: str | None = None
    acceptance_reference_url: str | None = None
    placeholder_strings: list[str] = Field(default_factory=list)
    is_placeholder: bool = False


class JobCounts(BaseModel):
    total: int = 0
    done: int = 0
    needs_review: int = 0
    failed: int = 0
    pending: int = 0


class JobRecord(BaseModel):
    job_id: str
    sku: str
    display_name: str = ""
    status: JobStatus = JobStatus.queued
    created_at: datetime
    completed_at: datetime | None = None
    shots: list[ShotRecord] = Field(default_factory=list)
    counts: JobCounts = Field(default_factory=JobCounts)
    placeholder_count: int = 0
    mock_mode: bool = True


class SkuCard(BaseModel):
    sku: str
    display_name: str
    short_name: str
    card_label: str
    brand_ruleset: str
    hero_thumbnail_url: str
    shot_count: int
    demo_order: int
    brand_accent: str
    reference_count: int = 0
    headliner: str | None = None
    can_generate: bool = True
    unavailable_reason: str | None = None


class ReferenceShot(BaseModel):
    shot_id: str
    label: str
    type: str
    has_reference: bool
    reference_url: str | None = None
    reference_path: str | None = None


class SkuDetail(BaseModel):
    sku: str
    display_name: str
    short_name: str
    card_label: str
    brand_ruleset: str
    brand_accent: str
    brand_voice_summary: str | None = None
    brand_voice_tone: str | None = None
    hero_thumbnail_url: str
    hero_path: str
    headliner: str | None = None
    marketplace_bullets: list[str] = Field(default_factory=list)
    approved_source_note: str | None = None
    reference_shots: list[ReferenceShot] = Field(default_factory=list)
    asset_root_label: str = "Staples Assets"
