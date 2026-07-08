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

import logging
from typing import Optional

_log = logging.getLogger(__name__)

import google.auth.credentials
from google import genai
from google.genai.chats import Chat
from google.genai.types import GenerateContentConfig, ThinkingConfig
from google.genai.types import ThinkingLevel as SDKThinkingLevel

from gemini_bridge.config import Config, ThinkingLevel

# Thinking budget token counts for Gemini 2.x models
_THINKING_BUDGET_2X: dict[str, int] = {
    "none": 0,
    "low": 1024,
    "medium": 8192,
    "high": 32768,
}

# Thinking level enum values for Gemini 3.x models
_THINKING_LEVEL_3X: dict[str, SDKThinkingLevel] = {
    "none": SDKThinkingLevel.MINIMAL,
    "low": SDKThinkingLevel.LOW,
    "medium": SDKThinkingLevel.MEDIUM,
    "high": SDKThinkingLevel.HIGH,
}


class ClientError(Exception):
    """Raised when a Gemini inference or session operation fails."""


class GeminiClient:
    """Manages persistent Gemini chat sessions and provides a unified ask() interface."""

    def __init__(
        self,
        config: Config,
        credentials: Optional[google.auth.credentials.Credentials] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self._config = config
        if api_key:
            self._raw_client = genai.Client(api_key=api_key)
        else:
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

    @property
    def default_thinking(self) -> ThinkingLevel:
        return self._config.default_thinking

    def _build_generation_config(
        self,
        thinking: ThinkingLevel,
        system_instruction: Optional[str] = None,
    ) -> GenerateContentConfig:
        model = self._config.model
        si = {"system_instruction": system_instruction} if system_instruction else {}
        if model.startswith("gemini-2."):
            return GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_budget=_THINKING_BUDGET_2X[thinking]),
                **si,
            )
        if model.startswith("gemini-3."):
            return GenerateContentConfig(
                thinking_config=ThinkingConfig(thinking_level=_THINKING_LEVEL_3X[thinking]),
                **si,
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
        system_instruction: Optional[str] = None,
    ) -> str:
        """Send prompt to chat session, return response text. Raises ClientError on failure."""
        effective_thinking: ThinkingLevel = thinking or self._config.default_thinking
        gen_config = self._build_generation_config(effective_thinking, system_instruction)
        _log.debug("ask: thinking=%s prompt_len=%d", effective_thinking, len(prompt))
        try:
            response = session.send_message(prompt, config=gen_config)
        except Exception as exc:
            _log.error("inference failed: %s", exc)
            raise ClientError(f"Gemini inference failed: {exc}") from exc
        if not response.text:
            _log.warning("Gemini returned an empty response")
            raise ClientError("Gemini returned an empty response.")
        _log.debug("response_len=%d", len(response.text))
        return response.text
