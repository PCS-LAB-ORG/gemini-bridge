"""
gemini_bridge/transcript.py
----------------------------
Append tool exchanges to a session transcript file in Markdown format.

Responsibilities:
  - Determine the transcript file path from config.transcript_dir and startup timestamp
  - Create the transcript directory if it does not exist
  - Append each exchange (tool name, thinking level, session, prompt, response) as Markdown
  - Fail silently on write errors so a transcript failure never breaks a tool call

Design notes:
  - Single Responsibility: transcript writing only; no Gemini calls, no config loading
  - Open/Closed: exchange format is isolated in _format_exchange(); changing format touches one fn
  - Transcript file is opened in append mode per exchange — no persistent file handle needed

Raises:
  (none) — write errors are caught and logged to stderr; tool calls must not fail due to I/O

Used by:  tools/*.py (via append_exchange() after each Gemini response)
Imports:  config.py (Config)
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)


class TranscriptWriter:
    """Writes tool exchanges to a Markdown transcript file for the current server session."""

    def __init__(self, config_transcript_dir: str, startup_time: datetime) -> None:
        transcript_dir = Path(config_transcript_dir).expanduser().resolve()
        transcript_dir.mkdir(parents=True, exist_ok=True)
        filename = startup_time.strftime("%Y%m%d-%H%M-gemini-transcript.md")
        self._path = transcript_dir / filename

    @property
    def path(self) -> Path:
        return self._path

    def append(
        self,
        tool_name: str,
        prompt: str,
        response: str,
        thinking: str,
        session: str = "default",
        timestamp: Optional[datetime] = None,
    ) -> None:
        """Append one exchange to the transcript. Never raises — write errors go to stderr."""
        ts = timestamp or datetime.now()
        block = _format_exchange(tool_name, prompt, response, thinking, session, ts)
        try:
            with self._path.open("a", encoding="utf-8") as fh:
                fh.write(block)
        except OSError as exc:
            _log.warning("transcript write failed: %s", exc)


def _format_exchange(
    tool_name: str,
    prompt: str,
    response: str,
    thinking: str,
    session: str,
    timestamp: datetime,
) -> str:
    ts_str = timestamp.strftime("%H:%M:%S")
    return (
        f"\n## [{ts_str}] {tool_name} — thinking: {thinking} | session: {session}\n\n"
        f"**Prompt:**\n{prompt}\n\n"
        f"**Response:**\n{response}\n\n"
        "---\n"
    )
