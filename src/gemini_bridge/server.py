"""
gemini_bridge/server.py
------------------------
MCP server construction and tool registration.

Responsibilities:
  - Build the FastMCP server instance
  - Accept pre-constructed GeminiClient and TranscriptWriter (injected by __main__.py)
  - Register all 5 tools by calling each tool module's register() function
  - Return the configured server instance for running

Design notes:
  - Single Responsibility: server wiring only; no config loading, no credential logic
  - Open/Closed: add a new tool by importing its register() + one function call — nothing else changes
  - Dependency Inversion: depends on GeminiClient and TranscriptWriter abstractions, not concrete init

Raises:
  (none) — startup errors surface from __main__.py where they are caught and reported

Used by:  __main__.py -> build_server()
Imports:  client.py (GeminiClient), transcript.py (TranscriptWriter), tools/__init__.py
"""

from mcp.server.fastmcp import FastMCP

from gemini_bridge.client import GeminiClient
from gemini_bridge.tools import (
    register_architect,
    register_ask,
    register_brainstorm,
    register_debug,
    register_review,
)
from gemini_bridge.transcript import TranscriptWriter

_SERVER_NAME = "gemini-bridge"


def build_server(client: GeminiClient, transcript: TranscriptWriter) -> FastMCP:
    """Construct and return the configured MCP server with all tools registered."""
    mcp = FastMCP(_SERVER_NAME)
    register_ask(mcp, client, transcript)
    register_brainstorm(mcp, client, transcript)
    register_review(mcp, client, transcript)
    register_debug(mcp, client, transcript)
    register_architect(mcp, client, transcript)
    return mcp
