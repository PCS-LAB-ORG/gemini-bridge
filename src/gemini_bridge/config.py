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
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

CONFIG_PATH: Path = Path.home() / ".config" / "gemini-bridge" / "config.json"

ThinkingLevel = Literal["none", "low", "medium", "high"]
AuthMethod = Literal["adc", "env", "keychain", "api_key"]


class ConfigError(Exception):
    """Raised when config cannot be loaded or validated."""


class AuthConfig(BaseModel):
    method: AuthMethod = "adc"
    # None for adc/env; defaults applied by validator when method="keychain"
    keychain_service: Optional[str] = None
    keychain_account: Optional[str] = None
    # Only read when method="api_key"; stores env var NAME, never the key value
    api_key_env: Optional[str] = "GEMINI_API_KEY"

    @model_validator(mode="after")
    def apply_keychain_defaults(self) -> "AuthConfig":
        if self.method == "keychain":
            if self.keychain_service is None:
                self.keychain_service = "gemini-bridge"
            if self.keychain_account is None:
                self.keychain_account = "vertex-sa"
        return self


class Config(BaseModel):
    project: Optional[str] = None  # required for adc/env/keychain; unused for api_key
    location: str = "global"
    model: str = "gemini-2.5-flash"
    default_thinking: ThinkingLevel = "medium"
    transcript_dir: str = "./session-summaries"
    auth: AuthConfig = AuthConfig()

    @field_validator("model")
    @classmethod
    def model_family_recognized(cls, v: str) -> str:
        if not (v.startswith("gemini-2.") or v.startswith("gemini-3.")):
            raise ValueError(
                f"Unrecognized model family: {v!r}. Expected 'gemini-2.*' or 'gemini-3.*'."
            )
        return v

    @model_validator(mode="after")
    def project_required_for_vertex(self) -> "Config":
        if self.auth.method != "api_key" and not self.project:
            raise ValueError(
                "'project' is required for Vertex AI auth methods (adc, env, keychain). "
                "Add it to config.json or switch to method='api_key'."
            )
        return self

    @model_validator(mode="after")
    def location_compatible_with_model(self) -> "Config":
        if self.auth.method == "api_key":
            return self  # location is unused in Developer API mode
        if self.model.startswith("gemini-3.") and self.location != "global":
            raise ValueError(
                f"Model {self.model!r} only supports location='global' on Vertex AI. "
                "Remove the location field or set it to 'global'."
            )
        return self


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
