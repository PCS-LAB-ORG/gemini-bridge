# Roadmap

## 26.7.1 — Shipped

**5 tools, ADC + env + Keychain auth, persistent sessions, transcript logging, structured logging, full docs.**

### Core (v1.0)

5 focused tools, Vertex AI + ADC auth, single persistent session, transcript logging, setup wizard.

- `gemini_ask`, `gemini_brainstorm`, `gemini_review`, `gemini_debug`, `gemini_architect`
- ADC (Application Default Credentials) — one-time setup, SDK auto-refreshes
- One default Gemini chat session per server process lifetime
- Transcript logging to `YYYYMMDD-HHMM-gemini-bridge-transcript.md`
- Interactive `setup.sh` wizard
- Full `docs/` directory + README.md

**Why this scope:** Five tools cover the primary use cases (consult, challenge, critique, debug,
design). Persistent sessions give Gemini context across related calls. ADC requires no
credential management beyond one-time setup. Scope is intentionally narrow.

### Env File Auth (v1.1)

Env-file service account fallback (`GOOGLE_APPLICATION_CREDENTIALS`).

`auth.py` (`_load_env()`) reads the env var path and loads credentials from the SA JSON file on
disk. `setup.sh` verification checks the env var is set and the file exists, warns non-fatally
if not set in the current shell. Docs updated with step-by-step SA setup instructions.

### Apple Keychain Auth (v2.5)

Service account JSON stored in Apple Keychain, loaded to memory at server startup, zero disk
artifact after initial store.

`auth.py` (`_load_keychain()`) reads the item via `security(1)`, hex-decodes if needed (the CLI
returns hex for binary-stored multi-line values), and parses the SA JSON. `setup.sh` option 3
prompts for keychain service/account names, verifies the item exists and contains valid JSON,
writes `keychain_service`/`keychain_account` fields to config.json.

**Minimum SA role:** `roles/aiplatform.user` — grants `aiplatform.endpoints.predict` only.

**macOS only:** The `security` CLI is macOS-specific. Linux equivalents (secret-tool, pass)
are out of scope.

### Per-Call Model Selection + Discoverability ✓ Shipped

Per-call `model=` parameter on all five inference tools; `-latest` aliases (Developer API);
transparent fallback to `gemini-3.1-flash-lite` on 503/429 with a disclosure notice; default model
raised to `gemini-3.5-flash`.

Model options are now **discoverable** and **backend-aware**: each tool's `model` parameter
description lists the models valid for the active backend, and a new `gemini_list_models` tool
returns the live, chat-only catalog (degrading to a curated static shortlist if the live list is
unavailable). Single source of truth in `models.py`. See
[configuration.md](configuration.md#choosing-a-model) and [tools.md](tools.md#gemini_list_models).

---

## 26.7.2 — Planned

### Named Sessions (#15)

- `gemini_new_session(name)` — create a fresh named chat session
- `session_name` parameter on all 5 tools routes to that session's history
- `gemini_list_sessions()` — list active session names

**Why deferred:** Single session per tool satisfies the primary use case. Named sessions
add routing logic and lifecycle management that should be validated as needed. The v1
architecture already supports this — `_sessions` is a dict keyed by name.

### Per-Project Transcript Routing (#17)

`gemini_set_transcript_dir(path)` tool — redirect the transcript file location without
editing config.json.

**Why this matters:** The MCP server is registered globally (`-s user`) and starts once per
Claude Code session regardless of which project is active. Currently, changing the transcript
directory requires editing `~/.config/gemini-bridge/config.json` and restarting Claude Code.
The tool lets Claude redirect transcripts to the active project's `session-summaries/`
without a manual config edit.

### Google AI Studio API Key Auth (#30) ✓ Shipped

API key auth method for Google AI Studio — the non-Vertex, public-facing Gemini endpoint.
`AuthResult` dataclass + `build_auth()` unified dispatch in `auth.py`. `Config.project`
made optional with conditional validator. No GCP project or `gcloud` setup required.

**Why:** Google AI Studio is hugely popular. Supporting API key auth makes gemini-bridge
accessible without a GCP project. The design keeps secure auth (ADC, Keychain) as first-class
citizens — API key is additive, not a replacement.

---

## Backlog

### Sliding Window Context Management (v4.0)

Automatic context window management for very long sessions — summarize and trim older exchanges
when approaching the Gemini context limit.

**Why deferred:** Gemini 2.5/3.x has a 1M+ token context window. A typical Claude Code
session's tool calls will not approach this limit. This becomes relevant only for very long
multi-day sessions where session state is not reset.
