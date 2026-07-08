"""Tests for gemini_bridge/client.py — GeminiClient session management and ask()."""

from unittest.mock import MagicMock, patch

import pytest
from gemini_bridge.client import ClientError, GeminiClient
from gemini_bridge.config import Config


def _make_client(model: str = "gemini-2.5-flash") -> GeminiClient:
    config = Config(project="test-project", model=model)
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


class TestThinkingConfig:
    def test_gemini2_thinking_none_maps_to_budget_zero(self) -> None:
        client = _make_client("gemini-2.5-flash")
        config = client._build_generation_config("none")
        assert config.thinking_config.thinking_budget == 0  # type: ignore[union-attr]

    def test_gemini2_thinking_high_maps_to_budget_32768(self) -> None:
        client = _make_client("gemini-2.5-pro")
        config = client._build_generation_config("high")
        assert config.thinking_config.thinking_budget == 32768  # type: ignore[union-attr]

    def test_gemini3_thinking_maps_to_level_enum(self) -> None:
        from google.genai.types import ThinkingLevel as SDKThinkingLevel

        client = _make_client("gemini-3.5-flash")
        config = client._build_generation_config("medium")
        assert config.thinking_config.thinking_level == SDKThinkingLevel.MEDIUM  # type: ignore[union-attr]

    def test_unknown_model_family_raises_client_error(self) -> None:
        client = _make_client()
        # Bypass pydantic validation to simulate a bad model that passed config validation
        client._config = Config.model_construct(
            project="p", model="gpt-4-bad", default_thinking="medium"
        )
        with pytest.raises(ClientError, match="Unrecognized model family"):
            client._build_generation_config("low")


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
        mock_session.send_message.return_value = mock_response

        with pytest.raises(ClientError, match="empty response"):
            client.ask(mock_session, "Hello", "low")

    def test_ask_raises_client_error_on_exception(self) -> None:
        client = _make_client()
        mock_session = MagicMock()
        mock_session.send_message.side_effect = RuntimeError("API error")

        with pytest.raises(ClientError, match="inference failed"):
            client.ask(mock_session, "Hello", "medium")

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
