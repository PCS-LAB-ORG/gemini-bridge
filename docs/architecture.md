# Architecture

## Component Diagram

```
__main__.py
  ├── load_config()          → config.py  → ~/.config/gemini-bridge/config.json
  ├── build_credentials()    → auth.py    → google.auth.credentials.Credentials
  ├── GeminiClient(config, creds)         → client.py
  ├── TranscriptWriter(dir, time)         → transcript.py
  └── build_server(client, transcript)   → server.py
        └── FastMCP + 5 registered tools → tools/*.py
```

## Data Flow (per tool call)

1. Claude Code sends an MCP tool call (e.g. `gemini_brainstorm`)
2. `server.py` routes to the registered tool function in `tools/brainstorm.py`
3. Tool calls `call_gemini()` from `tools/base.py` with the session name, system prompt, and prompt
4. `call_gemini()` calls `client.get_or_create_session()` — creates a chat session on first use
5. `client.ask()` builds a `GenerateContentConfig` with the thinking level, sends to Vertex AI
6. Response text is returned; `transcript.append()` writes the exchange to the Markdown file
7. Tool returns the response string as the MCP tool result to Claude Code

## Session Lifecycle

- **Created:** on first call to any tool, keyed by `tool_name:session_name`
- **Persists:** for the lifetime of the MCP server process (one Claude Code session)
- **Accumulates context:** Gemini's `Chat` object retains message history automatically
- **Destroyed:** when Claude Code restarts (new server process, new sessions)

Each tool uses its own session key (`gemini_ask:default`, `gemini_brainstorm:default`, etc.)
so the system prompt persona is locked for the session.

## Transcript Lifecycle

- **File created:** at server startup, named with the startup timestamp
- **File path:** `{transcript_dir}/YYYYMMDD-HHMM-gemini-transcript.md`
- **Appended:** after every successful Gemini response
- **Never truncated:** append-only; write errors go to stderr, never break tool calls
- **Per session:** one file per Claude Code process lifetime

## SOLID Notes

| Principle | How it's enforced |
|---|---|
| SRP | Each module owns exactly one concern |
| OCP | New tools: add file + one line in server.py. New auth: add loader + one branch |
| LSP | All auth paths return `Credentials`; all tools return `ToolResult` |
| ISP | Tools receive only `GeminiClient` — not server or config objects |
| DIP | `client.py` depends on `Credentials` abstraction; `server.py` depends on callables |
