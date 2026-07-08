"""Tests for gemini_bridge.models — backend detection, shortlists, schema hints, chat filter.

The critical case is is_chat_capable: image/tts models ALSO report 'generateContent',
so a naive `'generateContent' in supported_actions` filter is wrong. These tests pin the
name-based exclusion that guards that trap (verified live 2026-07-08).
"""

from types import SimpleNamespace

from gemini_bridge import models


def _meta(name: str, actions=("generateContent", "countTokens")) -> SimpleNamespace:
    """Lightweight stand-in for google.genai.types.Model (no network)."""
    return SimpleNamespace(name=name, supported_actions=list(actions))


class TestBackendFor:
    def test_api_key_is_developer(self) -> None:
        assert models.backend_for("api_key") == models.DEVELOPER_API

    def test_other_methods_are_vertex(self) -> None:
        for method in ("adc", "env", "keychain", "something-else"):
            assert models.backend_for(method) == models.VERTEX


class TestShortlist:
    def test_developer_includes_latest_aliases(self) -> None:
        ids = [model_id for model_id, _ in models.shortlist(models.DEVELOPER_API)]
        assert "gemini-flash-latest" in ids
        assert "gemini-pro-latest" in ids
        assert "gemini-2.5-flash" in ids

    def test_vertex_excludes_latest_aliases(self) -> None:
        ids = [model_id for model_id, _ in models.shortlist(models.VERTEX)]
        assert ids, "vertex shortlist must not be empty"
        assert all("-latest" not in model_id for model_id in ids)
        assert "gemini-2.5-flash" in ids

    def test_default_family_leads_both_backends(self) -> None:
        # gemini-3.5-flash is the server default; it should be presented first.
        for backend in (models.DEVELOPER_API, models.VERTEX):
            first_id = models.shortlist(backend)[0][0]
            assert first_id == "gemini-3.5-flash"

    def test_labels_do_not_hardcode_default_word(self) -> None:
        # The default is marked dynamically, never baked into a static label (staleness guard).
        for backend in (models.DEVELOPER_API, models.VERTEX):
            for _, label in models.shortlist(backend):
                assert "default" not in label.lower()

    def test_unknown_backend_falls_back_to_developer(self) -> None:
        assert models.shortlist("nonsense") == models.shortlist(models.DEVELOPER_API)


class TestSchemaHint:
    def test_developer_hint_mentions_alias_default_and_list_tool(self) -> None:
        hint = models.schema_hint(models.DEVELOPER_API, "gemini-3.5-flash")
        assert "gemini-flash-latest" in hint
        assert "gemini-3.5-flash" in hint  # named as the server default
        assert "gemini_list_models" in hint

    def test_vertex_hint_omits_latest_aliases(self) -> None:
        hint = models.schema_hint(models.VERTEX, "gemini-3.5-flash")
        assert "-latest" not in hint
        assert "gemini-3.5-flash" in hint


class TestIsChatCapable:
    def test_flash_included(self) -> None:
        assert models.is_chat_capable(_meta("models/gemini-2.5-flash")) is True

    def test_image_excluded_despite_generatecontent(self) -> None:
        # The core trap: image models carry generateContent but must be dropped.
        assert models.is_chat_capable(_meta("models/gemini-2.5-flash-image")) is False

    def test_tts_excluded_despite_generatecontent(self) -> None:
        assert models.is_chat_capable(_meta("models/gemini-2.5-flash-preview-tts")) is False

    def test_gemini3_pro_image_excluded(self) -> None:
        assert models.is_chat_capable(_meta("models/gemini-3-pro-image")) is False

    def test_embedding_excluded(self) -> None:
        meta = _meta("models/gemini-embedding-001", actions=["embedContent"])
        assert models.is_chat_capable(meta) is False

    def test_live_excluded(self) -> None:
        assert models.is_chat_capable(_meta("models/gemini-live-2.5-flash-preview")) is False

    def test_no_generatecontent_excluded(self) -> None:
        assert models.is_chat_capable(_meta("models/gemini-2.5-flash", actions=["countTokens"])) is False

    def test_bare_name_without_prefix(self) -> None:
        # Some SDK paths yield the id without a "models/" prefix.
        assert models.is_chat_capable(_meta("gemini-2.5-pro")) is True
