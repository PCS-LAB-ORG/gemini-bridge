"""
gemini_bridge/__main__.py
--------------------------
Entry point: python -m gemini_bridge

Responsibilities:
  - Load config from ~/.config/gemini-bridge/config.json
  - Build credentials via auth.build_credentials()
  - Instantiate GeminiClient and TranscriptWriter
  - Build and run the MCP server
  - Report startup errors to stderr with actionable messages

Design notes:
  - Single Responsibility: startup orchestration only; all logic lives in imported modules
  - Dependency Inversion: passes ready-made Config, Credentials, Client, Transcript to server
  - Startup errors are fatal and reported clearly; runtime errors surface through tool results

Raises:
  SystemExit(1) — on config or auth failure at startup

Used by:  pyproject.toml [project.scripts], MCP registration (python -m gemini_bridge)
Imports:  config.py, auth.py, client.py, transcript.py, server.py
"""

import sys
from datetime import datetime


def main() -> None:
    startup_time = datetime.now()

    from gemini_bridge.auth import AuthError, build_credentials
    from gemini_bridge.client import GeminiClient
    from gemini_bridge.config import ConfigError, load_config
    from gemini_bridge.server import build_server
    from gemini_bridge.transcript import TranscriptWriter

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"gemini-bridge startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        credentials = build_credentials(config.auth)
    except AuthError as exc:
        print(f"gemini-bridge startup error: {exc}", file=sys.stderr)
        sys.exit(1)

    client = GeminiClient(config, credentials)
    transcript = TranscriptWriter(config.transcript_dir, startup_time)
    server = build_server(client, transcript)
    server.run()


if __name__ == "__main__":
    main()
