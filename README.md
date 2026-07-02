<h1 align="center">gemini-bridge</h1>
<h4 align="center">Gemini as a live sounding board for Claude Code — Vertex AI, persistent sessions, structured logging.</h4>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11+-blue.svg">
  <img alt="MCP" src="https://img.shields.io/badge/MCP-1.28-green.svg">
  <img alt="Vertex AI" src="https://img.shields.io/badge/Vertex%20AI-Gemini-orange.svg">
  <img alt="Auth" src="https://img.shields.io/badge/auth-ADC%20%7C%20env%20%7C%20Keychain-purple.svg">
  <img alt="Tests" src="https://img.shields.io/badge/tests-44%20passing-brightgreen.svg">
</p>

gemini-bridge is an MCP server that gives Claude Code a live Gemini counterpart. When Claude is working on a hard problem — an architectural decision, a tricky bug, a code review — it can consult Gemini as a second opinion without switching tools or context.

Sessions persist across all tool calls within a Claude Code session. Gemini accumulates context naturally across tools and turns. Every exchange is appended to a dated Markdown transcript file. The server logs to a daily rotating file so you can watch it live.

Five focused tools, each with a distinct system prompt persona. Not a 37-tool Swiss Army knife.

**Quick navigation:** [What it does](#what-it-does) | [Prerequisites](#prerequisites) | [Quick start](#quick-start) | [Configuration](#configuration) | [Auth methods](#auth-methods) | [Thinking levels](#thinking-levels) | [Roadmap](#roadmap) | [Full documentation](#full-documentation)

---

## What it does

| Tool | Persona | Required parameters |
|---|---|---|
| `gemini_ask` | Direct, precise — general purpose | `prompt` |
| `gemini_brainstorm` | Devil's advocate, unconventional | `topic` |
| `gemini_review` | Critical, severity-first | `content` |
| `gemini_debug` | Evidence-based, hypothesis-driven | `error` |
| `gemini_architect` | Opinionated, explicit tradeoffs | `description` |

All tools share optional `thinking` (`none`/`low`/`medium`/`high`) and `session_name` parameters. Claude picks thinking level based on question complexity.

**Session model:** One Gemini chat session per tool name per Claude Code process. Context accumulates naturally within a session — later calls can reference earlier ones.

**Transcript logging:** Every exchange appended to `{transcript_dir}/YYYYMMDD-HHMM-gemini-transcript.md`.

**Server logging:** Structured logs at `~/.config/gemini-bridge/logs/YYYYMMDD-gemini-bridge.log`. See [docs/logging.md](docs/logging.md).

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.11+ | `python3 --version` |
| gcloud CLI | [Install guide](https://cloud.google.com/sdk/docs/install) |
| GCP project | With Vertex AI (Agent Platform) API enabled |
| Claude Code | MCP-enabled version |
| Auth | ADC, SA key file, or Apple Keychain — see [Auth methods](#auth-methods) |

---

## Quick start

```bash
# 1. Clone and install
git clone https://github.com/PCS-LAB-ORG/gemini-bridge.git
cd gemini-bridge
pip install -e .

# 2. Configure (interactive wizard — reads existing config as defaults on re-run)
bash setup.sh

# 3. Register with Claude Code
claude mcp add -s user gemini-bridge -- python3 -m gemini_bridge

# 4. Verify
claude mcp list
```

Restart Claude Code after step 3. On next start you'll see startup entries in the log:

```
[gemini-bridge] 17:50:10 INFO  gemini_bridge.__main__: starting — auth=keychain model=gemini-3.1-pro-preview location=global
[gemini-bridge] 17:50:10 INFO  gemini_bridge.__main__: transcript → ~/session-summaries/20260702-1750-gemini-transcript.md
```

---

## Configuration

**Config file:** `~/.config/gemini-bridge/config.json` — created by `setup.sh`, safe to edit by hand.

| Field | Default | Description |
|---|---|---|
| `project` | — | GCP project ID (required) |
| `location` | `global` | Vertex AI location; `global` works for all models; specific regions for gemini-2.x only |
| `model` | `gemini-2.5-flash` | Gemini model ID (`gemini-2.*` or `gemini-3.*`) |
| `default_thinking` | `medium` | Thinking level when omitted per call |
| `transcript_dir` | `~/session-summaries` | Directory for exchange transcripts |
| `auth.method` | `adc` | `adc` · `env` · `keychain` |
| `auth.keychain_service` | `gemini-bridge` | Keychain service name (keychain method only) |
| `auth.keychain_account` | `vertex-sa` | Keychain account name (keychain method only) |

See [docs/configuration.md](docs/configuration.md) for full field reference including location constraints per model family.

---

## Auth methods

Three methods supported — `setup.sh` walks you through all of them.

**ADC (recommended for personal machines):**
```bash
gcloud auth application-default login
# Sets method: "adc" in config
```
One-time setup. SDK auto-refreshes. Note: `gcloud auth login` (CLI) and ADC are separate credential stores — see [docs/auth.md](docs/auth.md).

**Env file (service account key on disk):**
```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
# Sets method: "env" in config
```
Set the env var before starting Claude Code. Key file stays on disk — use only on full-disk-encrypted machines.

**Apple Keychain (recommended for DLP-sensitive environments, macOS only):**
```bash
security add-generic-password \
  -s "gemini-bridge" -a "vertex-sa" \
  -w "$(cat /path/to/sa-key.json)"
rm /path/to/sa-key.json   # remove disk copy
# Sets method: "keychain" in config
```
SA JSON loaded to memory at startup; zero disk artifact after store. `setup.sh` verifies the item exists and contains valid JSON before writing config.

**Minimum GCP role for service account:** `roles/aiplatform.user` (renamed from "Vertex AI Platform User" to "Agent Platform User" in 2026 — same role ID `roles/aiplatform.user`).

---

## Thinking levels

Claude picks per call based on question complexity. See [docs/tools.md](docs/tools.md) for full tool documentation.

| Level | Gemini 2.x (`thinking_budget`) | Gemini 3.x (`thinking_level`) |
|---|---|---|
| `none` | 0 tokens | MINIMAL |
| `low` | 1024 tokens | LOW |
| `medium` | 8192 tokens | MEDIUM |
| `high` | 32768 tokens | HIGH |

---

## Roadmap

| Release | Status | Highlights |
|---|---|---|
| 26.7.1 | ✓ Shipped | 5 tools · ADC, env + Keychain auth · persistent sessions · transcript logging · structured logging · full docs |
| 26.7.2 | Planned | Named sessions · per-project transcript routing · Google AI Studio API key auth |

See [docs/roadmap.md](docs/roadmap.md) for full phase breakdown and rationale.

---

## Full documentation

See [docs/README.md](docs/README.md) for the complete documentation index.
