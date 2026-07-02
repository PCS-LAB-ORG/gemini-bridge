"""
gemini_bridge/tools/base.py
----------------------------
Shared type definitions and helper for all MCP tools.

Responsibilities:
  - Define ToolResult type alias (return type for all tool handlers)
  - Define ThinkingParam type alias (optional thinking level parameter)
  - Provide call_gemini() helper that combines ask() + transcript append

Design notes:
  - Interface Segregation: tools import only what they need from here; no server/config exposure
  - Single Responsibility: shared plumbing only — no tool-specific logic lives here
  - Liskov Substitution: all tools return ToolResult; callers are agnostic to which tool ran

Raises:
  (none directly) — call_gemini() surfaces ClientError messages as ToolResult strings

Used by:  tools/ask.py, tools/brainstorm.py, tools/review.py, tools/debug.py, tools/architect.py
Imports:  client.py (GeminiClient), transcript.py (TranscriptWriter), config.py (ThinkingLevel)
"""

import logging
from typing import Optional

from gemini_bridge.client import ClientError, GeminiClient

_log = logging.getLogger(__name__)
from gemini_bridge.config import ThinkingLevel
from gemini_bridge.transcript import TranscriptWriter

# Return type for all MCP tool handlers.
ToolResult = str

# Optional thinking level parameter type accepted by every tool.
ThinkingParam = Optional[ThinkingLevel]


def call_gemini(
    client: GeminiClient,
    transcript: TranscriptWriter,
    tool_name: str,
    session_name: str,
    system_instruction: str,
    prompt: str,
    thinking: ThinkingParam,
) -> ToolResult:
    """Get a session, call ask(), log to transcript, return response or error string."""
    session = client.get_or_create_session(
        name=f"{tool_name}:{session_name}",
        system_instruction=system_instruction,
    )
    effective_thinking: ThinkingLevel = thinking or client._config.default_thinking
    _log.debug("%s session=%r thinking=%s", tool_name, session_name, effective_thinking)
    try:
        response = client.ask(session, prompt, thinking)
    except ClientError as exc:
        _log.error("%s session=%r failed: %s", tool_name, session_name, exc)
        return f"[gemini-bridge error] {exc}"

    _log.debug("%s session=%r OK", tool_name, session_name)
    transcript.append(
        tool_name=tool_name,
        prompt=prompt,
        response=response,
        thinking=effective_thinking,
        session=session_name,
    )
    return response
