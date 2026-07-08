"""Tests for gemini_bridge/tools — tool registration and call_gemini() helper."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from gemini_bridge.client import GeminiClient
from gemini_bridge.config import Config
from gemini_bridge.tools.base import call_gemini
from gemini_bridge.transcript import TranscriptWriter


def _make_client() -> GeminiClient:
    config = Config(project="test-project")
    mock_creds = MagicMock()
    with patch("google.genai.Client"):
        return GeminiClient(config, mock_creds)


def _make_transcript(tmp_path: "Path") -> TranscriptWriter:
    from datetime import datetime

    return TranscriptWriter(str(tmp_path), datetime.now())


class TestCallGemini:
    def test_returns_response_on_success(self, tmp_path: object) -> None:
        client = _make_client()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "brainstorm result"
        mock_chat.send_message.return_value = mock_response
        client._raw_client.chats.create.return_value = mock_chat

        transcript = _make_transcript(tmp_path)
        result = call_gemini(
            client=client,
            transcript=transcript,
            tool_name="gemini_brainstorm",
            session_name="default",
            system_instruction="Be creative.",
            prompt="Ideas for caching?",
            thinking="low",
        )
        assert result == "brainstorm result"

    def test_returns_error_string_on_client_error(self, tmp_path: object) -> None:
        client = _make_client()
        mock_chat = MagicMock()
        mock_chat.send_message.side_effect = Exception("API down")
        client._raw_client.chats.create.return_value = mock_chat

        transcript = _make_transcript(tmp_path)
        result = call_gemini(
            client=client,
            transcript=transcript,
            tool_name="gemini_ask",
            session_name="default",
            system_instruction="Answer.",
            prompt="Hello",
            thinking="none",
        )
        assert result.startswith("[gemini-bridge error]")

    def test_appends_to_transcript_on_success(self, tmp_path: object) -> None:
        client = _make_client()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "done"
        mock_chat.send_message.return_value = mock_response
        client._raw_client.chats.create.return_value = mock_chat

        transcript = _make_transcript(tmp_path)
        call_gemini(
            client=client,
            transcript=transcript,
            tool_name="gemini_review",
            session_name="default",
            system_instruction="Review.",
            prompt="Check this code.",
            thinking="medium",
        )
        content = transcript.path.read_text()
        assert "gemini_review" in content
        assert "Check this code." in content

    def test_fallback_to_default_model_on_503(self, tmp_path: object) -> None:
        from gemini_bridge.client import FALLBACK_MODEL

        client = _make_client()
        mock_busy_chat = MagicMock()
        mock_busy_chat.send_message.side_effect = Exception("503 UNAVAILABLE model overloaded")
        mock_fallback_chat = MagicMock()
        mock_fallback_response = MagicMock()
        mock_fallback_response.text = "fallback answer"
        mock_fallback_chat.send_message.return_value = mock_fallback_response
        client._raw_client.chats.create.side_effect = [mock_busy_chat, mock_fallback_chat]

        transcript = _make_transcript(tmp_path)
        with patch("gemini_bridge.client.time.sleep"):
            result = call_gemini(
                client=client,
                transcript=transcript,
                tool_name="gemini_ask",
                session_name="default",
                system_instruction="Answer.",
                prompt="Hello",
                thinking="low",
                model="gemini-3.5-flash",  # busy model
            )
        assert "[gemini-bridge notice]" in result
        assert "gemini-3.5-flash" in result
        assert FALLBACK_MODEL in result
        assert "fallback answer" in result


class TestToolRegistration:
    def test_all_tools_register_without_error(self, tmp_path: Path) -> None:
        from datetime import datetime

        from gemini_bridge.tools import (
            register_architect,
            register_ask,
            register_brainstorm,
            register_debug,
            register_review,
        )
        from mcp.server.fastmcp import FastMCP

        client = _make_client()
        transcript = TranscriptWriter(str(tmp_path), datetime.now())
        mcp = FastMCP("test-server")
        register_ask(mcp, client, transcript)
        register_brainstorm(mcp, client, transcript)
        register_review(mcp, client, transcript)
        register_debug(mcp, client, transcript)
        register_architect(mcp, client, transcript)
