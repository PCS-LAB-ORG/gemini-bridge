# Transcripts

## File format

Each file is named `YYYYMMDD-HHMM-gemini-transcript.md` using the **server startup timestamp**.
All tool calls within one Claude Code session (one server process) append to the same file.

**Per-exchange format:**

```markdown
## [14:32:07] gemini_brainstorm — thinking: medium | session: default

**Prompt:**
How should we structure retry logic for the Pub/Sub consumer?

**Response:**
Three angles worth considering...

---
```

Header contains: time, tool name, effective thinking level, session name.

## Session boundaries

A new transcript file is created each time the MCP server starts — i.e., each time Claude
Code starts or restarts. Consecutive Claude Code sessions produce separate files.

This means:
- Calling `gemini_brainstorm` then `gemini_review` in one Claude Code session → same file
- Restarting Claude Code → new file, new timestamp, fresh sessions

## Transcript directory

**Default:** `~/session-summaries`

Configured in `transcript_dir` in `~/.config/gemini-bridge/config.json`.

The directory is created if it doesn't exist. The server never fails to start due to a
missing directory.

## Changing the transcript directory

Edit `~/.config/gemini-bridge/config.json` and restart Claude Code:
```json
{"transcript_dir": "/path/to/my-project/session-summaries"}
```

The v3 `gemini_set_transcript_dir(path)` tool will allow per-session routing without
a config edit — useful when working across multiple projects.

## Write failure behavior

If the transcript write fails (disk full, permissions error), the error is printed to
stderr and the tool call completes normally. Transcript failures never surface to Claude
or the user as tool errors.
