"""
gemini_bridge/__main__.py
--------------------------
Entry point: python -m gemini_bridge

Responsibilities:
  - Configure structured logging (file + stderr) before any other import runs
  - Load config from ~/.config/gemini-bridge/config.json
  - Build credentials via auth.build_credentials()
  - Instantiate GeminiClient and TranscriptWriter
  - Build and run the MCP server
  - Report startup errors with actionable messages

Design notes:
  - Single Responsibility: startup orchestration only; all logic lives in imported modules
  - Dependency Inversion: passes ready-made Config, Credentials, Client, Transcript to server
  - Logging is configured first so all downstream modules inherit the handler/formatter

Log files:
  ~/.config/gemini-bridge/logs/YYYYMMDD-gemini-bridge.log
  Daily files; 4 most recent kept; multiple sessions same day append to same file.
  Tail: tail -f ~/.config/gemini-bridge/logs/$(ls -t ~/.config/gemini-bridge/logs/*.log | head -1 | xargs basename)

Environment variables:
  GEMINI_BRIDGE_LOG_LEVEL  — DEBUG | INFO | WARNING | ERROR (default: INFO)

Raises:
  SystemExit(1) — on config or auth failure at startup

Used by:  pyproject.toml [project.scripts], MCP registration (python -m gemini_bridge)
Imports:  config.py, auth.py, client.py, transcript.py, server.py
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path

_LOG_DIR = Path.home() / ".config" / "gemini-bridge" / "logs"
_MAX_LOG_FILES = 4


def _setup_log_file(startup_time: datetime) -> logging.FileHandler:
    """Create today's log file, prune files beyond _MAX_LOG_FILES."""
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = _LOG_DIR / f"{startup_time.strftime('%Y%m%d')}-gemini-bridge.log"
    # Prune oldest files, keeping _MAX_LOG_FILES most recent
    existing = sorted(_LOG_DIR.glob("*-gemini-bridge.log"), reverse=True)
    for old in existing[_MAX_LOG_FILES:]:
        try:
            old.unlink()
        except OSError:
            pass
    return logging.FileHandler(log_file, mode="a", encoding="utf-8")


def _configure_logging(startup_time: datetime) -> None:
    """Set up file + stderr logging before any module that calls getLogger() is imported."""
    raw_level = os.environ.get("GEMINI_BRIDGE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, raw_level, logging.INFO)
    formatter = logging.Formatter(
        fmt="[gemini-bridge] %(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    root = logging.getLogger("gemini_bridge")
    root.setLevel(level)
    # File handler — primary; visible via tail
    file_handler = _setup_log_file(startup_time)
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)
    # Stderr handler — useful when running server manually; swallowed by Claude Code
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(formatter)
    root.addHandler(stderr_handler)
    # Suppress chatty third-party loggers unless in DEBUG mode
    if level > logging.DEBUG:
        logging.getLogger("google").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


_startup_time = datetime.now()
_configure_logging(_startup_time)

_log = logging.getLogger(__name__)


def main() -> None:
    startup_time = _startup_time

    from gemini_bridge.auth import AuthError, build_credentials
    from gemini_bridge.client import GeminiClient
    from gemini_bridge.config import ConfigError, load_config
    from gemini_bridge.server import build_server
    from gemini_bridge.transcript import TranscriptWriter

    try:
        config = load_config()
    except ConfigError as exc:
        _log.error("startup failed — config error: %s", exc)
        sys.exit(1)

    try:
        credentials = build_credentials(config.auth)
    except AuthError as exc:
        _log.error("startup failed — auth error: %s", exc)
        sys.exit(1)

    _log.info(
        "starting — auth=%s model=%s location=%s",
        config.auth.method,
        config.model,
        config.location,
    )

    client = GeminiClient(config, credentials)
    transcript = TranscriptWriter(config.transcript_dir, startup_time)

    _log.info("transcript → %s", transcript.path)

    server = build_server(client, transcript)
    server.run()


if __name__ == "__main__":
    main()
