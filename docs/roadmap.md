# Roadmap

## v1.0 — Core (current)

5 focused tools, Vertex AI + ADC auth, single persistent session, transcript logging, setup wizard.

**What's included:**
- `gemini_ask`, `gemini_brainstorm`, `gemini_review`, `gemini_debug`, `gemini_architect`
- ADC (Application Default Credentials) as the only auth method
- One default Gemini chat session per server process lifetime
- Transcript logging to `YYYYMMDD-HHMM-gemini-transcript.md`
- Interactive `setup.sh` wizard
- Full `docs/` directory + README.md

**Why this scope:** Five tools cover the primary use cases (consult, challenge, critique, debug,
design). Persistent sessions give Gemini context across related calls. ADC requires no
credential management beyond one-time setup. Scope is intentionally narrow.

---

## v1.1 — Env File Auth Fallback

**Feature:** Env-file service account fallback (`GOOGLE_APPLICATION_CREDENTIALS`).

Already implemented in auth.py (`method: "env"`). Full test coverage included in v1.0.
This is a documentation and setup.sh enhancement — configuring the env var, adding
the method to the wizard.

**Why deferred:** ADC covers the primary use case. Env-file auth is a lower-security
fallback for environments where ADC isn't viable.

---

## v2.0 — Named Sessions

**Features:**
- `gemini_new_session(name)` — create a fresh named chat session
- `session_name` parameter on all 5 tools routes to that session's history
- `gemini_list_sessions()` — list active session names

**Why deferred:** Single session per tool satisfies the primary use case. Named sessions
add routing logic and lifecycle management that should be validated as needed. The v1
architecture already supports this — `_sessions` is a dict keyed by name.

---

## v2.5 — Apple Keychain Auth (macOS)

**Feature:** Service account JSON stored in Apple Keychain, loaded to memory at server
startup, zero disk artifact after initial store.

**Why Keychain over a disk file:** A SA JSON on disk is a persistent secret at rest. Keychain
provides OS-managed storage with ACL enforcement. The MCP server reads once at startup and
the raw bytes disappear when the process exits.

**Minimum SA role:** `roles/aiplatform.user` — grants `aiplatform.endpoints.predict` only.

**Already stubbed:** `auth.py` has `_load_keychain()` implemented and tested. v2.5 is
setup.sh updates + documentation + removing the "macOS only" limitation note from the wizard.

**macOS only:** The `security` CLI is macOS-specific. Linux equivalents (secret-tool, pass)
are out of scope for this phase.

---

## v3.0 — Per-Project Transcript Routing

**Feature:** `gemini_set_transcript_dir(path)` tool — redirect the transcript file location
without editing config.json.

**Why this matters:** The MCP server is registered globally (`-s user`) and starts once per
Claude Code session regardless of which project is active. Currently, changing the transcript
directory requires editing `~/.config/gemini-bridge/config.json` and restarting Claude Code.
The v3 tool lets Claude redirect transcripts to the active project's `session-summaries/`
without a manual config edit.

---

## v4.0 — Sliding Window Context Management

**Feature:** Automatic context window management for very long sessions — summarize and trim
older exchanges when approaching the Gemini context limit.

**Why deferred:** Gemini 2.5/3.x has a 1M+ token context window. A typical Claude Code
session's tool calls will not approach this limit. This becomes relevant only for very
long multi-day sessions where session state is not reset.

---

## v5.0 — Upstream Contribution to rlabs/gemini-mcp

**Feature:** Evaluate contributing Vertex AI + ADC auth back to the rlabs/gemini-mcp project
as an upstream PR.

The rlabs project (MIT) is TypeScript, stateless, and API-key-only. Vertex AI auth and
persistent sessions would be a meaningful addition. Whether to pursue this depends on the
maintainers' interest and the effort of TypeScript translation.
