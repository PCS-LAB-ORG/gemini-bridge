"""Tests for gemini_bridge/client.py — GeminiClient session management and ask()."""

from unittest.mock import MagicMock, patch

import pytest
from gemini_bridge.client import _MAX_SESSIONS, DEFAULT_MODEL, ClientError, GeminiClient
from gemini_bridge.config import Config


def _make_client() -> GeminiClient:
    config = Config(project="test-project")
    mock_creds = MagicMock()
    with patch("google.genai.Client"):
        return GeminiClient(config, mock_creds)


class TestSessionManagement:
    def test_get_or_create_session_creates_new(self) -> None:
        client = _make_client()
        mock_chat = MagicMock()
        client._raw_client.chats.create.return_value = mock_chat

        session = client.get_or_create_session("default", "You are helpful.")
        assert session is mock_chat
        client._raw_client.chats.create.assert_called_once()

    def test_get_or_create_session_returns_existing(self) -> None:
        client = _make_client()
        mock_chat = MagicMock()
        client._raw_client.chats.create.return_value = mock_chat

        s1 = client.get_or_create_session("default")
        s2 = client.get_or_create_session("default")
        assert s1 is s2
        client._raw_client.chats.create.assert_called_once()

    def test_different_session_names_create_separate_sessions(self) -> None:
        client = _make_client()
        chat_a, chat_b = MagicMock(), MagicMock()
        client._raw_client.chats.create.side_effect = [chat_a, chat_b]

        sa = client.get_or_create_session("ask:default")
        sb = client.get_or_create_session("brainstorm:default")
        assert sa is not sb

    def test_different_models_create_separate_sessions(self) -> None:
        client = _make_client()
        chat_a, chat_b = MagicMock(), MagicMock()
        client._raw_client.chats.create.side_effect = [chat_a, chat_b]

        sa = client.get_or_create_session("ask:default", model="gemini-2.5-flash")
        sb = client.get_or_create_session("ask:default", model="gemini-2.5-pro")
        assert sa is not sb

    def test_session_cache_evicts_oldest_when_full(self) -> None:
        client = _make_client()
        client._raw_client.chats.create.return_value = MagicMock()

        for i in range(_MAX_SESSIONS + 1):
            client.get_or_create_session(f"session:{i}")

        assert len(client._sessions) == _MAX_SESSIONS
        assert "session:0:gemini-2.5-flash" not in client._sessions
        assert f"session:{_MAX_SESSIONS}:{DEFAULT_MODEL}" in client._sessions


class TestThinkingConfig:
    def test_gemini2_thinking_none_maps_to_budget_zero(self) -> None:
        client = _make_client()
        config = client._build_generation_config("none", model="gemini-2.5-flash")
        assert config.thinking_config.thinking_budget == 0  # type: ignore[union-attr]

    def test_gemini2_thinking_high_maps_to_budget_32768(self) -> None:
        client = _make_client()
        config = client._build_generation_config("high", model="gemini-2.5-pro")
        assert config.thinking_config.thinking_budget == 32768  # type: ignore[union-attr]

    def test_gemini3_thinking_maps_to_level_enum(self) -> None:
        from google.genai.types import ThinkingLevel as SDKThinkingLevel

        client = _make_client()
        config = client._build_generation_config("medium", model="gemini-3.5-flash")
        assert config.thinking_config.thinking_level == SDKThinkingLevel.MEDIUM  # type: ignore[union-attr]

    def test_unknown_model_family_raises_client_error(self) -> None:
        client = _make_client()
        with pytest.raises(ClientError, match="Unrecognized model family"):
            client._build_generation_config("low", model="gpt-4-bad")

    def test_latest_alias_treated_as_gemini2(self) -> None:
        client = _make_client()
        cfg = client._build_generation_config("low", model="gemini-flash-latest")
        # Should use thinking_budget (GEMINI_2 path), not thinking_level
        assert cfg.thinking_config.thinking_budget == 1024  # type: ignore[union-attr]

    def test_gemini2_pro_thinking_none_clamped_to_minimum(self) -> None:
        client = _make_client()
        config = client._build_generation_config("none", model="gemini-2.5-pro")
        assert config.thinking_config.thinking_budget == 128  # type: ignore[union-attr]

    def test_gemini2_flash_thinking_none_stays_zero(self) -> None:
        client = _make_client()
        config = client._build_generation_config("none", model="gemini-2.5-flash")
        assert config.thinking_config.thinking_budget == 0  # type: ignore[union-attr]


class TestAsk:
    def test_ask_returns_response_text(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Gemini response"
        mock_session.send_message.return_value = mock_response

        result = client.ask(mock_session, "Hello", "low")
        assert result == "Gemini response"

    def test_ask_raises_client_error_on_empty_response(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.candidates[0].finish_reason.name = "SAFETY"
        mock_session.send_message.return_value = mock_response

        with pytest.raises(ClientError, match="finish_reason=SAFETY"):
            client.ask(mock_session, "Hello", "low")

    def test_ask_empty_response_unknown_finish_reason(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.candidates = []
        mock_session.send_message.return_value = mock_response

        with pytest.raises(ClientError, match="finish_reason=UNKNOWN"):
            client.ask(mock_session, "Hello", "low")

    def test_ask_raises_client_error_on_exception(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_session.send_message.side_effect = RuntimeError("API error")

        with pytest.raises(ClientError, match="inference failed"):
            client.ask(mock_session, "Hello", "medium")

    def test_ask_retries_on_503_and_eventually_succeeds(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_session.send_message.side_effect = [
            RuntimeError("503 UNAVAILABLE"),
            mock_response,
        ]
        with patch("gemini_bridge.client.time.sleep"):
            result = client.ask(mock_session, "Hello", "low")
        assert result == "ok"
        assert mock_session.send_message.call_count == 2

    def test_ask_raises_after_all_retries_exhausted(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_session.send_message.side_effect = RuntimeError("503 UNAVAILABLE")
        with patch("gemini_bridge.client.time.sleep"):
            with pytest.raises(ClientError, match="after 4 attempt"):
                client.ask(mock_session, "Hello", "low")

    def test_ask_does_not_retry_non_retryable_error(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_session.send_message.side_effect = RuntimeError("400 INVALID_ARGUMENT")
        with patch("gemini_bridge.client.time.sleep") as mock_sleep:
            with pytest.raises(ClientError):
                client.ask(mock_session, "Hello", "low")
        mock_sleep.assert_not_called()
        assert mock_session.send_message.call_count == 1

    def test_ask_uses_config_default_thinking_when_none(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_session.send_message.return_value = mock_response

        client.ask(mock_session, "Hello", None)
        mock_session.send_message.assert_called_once()
        call_kwargs = mock_session.send_message.call_args
        assert call_kwargs is not None

    def test_ask_passes_system_instruction_in_gen_config(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_session.send_message.return_value = mock_response

        client.ask(mock_session, "Hello", "low", system_instruction="You are a critic.")
        _, kwargs = mock_session.send_message.call_args
        assert kwargs["config"].system_instruction == "You are a critic."

    def test_default_thinking_property(self) -> None:
        client = _make_client()
        assert client.default_thinking == "medium"

    def test_build_generation_config_includes_system_instruction(self) -> None:
        client = _make_client()
        cfg = client._build_generation_config("low", system_instruction="Be concise.")
        assert cfg.system_instruction == "Be concise."

    def test_build_generation_config_no_system_instruction(self) -> None:
        client = _make_client()
        cfg = client._build_generation_config("low")
        assert cfg.system_instruction is None
