"""Environment and path resolution for the Staples image POC."""

from __future__ import annotations

import os
import re
import tempfile
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

HEX_RE = re.compile(r"^#[0-9A-F]{6}$")


def running_serverless() -> bool:
    """True on Vercel/Lambda, where only the temp dir is writable."""
    return bool(os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"))

DEMO_ORDER = {
    "24639471": 1,  # ExpressMop
    "24321408": 2,  # Power Cleaner
    "24636223": 3,  # ProGel
    "990119": 4,  # Hyken
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    asset_root: Path = Path(".")
    config_dir: Path = Path("./_DEV_HANDOFF/config")
    prompt_dir: Path = Path("./_DEV_HANDOFF/prompts")
    output_dir: Path = Path("./outputs")

    app_host: str = "127.0.0.1"
    app_port: int = 8000
    log_level: str = "INFO"
    max_concurrent_shots: int = 3
    mock_mode: bool = True

    # The 2.3 GB `Staples Assets/` tree cannot ship to a serverless bundle, so
    # a missing source image degrades the SKU instead of killing startup there.
    strict_assets: bool = Field(default_factory=lambda: not running_serverless())

    higgsfield_api_key: str = ""
    higgsfield_api_secret: str = ""
    higgsfield_api_base_url: str = "https://api.higgsfield.ai"
    higgsfield_nano_banana_endpoint: str = "/nano-banana"

    # Ordered fallback chain, tried left to right. nano-banana accepts up to 8
    # product references and is the only image model that can composite them, so
    # it stays first. Soul reference takes a single reference; Soul standard is
    # prompt-only and cannot ground the product, so it is last.
    higgsfield_model_chain: str = (
        "/nano-banana,/higgsfield-ai/soul/reference,/higgsfield-ai/soul/standard"
    )
    higgsfield_max_input_images: int = 8
    higgsfield_max_retries: int = 3
    # When true, a Higgsfield failure fails the shot instead of silently
    # producing a Gemini image under a Higgsfield-branded deliverable.
    higgsfield_required: bool = False

    gemini_api_key: str = ""
    gemini_model: str = "gemini-pro-vision-latest"
    gemini_image_model: str = "nano-banana-pro-preview"
    gemini_max_retries: int = 1

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-5"
    anthropic_reasoning_effort: str = "medium"
    anthropic_max_tokens: int = 8000

    higgsfield_poll_interval_seconds: int = 3
    higgsfield_poll_timeout_seconds: int = 300

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parent.parent

    @property
    def is_serverless(self) -> bool:
        return running_serverless()

    @property
    def writable_root(self) -> Path:
        """Base for anything the app creates. Read-only deploys get the temp dir."""
        if self.is_serverless:
            return Path(tempfile.gettempdir()) / "staples-poc"
        return self.project_root

    @property
    def output_root(self) -> Path:
        path = self.output_dir
        if not path.is_absolute():
            path = (self.writable_root / path).resolve()
        return path

    @property
    def thumbnail_dir(self) -> Path:
        return self.writable_root / "assets" / "thumbnails"

    @property
    def higgsfield_models(self) -> list[str]:
        """Model chain as normalized, leading-slash paths."""
        raw = self.higgsfield_model_chain or self.higgsfield_nano_banana_endpoint
        paths: list[str] = []
        for part in raw.split(","):
            p = part.strip()
            if not p:
                continue
            if not p.startswith("/"):
                p = "/" + p
            if p not in paths:
                paths.append(p)
        return paths

    @property
    def higgsfield_configured(self) -> bool:
        return bool(self.higgsfield_api_key and self.higgsfield_api_secret)

    def resolve_asset(self, relative: str | None) -> Path | None:
        if not relative:
            return None
        # Config notes sometimes append parenthetical comments after the path.
        cleaned = relative.split("  (")[0].strip()
        root = self.asset_root
        if not root.is_absolute():
            root = (self.project_root / root).resolve()
        return (root / cleaned).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
