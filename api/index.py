"""Vercel serverless entrypoint.

Vercel bundles this module and serves the exported ASGI `app`. The project root
must be importable before `app.main` is resolved, because the function's working
directory is not guaranteed to be on `sys.path`.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import app  # noqa: E402

__all__ = ["app"]
