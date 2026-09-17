"""Job lifecycle and concurrent shot execution."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import Settings
from app.loader import AppConfig, LoadedSku
from app.models import (
    JobCounts,
    JobRecord,
    JobStatus,
    ShotRecord,
    ShotStatus,
)
from app.pipeline import router as shot_router

logger = logging.getLogger(__name__)


class AssetsUnavailableError(RuntimeError):
    """Raised when a SKU's source imagery is not present on this deployment."""

    def __init__(self, sku: str, missing: list[str]) -> None:
        self.sku = sku
        self.missing = missing
        super().__init__(f"Source assets unavailable for SKU {sku}")


class Orchestrator:
    def __init__(self, app_config: AppConfig) -> None:
        self.app_config = app_config
        self.settings = app_config.settings
        self.jobs: dict[str, JobRecord] = {}
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> JobRecord | None:
        return self.jobs.get(job_id)

    async def create_job(self, sku_id: str) -> JobRecord:
        sku = self.app_config.skus.get(sku_id)
        if not sku:
            raise KeyError(sku_id)
        if not sku.can_generate:
            raise AssetsUnavailableError(sku_id, sku.missing_assets)

        job_id = str(uuid.uuid4())
        shots: list[ShotRecord] = []
        placeholder_count = 0
        for sc in sku.enabled_shots:
            prov = str(sc.get("text_provenance", ""))
            is_ph = prov.startswith("PLACEHOLDER_POC")
            ph_strings: list[str] = []
            if is_ph:
                placeholder_count += 1
                ot = sc.get("overlay_text") or {}
                if ot.get("headline"):
                    ph_strings.append(str(ot["headline"]))
                if ot.get("body"):
                    ph_strings.append(str(ot["body"]))
            label = sc.get("brief_shot_name") or sc["shot_id"]
            ref = sc.get("_acceptance_reference_abs")
            shots.append(
                ShotRecord(
                    shot_id=sc["shot_id"],
                    label=label,
                    type=sc["type"],
                    text_provenance=prov,
                    is_placeholder=is_ph,
                    placeholder_strings=ph_strings,
                    acceptance_reference_url=(
                        f"/api/reference/{sku.sku}/{sc['shot_id']}" if ref else None
                    ),
                )
            )

        job = JobRecord(
            job_id=job_id,
            sku=sku.sku,
            display_name=sku.display_name,
            status=JobStatus.queued,
            created_at=datetime.now(timezone.utc),
            shots=shots,
            counts=JobCounts(total=len(shots), pending=len(shots)),
            placeholder_count=placeholder_count,
            mock_mode=self.settings.mock_mode,
        )
        self.jobs[job_id] = job
        self._tasks[job_id] = asyncio.create_task(self._run_job(job, sku))
        return job

    async def _run_job(self, job: JobRecord, sku: LoadedSku) -> None:
        job.status = JobStatus.running
        self._refresh_counts(job)

        output_root = self.settings.output_root
        job_dir = output_root / sku.sku / ("_MOCK" if job.mock_mode else "run") / job.job_id
        job_dir.mkdir(parents=True, exist_ok=True)

        ruleset = self.app_config.rulesets[sku.brand_ruleset]
        sem = asyncio.Semaphore(self.settings.max_concurrent_shots)

        async def one(shot_rec: ShotRecord, shot_cfg: dict[str, Any]) -> None:
            async with sem:
                await shot_router.run_shot(
                    job=job,
                    shot_rec=shot_rec,
                    shot_cfg=shot_cfg,
                    sku=sku,
                    ruleset=ruleset,
                    mock_mode=job.mock_mode,
                    output_root=output_root,
                    on_update=lambda: self._refresh_counts(job),
                )

        cfg_by_id = {s["shot_id"]: s for s in sku.enabled_shots}
        await asyncio.gather(
            *[one(sr, cfg_by_id[sr.shot_id]) for sr in job.shots],
            return_exceptions=False,
        )

        job.completed_at = datetime.now(timezone.utc)
        self._refresh_counts(job)
        if job.counts.failed and job.counts.done == 0:
            job.status = JobStatus.failed
        elif job.counts.needs_review or job.counts.failed:
            job.status = JobStatus.completed_with_flags
        else:
            job.status = JobStatus.completed

        shot_router.write_manifest(job, sku, job_dir)
        shot_router.write_package_readme(job, job_dir)
        zip_path = job_dir / "package.zip"
        shot_router.zip_package(job_dir, zip_path)
        logger.info("Job %s finished as %s", job.job_id, job.status.value)

    def _refresh_counts(self, job: JobRecord) -> None:
        counts = JobCounts(total=len(job.shots))
        for s in job.shots:
            if s.status == ShotStatus.done:
                counts.done += 1
            elif s.status == ShotStatus.needs_review:
                counts.needs_review += 1
            elif s.status == ShotStatus.failed:
                counts.failed += 1
            else:
                counts.pending += 1
        job.counts = counts

    def job_dir(self, job: JobRecord) -> Path:
        root = self.settings.output_root
        return root / job.sku / ("_MOCK" if job.mock_mode else "run") / job.job_id
