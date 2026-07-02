"""
gemini_bridge/config.py
-----------------------
Load and validate configuration from ~/.config/gemini-bridge/config.json.

Responsibilities:
  - Define Config and AuthConfig pydantic models
  - Load config from the standard path (~/.config/gemini-bridge/config.json)
  - Provide sensible defaults for all optional fields
  - Raise ConfigError with actionable messages on validation failure

Design notes:
  - Single Responsibility: config loading/validation only; no credentials, no SDK init
  - Open/Closed: add a new field to Config — nothing else changes
  - Dependency Inversion: callers depend on Config/AuthConfig types, not on JSON schema

Raises:
  ConfigError — wraps all config load/parse/validation failures

Used by:  auth.py, client.py, transcript.py, server.py
Imports:  (stdlib + pydantic only)
"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, field_validator

CONFIG_PATH: Path = Path.home() / ".config" / "gemini-bridge" / "config.json"

ThinkingLevel = Literal["none", "low", "medium", "high"]
AuthMethod = Literal["adc", "env", "keychain"]


class ConfigError(Exception):
    """Raised when config cannot be loaded or validated."""


class AuthConfig(BaseModel):
    method: AuthMethod = "adc"
    keychain_service: str = "gemini-bridge"
    keychain_account: str = "vertex-sa"


class Config(BaseModel):
    project: str
    location: str = "us-central1"
    model: str = "gemini-2.5-flash"
    default_thinking: ThinkingLevel = "medium"
    transcript_dir: str = "~/session-summaries"
    auth: AuthConfig = AuthConfig()

    @field_validator("model")
    @classmethod
    def model_family_recognized(cls, v: str) -> str:
        if not (v.startswith("gemini-2.") or v.startswith("gemini-3.")):
            raise ValueError(
                f"Unrecognized model family: {v!r}. Expected 'gemini-2.*' or 'gemini-3.*'."
            )
        return v


def load_config(path: Path = CONFIG_PATH) -> Config:
    """Load and validate config from path. Raises ConfigError on any failure."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}\n" "Run 'bash setup.sh' to create it.")
    try:
        raw = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config file is not valid JSON ({path}): {exc}") from exc
    try:
        return Config(**raw)
    except Exception as exc:
        raise ConfigError(f"Config validation failed: {exc}") from exc
