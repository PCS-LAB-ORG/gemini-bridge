"""
gemini_bridge/auth.py
---------------------
Credential loading for all supported authentication methods.

Responsibilities:
  - Load Application Default Credentials (ADC) — default method
  - Load service account credentials from GOOGLE_APPLICATION_CREDENTIALS env var
  - Load service account credentials from Apple Keychain (macOS)
  - Build a google.auth.credentials.Credentials instance for any configured method

Design notes:
  - Single Responsibility: credential loading only; SDK client construction is in client.py
  - Open/Closed: add a new method by adding a loader function + one entry in _LOADERS —
    build_credentials() requires no modification
  - Liskov Substitution: all paths return google.auth.credentials.Credentials; callers are agnostic
  - Dependency Inversion: client.py depends on the Credentials abstraction, not concrete loaders

Raises:
  AuthError — wraps all credential failures with actionable messages for Claude to surface

Used by:  client.py -> build_client()
Imports:  config.py (AuthConfig, ConfigError)
"""

import json
import logging
import subprocess
from typing import Callable

_log = logging.getLogger(__name__)

import google.auth
import google.auth.credentials
import google.auth.exceptions
from google.oauth2 import service_account

from gemini_bridge.config import AuthConfig, ConfigError

_VERTEX_SCOPES = ["https://www.googleapis.com/auth/cloud-platform"]

# All loaders receive the full AuthConfig so parameterized methods (keychain)
# can access their fields without special-casing in build_credentials().
_CredLoader = Callable[[AuthConfig], google.auth.credentials.Credentials]


class AuthError(Exception):
    """Raised when credential loading fails. Message is user-actionable."""


def _load_adc(auth_config: AuthConfig) -> google.auth.credentials.Credentials:
    try:
        credentials, _ = google.auth.default(scopes=_VERTEX_SCOPES)
        _log.debug("adc credentials loaded")
        return credentials
    except google.auth.exceptions.DefaultCredentialsError as exc:
        _log.error("adc credential load failed: %s", exc)
        raise AuthError(
            "Gemini auth error: no ADC credentials found.\n"
            "Fix: gcloud auth application-default login"
        ) from exc


def _load_env(auth_config: AuthConfig) -> google.auth.credentials.Credentials:
    """Load service account credentials from GOOGLE_APPLICATION_CREDENTIALS env var."""
    try:
        credentials, _ = google.auth.default(scopes=_VERTEX_SCOPES)
        _log.debug("env credentials loaded")
        return credentials
    except google.auth.exceptions.DefaultCredentialsError as exc:
        _log.error("env credential load failed: %s", exc)
        raise AuthError(
            "Gemini auth error: GOOGLE_APPLICATION_CREDENTIALS not set or file unreadable.\n"
            "Fix: export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json"
        ) from exc


def _load_keychain(auth_config: AuthConfig) -> google.auth.credentials.Credentials:
    """Load service account JSON from Apple Keychain (macOS only)."""
    # model_validator guarantees non-None when method="keychain"; or-defaults are a safety net
    service = auth_config.keychain_service or "gemini-bridge"
    account = auth_config.keychain_account or "vertex-sa"
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-a", account, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        _log.error("keychain item not found (service=%r, account=%r)", service, account)
        raise AuthError(
            f"Gemini auth error: Keychain item not found "
            f"(service={service!r}, account={account!r}).\n"
            "Fix: re-run setup.sh to store the service account key."
        ) from exc
    except FileNotFoundError as exc:
        _log.error("security CLI not found — Keychain auth requires macOS")
        raise AuthError(
            "Gemini auth error: 'security' CLI not found. Keychain auth requires macOS."
        ) from exc

    raw = result.stdout.strip()
    # macOS Keychain stores multi-line values (like SA JSON) as binary and returns
    # them as a lowercase hex string via security(1) -w. Detect and decode.
    if raw and all(c in "0123456789abcdef" for c in raw):
        try:
            raw = bytes.fromhex(raw).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            _log.error("keychain value hex decode failed: %s", exc)
            raise AuthError(
                "Gemini auth error: Keychain value could not be decoded.\n"
                "Fix: re-run setup.sh to re-store the service account key."
            ) from exc
    try:
        sa_info = json.loads(raw)
    except json.JSONDecodeError as exc:
        _log.error("keychain value is not valid JSON: %s", exc)
        raise AuthError(
            "Gemini auth error: Keychain value is not valid service account JSON.\n"
            "Fix: re-run setup.sh to re-store the service account key."
        ) from exc

    _log.debug("keychain credentials loaded (service=%r, account=%r)", service, account)

    return service_account.Credentials.from_service_account_info(sa_info, scopes=_VERTEX_SCOPES)


_LOADERS: dict[str, _CredLoader] = {
    "adc": _load_adc,
    "env": _load_env,
    "keychain": _load_keychain,
}


def build_credentials(auth_config: AuthConfig) -> google.auth.credentials.Credentials:
    """Build credentials from the given auth config. Raises AuthError on failure."""
    loader = _LOADERS.get(auth_config.method)
    if loader is None:
        raise ConfigError(f"Unknown auth method: {auth_config.method!r}")
    return loader(auth_config)
