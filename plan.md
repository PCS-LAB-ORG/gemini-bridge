# Gemini Bridge MCP Server — Implementation Plan

## Context

The goal is to give Claude Code a live Gemini counterpart it can consult during technical
work — brainstorming, code review, debugging, architecture discussions. A second model
weighing in on hard problems reduces the chance of going in circles or making avoidable
mistakes. The user directs all work; Gemini is a sounding board and judge, not a driver.

Authentication uses Google Cloud Application Default Credentials (ADC) via Vertex AI as
the default, with Apple Keychain-backed service account auth on the roadmap for environments
where persistent ADC isn't viable. No API keys.

---

## Decision: Build from Scratch in Python (Not Fork rlabs/gemini-mcp)

An existing open-source project — [`rlabs-inc/gemini-mcp`](https://github.com/rlabs-inc/gemini-mcp)
(MIT license) — has 37 tools and mature MCP integration, but:

| Factor | rlabs/gemini-mcp | What We Need |
|---|---|---|
| Language | TypeScript / Node.js | Python (GCP stack alignment) |
| Auth | API key only | Vertex AI + ADC + Keychain SA (roadmap) |
| Session model | Stateless (by design) | Persistent chat history |
| Scope | 37 tools — image gen, video, TTS, YouTube | 5 focused text tools |
| Transcript logging | None | Required |
| System prompts | None | Per-tool personas |
| Thinking budget | `thinkingLevel` enum (Gemini 3 only) | Model-agnostic abstraction needed |

Adding persistent sessions + ADC + transcripts + Python translation to the rlabs project
is more refactoring than building the focused scope from scratch. The 37-tool breadth is
a liability here, not an asset.

**Estimated scope (fresh build):** 5 tools x ~80 lines + session/config/transcript
~300 lines + MCP wiring ~150 lines + setup script ~100 lines = **~900 lines Python, 5-7 days.**

---

## Project Name and Repo

- **Repo name**: `gemini-bridge`
- **Package name**: `gemini-bridge` (installed via `pip install -e .`)
- **Language**: Python 3.11+
- **Local path**: `~/dev/github/gemini-bridge/`
- **Remote**: `PCS-LAB-ORG/gemini-bridge` (private)

---

## File Structure

```
gemini-bridge/
├── pyproject.toml
├── setup.sh                        # interactive configure wizard
├── README.md                       # follows lab-cleanup README style (see Documentation section)
├── session-summaries/              # default transcript location during development
├── docs/
│   ├── README.md                   # full documentation index
│   ├── architecture.md             # system design, component relationships, data flow
│   ├── auth.md                     # all auth methods, setup steps, troubleshooting
│   ├── configuration.md            # full config.json field reference
│   ├── tools.md                    # all 5 tools: parameters, system prompts, examples
│   ├── transcripts.md              # transcript format, session lifecycle, location strategy
│   ├── development.md              # dev setup, running tests, adding a new tool
│   └── roadmap.md                  # v1-v5 roadmap with rationale for each phase
├── src/
│   └── gemini_bridge/
│       ├── __init__.py
│       ├── __main__.py             # entry: python -m gemini_bridge
│       ├── server.py               # MCP server, tool registration
│       ├── client.py               # Gemini chat wrapper, session state
│       ├── config.py               # load/validate ~/.config/gemini-bridge/config.json
│       ├── auth.py                 # ADC, Keychain SA, env-file credential loading
│       ├── transcript.py           # append exchanges to session transcript file
│       └── tools/
│           ├── __init__.py
│           ├── base.py             # ToolResult type, shared parameter definitions
│           ├── ask.py
│           ├── brainstorm.py
│           ├── review.py
│           ├── debug.py
│           └── architect.py
└── tests/
    ├── test_client.py
    ├── test_config.py
    ├── test_auth.py
    ├── test_transcript.py
    └── test_tools.py
```

---

## Code Quality Standards

### SOLID Principles

These are non-negotiable, not aspirational. Every module must satisfy them before v1 ships.

| Principle | Application in this project |
|---|---|
| **Single Responsibility** | Each module owns exactly one concern: `auth.py` loads credentials only; `transcript.py` writes only; `config.py` validates only; tools hold only prompt logic |
| **Open/Closed** | New auth methods add a loader function + one branch in `build_credentials()` — nothing else changes. New tools add a file in `tools/` + one registration line in `server.py` |
| **Liskov Substitution** | All auth paths return `google.auth.credentials.Credentials`; all tools return `ToolResult`; substituting one implementation for another must not break callers |
| **Interface Segregation** | Tools receive only a `GeminiClient` handle — not the full server or config object. `GeminiClient` exposes `ask(session, prompt, thinking)` only, not internal session state |
| **Dependency Inversion** | `client.py` depends on the `google.auth.credentials.Credentials` abstraction, not on any concrete loader. `server.py` depends on tool callables, not on tool internals |

### No Workarounds Policy

- No `# type: ignore` without a paired comment explaining why and what will remove it
- No bare `except Exception` — catch specific exceptions, always
- No `TODO` left in merged code — open a GitHub issue instead, reference it in a comment
- No mutable default arguments, no global state outside the server process lifecycle
- Ruff + mypy (strict) must pass clean before any PR merges

### File Header Standard

Every `.py` file begins with a module-level docstring following this template:

```python
"""
gemini_bridge/auth.py
---------------------
Credential loading for all supported authentication methods.

Responsibilities:
  - Load Application Default Credentials (ADC) — default method
  - Load service account credentials from Apple Keychain (macOS, v2)
  - Load service account credentials from GOOGLE_APPLICATION_CREDENTIALS env var

Design notes:
  - Single Responsibility: credential loading only; SDK client construction is in client.py
  - Open/Closed: add a new method by adding a loader function + one branch in build_credentials()
  - Returns google.auth.credentials.Credentials interface; callers never import concrete types

Raises:
  AuthError  — wraps all credential failures with actionable messages for Claude to surface

Used by:  client.py -> build_client()
Imports:  config.py (AuthConfig)
"""
```

Fields required in every header: file path relative to src/, one-line description,
Responsibilities list, Design notes (SOLID callouts relevant to this file), Raises,
Used by, Imports. The goal is that any developer — human or AI — can understand the
module's contract without reading the implementation.

---

## Documentation

### README.md (top-level)

Follows the style established in `~/dev/github/lab-cleanup/README.md`. Structure:

```
<h1 align="center">gemini-bridge</h1>
<h4 align="center">Gemini as a live sounding board for Claude Code — via Vertex AI, ADC auth, persistent sessions.</h4>

[badges: Python, MCP, Vertex AI, Auth method]

[2-paragraph intro: what it is, why it exists, what it is not]

Quick navigation: [What it does] | [Prerequisites] | [Quick start] | [Project structure]
                  [Architecture] | [Configuration] | [Auth methods] | [Tools] | [Full Documentation]

## What it does
  [5 tools described briefly, session model, transcript logging]

## Prerequisites
  [table: Python 3.11+, gcloud CLI, ADC, MCP-compatible Claude Code version]

## Quick start
  [3 steps: clone + pip install -e ., run setup.sh, claude mcp add command]

## Project structure
  [annotated tree, same as File Structure above]

## Architecture
  [Mermaid flowchart: Claude Code -> MCP tool call -> GeminiClient -> Vertex AI ->
   response -> transcript append -> tool result returned to Claude]

## Configuration
  [config.json field reference table]

## Auth methods
  [ADC (default), env-file, Keychain (roadmap) — one paragraph each]

## Known limitations / roadmap
  [link to docs/roadmap.md]

## Full Documentation
  [link to docs/README.md]
```

### docs/ Contents

| File | Contents |
|---|---|
| `docs/README.md` | Index of all docs with one-line summaries and links |
| `docs/architecture.md` | Component diagram, data flow, session lifecycle, transcript lifecycle |
| `docs/auth.md` | Step-by-step setup for each auth method, troubleshooting table, gcloud auth vs ADC distinction |
| `docs/configuration.md` | Every config.json field: type, default, valid values, effect |
| `docs/tools.md` | All 5 tools: full parameter list, system prompt text, example prompts, when to use each |
| `docs/transcripts.md` | File format spec, session boundary behavior, how to change transcript_dir, format examples |
| `docs/development.md` | Dev environment setup, running tests, adding a new tool (step-by-step), mypy/ruff config |
| `docs/roadmap.md` | v1-v5 features with rationale; what was deliberately deferred and why |

---

## Tools (v1 — 5 Tools)

All tools share two optional parameters:
- `session_name: str = "default"` (for v2 named sessions; v1 ignores this, always uses default)
- `thinking: "none" | "low" | "medium" | "high" = None` (falls back to config default)

### 1. `gemini_ask`
General purpose. No specialized persona. Use when no other tool fits.
- **System prompt**: You are a knowledgeable technical assistant working alongside Claude,
  another AI. Answer directly and precisely. Prefer concrete examples. When uncertain, say so.
- **Parameters**: `prompt: str`

### 2. `gemini_brainstorm`
Divergent ideation. Explicitly instructs Gemini to challenge and diverge, not validate.
- **System prompt**: You are a creative thinking partner working alongside Claude, another AI.
  Push unconventional approaches. Challenge Claude's existing direction. Play devil's advocate
  when useful. Offer alternatives even when the current path seems fine. Be concise.
- **Parameters**: `topic: str`, `context: str = ""`

### 3. `gemini_review`
Critical code or design review. Pessimistic, rigorous framing — finds problems.
- **System prompt**: You are a critical technical reviewer working alongside Claude, another AI.
  Find problems, risks, and weaknesses in code, designs, and plans. Be direct. Don't soften
  feedback. Prioritize by severity. If something is sound, say so briefly and move on.
- **Parameters**: `content: str`, `question: str = ""`

### 4. `gemini_debug`
Hypothesis generation for bugs and failures. Evidence-driven, not speculative.
- **System prompt**: You are a systematic debugging assistant working alongside Claude, another AI.
  Generate root cause hypotheses from the evidence provided. Reason through failure modes.
  Suggest specific diagnostic steps. Don't guess without basis — reason from what's shown.
- **Parameters**: `error: str`, `context: str = ""`

### 5. `gemini_architect`
System design and tradeoff analysis. Opinionated where warranted.
- **System prompt**: You are a software architecture advisor working alongside Claude, another AI.
  Evaluate system designs, suggest patterns, identify scalability and maintainability concerns.
  Be opinionated when a clearly better path exists. Name tradeoffs explicitly when the choice
  is genuinely context-dependent.
- **Parameters**: `description: str`, `question: str = ""`

---

## Session Model

### v1 — Single Persistent Session

- Server starts one default `chat` object via `google-genai` `client.chats.create()`
- All tool calls within the Claude Code session append to the same conversation history
- Gemini accumulates context naturally across tools and turns
- Session resets only when the MCP server process restarts (i.e., Claude Code restarts)
- Per-call token cost grows as conversation grows — acceptable for typical session lengths
  given Gemini 2.5's 1M context window

```python
# client.py — core session state
self._sessions: dict[str, Chat] = {}

def get_or_create_session(self, name: str = "default") -> Chat:
    if name not in self._sessions:
        self._sessions[name] = self._genai_client.chats.create(
            model=self.config.model,
            config=GenerateContentConfig(system_instruction=SYSTEM_PROMPTS[name])
        )
    return self._sessions[name]
```

### v2 (Roadmap) — Named Sessions

- New tool: `gemini_new_session(name: str)` — creates a fresh named chat object
- `session_name` parameter on all tools routes to that chat's history
- `gemini_list_sessions()` — returns active session names
- Architecture already supports this: `_sessions` dict is in place in v1

**Why defer**: Single session satisfies the primary use case. Named sessions add routing
logic and lifecycle management that should be validated as needed.

---

## Thinking Budget

Tool parameter: `thinking: "none" | "low" | "medium" | "high"` (optional)
Falls back to `default_thinking` in config if not specified.

Claude chooses thinking level per call based on complexity:
- Simple factual questions → `none` or `low`
- Architecture decisions, tricky bugs → `high`

Server translates to model-appropriate API parameter:

| Level | Gemini 2.5 (`thinking_budget` int) | Gemini 3.x (`thinking_level` enum) |
|---|---|---|
| none   | 0     | "minimal" |
| low    | 1024  | "low"     |
| medium | 8192  | "medium"  |
| high   | 32768 | "high"    |

**Model family detection**: parse model string — `gemini-2.` prefix → budget int;
`gemini-3.` prefix → level enum. Raises `ConfigError` for unrecognized model family.

---

## Configuration

**Config file**: `~/.config/gemini-bridge/config.json`

```json
{
  "project": "my-gcp-project",
  "location": "us-central1",
  "model": "gemini-2.5-flash",
  "default_thinking": "medium",
  "transcript_dir": "~/session-summaries",
  "auth": {
    "method": "adc"
  }
}
```

For Keychain auth (v2):
```json
{
  "auth": {
    "method": "keychain",
    "keychain_service": "gemini-bridge",
    "keychain_account": "vertex-sa"
  }
}
```

**`setup.sh` — interactive wizard (run once, re-run to change settings):**
1. Prompt for auth method: `adc` (default) or `keychain` (service account via Keychain)
2. If `adc`: check `gcloud auth application-default print-access-token` succeeds — fail fast with clear message if not
3. If `keychain`: prompt for keychain service + account names; verify the secret can be read and is valid JSON
4. Show `gcloud config get-value project` as default project, prompt to confirm or override
5. Show model choices: `gemini-2.5-flash` (fast/cheap), `gemini-2.5-pro` (capable),
   `gemini-3.5-flash` (newest Flash), `gemini-3.1-pro-preview` (newest Pro) with notes
6. Prompt for default thinking level (recommend: `medium`)
7. Prompt for transcript directory (default: `~/session-summaries`)
8. Write `~/.config/gemini-bridge/config.json`
9. Print the exact `claude mcp add` command to run, and the pip install command

---

## Transcript Logging

**File**: `{transcript_dir}/YYYYMMDD-HHMM-gemini-transcript.md`
- Timestamp is captured at **server startup** so all calls in one Claude session share one file
- `transcript_dir` is created if it doesn't exist
- File is opened in append mode; exchanges are written as they happen

**Format per exchange**:
```markdown
## [14:32:07] gemini_brainstorm — thinking: medium | session: default

**Prompt:**
How should we structure the retry logic for the Pub/Sub consumer?

**Response:**
Three angles worth considering...

---
```

**Transcript directory default**: `{repo_root}/session-summaries/` within the gemini-bridge
repo during development; configured globally in `transcript_dir` for use in other projects.
The MCP server is registered globally (`-s user`) so it starts once per Claude Code session.
For project-specific transcript routing, update `transcript_dir` in config.json to point to
the active project's `session-summaries/` folder. A future `gemini_set_transcript_dir(path)`
tool (v3 roadmap) would let Claude redirect transcripts per project without a config edit.

---

## Authentication

Three methods supported, in preference order:

| Method | Status | Config value | Notes |
|---|---|---|---|
| ADC (user credentials) | v1 | `"adc"` (default) | `gcloud auth application-default login` once; SDK auto-refreshes |
| Apple Keychain (service account) | v2 roadmap | `"keychain"` | SA JSON in Keychain; loaded to memory at startup; zero disk artifact |
| Env file (service account) | v1 fallback | `"env"` | `GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json`; least preferred |

### v1: ADC (Default)

```python
from google import genai

client = genai.Client(
    vertexai=True,
    project=config.project,
    location=config.location,
    credentials=None,  # SDK auto-detects ADC from ~/.config/gcloud/application_default_credentials.json
)
```

ADC is the default because it requires no config beyond a one-time
`gcloud auth application-default login`. The SDK holds a refresh token and transparently
renews access tokens — no re-auth during normal use.

**`gcloud auth login` vs ADC — common confusion:**

| Command | Authenticates | Stored at | Re-auth frequency |
|---|---|---|---|
| `gcloud auth login` | gcloud CLI only | `~/.config/gcloud/credentials.db` | Short-lived; org session-timeout policy |
| `gcloud auth application-default login` | SDKs and APIs | `~/.config/gcloud/application_default_credentials.json` | Refresh token; typically months |

The MCP server uses ADC only. CLI credential expiry does not affect it. Confirmed working:
`gcloud auth application-default print-access-token` returns a token without re-auth.

### v1 Fallback: Env File (Least Preferred)

Set `GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json` in the shell environment before
starting Claude Code. The SDK picks it up automatically. Leaves a credential file on disk —
acceptable only on full-disk-encrypted machines with no shared access.

### v2 Roadmap: Apple Keychain (Preferred Service Account Path)

**Why Keychain over a file**: A service account JSON on disk is a persistent secret at rest.
It violates DLP policy, requires secure file permissions, and creates audit surface. Apple
Keychain provides OS-managed secret storage with ACL enforcement. The MCP server reads the
secret once at startup, creates an in-memory credentials object, and it disappears when the
process exits — no persistent artifact on disk.

**Minimum SA role** (principle of least privilege):
```
roles/aiplatform.user
```
Grants `aiplatform.endpoints.predict` — all Gemini inference needs. Nothing else.

**One-time setup — store SA JSON in Keychain:**
```bash
security add-generic-password \
  -s "gemini-bridge" \
  -a "vertex-sa" \
  -w "$(cat /path/to/downloaded-sa-key.json)"
rm /path/to/downloaded-sa-key.json   # remove the file from disk immediately
```

**Server reads at startup** (`auth.py`):
```python
import subprocess
import json
from google.oauth2 import service_account

def load_keychain_credentials(keychain_service: str, keychain_account: str):
    result = subprocess.run(
        ["security", "find-generic-password",
         "-s", keychain_service, "-a", keychain_account, "-w"],
        capture_output=True, text=True, check=True
    )
    sa_info = json.loads(result.stdout.strip())
    return service_account.Credentials.from_service_account_info(
        sa_info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
```

The `credentials` object is passed to `genai.Client(credentials=creds)`. The SDK handles
token refresh from the SA credentials internally. The raw JSON is never written to disk
after the initial Keychain store.

**macOS only**: The `security` CLI is macOS-specific. Linux equivalents (`secret-tool`,
`pass`) are out of scope for v2. Document as macOS-only feature.

### Error Handling — All Auth Methods

All auth errors are caught at tool-call time and returned as tool results (not server
crashes), so Claude can surface them as actionable messages:

| Exception | Cause | Message |
|---|---|---|
| `google.auth.exceptions.DefaultCredentialsError` | ADC not found | "Gemini auth error: no credentials. Run: `gcloud auth application-default login`" |
| `google.auth.exceptions.RefreshError` | Token refresh failed | "Gemini auth error: token refresh failed. Run: `gcloud auth application-default login`" |
| `subprocess.CalledProcessError` | Keychain item not found | "Gemini auth error: Keychain item not found. Re-run setup." |
| `json.JSONDecodeError` | Keychain value not valid JSON | "Gemini auth error: Keychain value is not valid service account JSON." |

Server stays running in all cases. Claude prompts user to fix and signals when to retry.

---

## Dependencies

```toml
[project]
name = "gemini-bridge"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "mcp>=1.28,<2",          # Pin v1.x; v2.0 is pre-release as of July 2026
    "google-genai>=1.34",    # Unified Vertex + Gemini Developer API SDK
    "google-auth>=2.0",      # For service_account.Credentials (Keychain path)
    "pydantic>=2.0",         # Config validation
]

[project.scripts]
gemini-bridge = "gemini_bridge.__main__:main"
```

---

## MCP Registration

After `pip install -e .` and `setup.sh`:

```bash
claude mcp add -s user gemini-bridge python -m gemini_bridge
```

Verify:
```bash
claude mcp list
```

---

## Verification Checklist

1. `gcloud auth application-default print-access-token` — returns token (ADC works)
2. `python -m gemini_bridge` — server starts, no errors in stderr
3. In Claude Code: call `gemini_ask` with a simple prompt — response returned, no error
4. Check `{transcript_dir}/YYYYMMDD-HHMM-gemini-transcript.md` — file exists, exchange appended
5. Call `gemini_brainstorm` then `gemini_review` in the same session — response style differs
   between tools (system prompt personas working)
6. Call any tool twice — second call has context from the first (session continuity confirmed)
7. Restart Claude Code — new transcript file created with new session timestamp
8. Simulate auth failure (rename ADC file temporarily) — tool returns error message, server stays up

---

## Roadmap

| Phase | Feature |
|---|---|
| v1 | 5 tools, Vertex ADC, single persistent session, transcript logging, setup script |
| v1 | Full `docs/` directory + README.md (ships with v1, not deferred) |
| v1.1 | Env-file SA fallback (GOOGLE_APPLICATION_CREDENTIALS) |
| v2 | Named sessions: `gemini_new_session`, `session_name` routing, `gemini_list_sessions` |
| v2.5 | Apple Keychain auth: SA JSON stored in Keychain, loaded to memory at startup, macOS only |
| v3 | `gemini_set_transcript_dir(path)` — per-project transcript routing without config edit |
| v4 | Sliding window context management for very long sessions |
| v5 | Evaluate: contribute Vertex AI auth back to rlabs/gemini-mcp as upstream PR |

---

## Resolved Decisions

- **Language**: Python 3.11+
- **Repo**: `PCS-LAB-ORG/gemini-bridge` (private)
- **Auth v1**: Vertex AI + ADC; env-file SA as fallback
- **Auth v2**: Apple Keychain for service account (DLP-safe, no disk artifact)
- **Transcript default**: `{repo_root}/session-summaries/`
- **Session model**: Single persistent session in v1; named sessions in v2
- **Tool design**: 5 specialized tools with per-tool system prompt personas
- **Thinking control**: Named levels (none/low/medium/high), Claude decides per call
- **Config UX**: `~/.config/gemini-bridge/config.json` written by `setup.sh`
- **Error handling**: Auth failures returned as tool results, server never crashes
- **Code standards**: SOLID throughout, no workarounds, ruff + mypy strict, file-level docstrings
- **Documentation**: `docs/` (8 files) + README.md ship with v1; style follows lab-cleanup baseline
