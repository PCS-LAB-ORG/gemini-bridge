"""
gemini_bridge/client.py
------------------------
Gemini chat session manager and unified ask() interface.

Responsibilities:
  - Build the google-genai Client from credentials and config
  - Create and cache named Chat sessions (one per name, keyed by session_name)
  - Translate named thinking levels to model-appropriate API parameters
  - Expose ask() as the single interface all tools use

Design notes:
  - Single Responsibility: session lifecycle + inference only; credentials come in ready-made
  - Open/Closed: new session names need no code changes — sessions are created on demand
  - Interface Segregation: tools receive only GeminiClient; they cannot access config or credentials
  - Dependency Inversion: client depends on google.auth.credentials.Credentials abstraction

Raises:
  ClientError — wraps inference and session failures with context for Claude to surface

Used by:  tools/*.py (via ask()), server.py (instantiates GeminiClient at startup)
Imports:  config.py (Config, ThinkingLevel), auth.py (build_credentials)
"""

from typing import Optional

import google.auth.credentials
from google import genai
from google.genai.types import Chat, GenerateContentConfig

from gemini_bridge.config import Config, ThinkingLevel

# Thinking budget values for Gemini 2.x (integer tokens)
_THINKING_BUDGET_2X: dict[str, int] = {
    "none": 0,
    "low": 1024,
    "medium": 8192,
    "high": 32768,
}

# Thinking level enum values for Gemini 3.x
_THINKING_LEVEL_3X: dict[str, str] = {
    "none": "minimal",
    "low": "low",
    "medium": "medium",
    "high": "high",
}


class ClientError(Exception):
    """Raised when a Gemini inference or session operation fails."""


class GeminiClient:
    """Manages persistent Gemini chat sessions and provides a unified ask() interface."""

    def __init__(self, config: Config, credentials: google.auth.credentials.Credentials) -> None:
        self._config = config
        self._raw_client = genai.Client(
            vertexai=True,
            project=config.project,
            location=config.location,
            credentials=credentials,
        )
        self._sessions: dict[str, Chat] = {}

    def get_or_create_session(
        self,
        name: str = "default",
        system_instruction: Optional[str] = None,
    ) -> Chat:
        """Return existing chat session or create a new one."""
        if name not in self._sessions:
            cfg: Optional[GenerateContentConfig] = None
            if system_instruction:
                cfg = GenerateContentConfig(system_instruction=system_instruction)
            self._sessions[name] = self._raw_client.chats.create(
                model=self._config.model,
                config=cfg,
            )
        return self._sessions[name]

    def _build_generation_config(self, thinking: ThinkingLevel) -> GenerateContentConfig:
        model = self._config.model
        if model.startswith("gemini-2."):
            return GenerateContentConfig(
                thinking_config={"thinking_budget": _THINKING_BUDGET_2X[thinking]}
            )
        if model.startswith("gemini-3."):
            return GenerateContentConfig(
                thinking_config={"thinking_level": _THINKING_LEVEL_3X[thinking]}
            )
        raise ClientError(
            f"Unrecognized model family: {model!r}. "
            "Expected 'gemini-2.*' or 'gemini-3.*'. Update config.json."
        )

    def ask(
        self,
        session: Chat,
        prompt: str,
        thinking: Optional[ThinkingLevel] = None,
    ) -> str:
        """Send prompt to chat session, return response text. Raises ClientError on failure."""
        effective_thinking: ThinkingLevel = thinking or self._config.default_thinking
        gen_config = self._build_generation_config(effective_thinking)
        try:
            response = session.send_message(prompt, config=gen_config)
        except Exception as exc:
            raise ClientError(f"Gemini inference failed: {exc}") from exc
        if not response.text:
            raise ClientError("Gemini returned an empty response.")
        return response.text
