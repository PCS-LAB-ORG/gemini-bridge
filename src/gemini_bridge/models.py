"""
gemini_bridge/models.py
-----------------------
Single source of truth for backend-aware model discoverability.

Responsibilities:
  - Define the curated, recommended model shortlist per backend
  - Detect the active backend from the auth method
  - Build the schema-hint string injected into every tool's `model` param
  - Filter a live models.list() down to chat-capable models

Design notes:
  - Single Responsibility: pure data + small pure functions; no SDK, no network, no I/O
  - Dependency Inversion: depends on nothing else in the package (avoids a circular import
    with client.py, which owns DEFAULT_MODEL/FALLBACK_MODEL). Consumers that need both a
    model constant AND these helpers import each from its own module.
  - Open/Closed: adding a model means editing RECOMMENDED here and nowhere else — the docs
    went stale precisely because there was no single source.

Curated ids verified live 2026-07-08:
  - Developer API `-latest` aliases (gemini-flash-latest, gemini-pro-latest) confirmed present.
  - Vertex GA text models confirmed against Google Cloud model docs; gemini-3.5-flash is GA.
    Vertex has NO `-latest` aliases (they 404), so its shortlist is alias-free.

Used by:  tools/base.py (schema hints), tools/list_models.py (live filter)
Imports:  (stdlib only)
"""

from typing import Optional, Protocol, Sequence


class ModelMeta(Protocol):
    """Structural shape of a models.list() entry.

    Matched by google.genai.types.Model at runtime; kept as a Protocol so this module
    depends on nothing (no SDK import) and tests can pass lightweight fakes.
    """

    name: str
    supported_actions: Optional[Sequence[str]]


# Backend identifiers.
DEVELOPER_API = "developer"  # api_key mode (Google AI Studio Developer API)
VERTEX = "vertex"            # adc/env/keychain modes (Vertex AI)

# Curated, recommended shortlist per backend: (model_id, one-line label).
# Order matters — the first entry is presented first and is the default family.
RECOMMENDED: dict[str, list[tuple[str, str]]] = {
    DEVELOPER_API: [  # VERIFIED 2026-07-08 against the live Developer API models.list
        ("gemini-3.5-flash", "newest Flash — near-Pro quality at Flash cost"),
        ("gemini-2.5-flash", "stable, fast, reliable"),
        ("gemini-flash-latest", "auto-tracks newest Flash (Developer API alias)"),
        ("gemini-pro-latest", "auto-tracks newest Pro (Developer API alias)"),
        ("gemini-2.5-pro", "higher-capability reasoning"),
    ],
    VERTEX: [  # VERIFIED 2026-07-08 against Google Cloud Vertex AI model docs (GA models)
        ("gemini-3.5-flash", "newest Flash — near-Pro quality at Flash cost (GA)"),
        ("gemini-2.5-flash", "stable, fast, reliable"),
        ("gemini-2.5-pro", "higher-capability reasoning (stable)"),
        ("gemini-3.1-flash-lite", "most cost-efficient, high-volume"),
    ],
}

# Name substrings that mark a NON-chat model. This is the decisive filter: image and TTS
# models also report 'generateContent', so filtering on that action alone is insufficient
# (verified live 2026-07-08). Name-based exclusion is what actually separates them.
_NON_CHAT_MARKERS = ("image", "tts", "audio", "embedding", "live")


def backend_for(auth_method: str) -> str:
    """Map a config auth method to a backend identifier.

    Only "api_key" is the Developer API; every other method (adc/env/keychain) is Vertex.
    """
    return DEVELOPER_API if auth_method == "api_key" else VERTEX


def shortlist(backend: str) -> list[tuple[str, str]]:
    """Return the curated (id, label) shortlist for a backend.

    Unknown backends fall back to the Developer API list (the safe, verified default).
    """
    return RECOMMENDED.get(backend, RECOMMENDED[DEVELOPER_API])


def schema_hint(backend: str, default_model: str) -> str:
    """Build the one-line `model` param description for a backend.

    Names the recommended ids, the active default, and points at gemini_list_models for
    the authoritative live list.
    """
    ids = ", ".join(model_id for model_id, _ in shortlist(backend))
    return (
        f"Optional Gemini model. Recommended: {ids}. "
        f"Omit to use the server default ({default_model}). "
        "Call gemini_list_models for the full, live list."
    )


def is_chat_capable(meta: ModelMeta) -> bool:
    """True if a models.list() entry is a text/chat model (not image/tts/audio/embedding/live).

    `meta` is a google.genai.types.Model (or any object with `.name` and `.supported_actions`).
    The SDK field is `supported_actions` (a list[str]) — NOT `supportedGenerationMethods`
    (that is the raw REST name). `generateContent` is necessary but NOT sufficient: image and
    TTS models report it too, so a name-based exclusion is the decisive check.
    """
    name = (getattr(meta, "name", "") or "").split("/")[-1]
    if any(marker in name for marker in _NON_CHAT_MARKERS):
        return False
    return "generateContent" in (getattr(meta, "supported_actions", None) or [])
