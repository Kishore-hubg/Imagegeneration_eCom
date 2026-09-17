"""Run one full job through the orchestrator and check provider bookkeeping.

Usage:
  .\\.venv\\Scripts\\python.exe scripts\\verify_pipeline_job.py --mock
  .\\.venv\\Scripts\\python.exe scripts\\verify_pipeline_job.py --sku 24639471
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from app.config import get_settings
from app.loader import load_app_config
from app.orchestrator import Orchestrator
from app.pipeline import compose


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    parser.add_argument("--sku", default="24639471")
    args = parser.parse_args()

    s = get_settings()
    if args.mock:
        s.mock_mode = True

    cfg = load_app_config(s)
    await compose.start_browser()
    try:
        orch = Orchestrator(cfg)
        job = await orch.create_job(args.sku)
        print(f"job {job.job_id} mock={job.mock_mode} — running {len(job.shots)} shots")
        await orch._tasks[job.job_id]

        print(f"\nstatus: {job.status.value}  {job.counts.model_dump()}")
        print("\nprovider per shot:")
        for shot in job.shots:
            if shot.scene_provider:
                print(
                    f"  {shot.shot_id:7s} {shot.type:16s} {shot.status.value:14s} "
                    f"{shot.scene_provider}/{shot.scene_model} refs={shot.scene_reference_count}"
                )
            else:
                print(f"  {shot.shot_id:7s} {shot.type:16s} {shot.status.value:14s} (no scene)")

        job_dir = orch.job_dir(job)
        manifest = json.loads((job_dir / "manifest.json").read_text(encoding="utf-8"))
        print(f"\nmanifest scene_providers: {manifest['scene_providers']}")
        readme = (job_dir / "README.txt").read_text(encoding="utf-8")
        block = readme.split("SCENE GENERATION PROVIDER")[1].split("PLACEHOLDER COPY")[0]
        print("README provider block:")
        print("".join(f"  {line}\n" for line in block.strip().splitlines()))
        print(f"artifacts: {job_dir}")
    finally:
        await compose.stop_browser()


if __name__ == "__main__":
    asyncio.run(main())
