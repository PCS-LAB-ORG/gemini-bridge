# Development Guide

## Setup

```bash
git clone https://github.com/PCS-LAB-ORG/gemini-bridge.git
cd gemini-bridge
python3 -m pip install -e .
python3 -m pip install pytest pytest-asyncio
pre-commit install
pre-commit install --hook-type commit-msg
```

## Running tests

```bash
python3 -m pytest tests/ -q
```

105 tests across 7 modules. All mocked — no network calls, runs in under 2 seconds.

## Running the server locally

```bash
# Configure first
bash setup.sh

# Start the server (MCP stdio transport — reads protocol from stdin)
python3 -m gemini_bridge
```

To register with Claude Code and use tools interactively:
```bash
claude mcp add -s user gemini-bridge -- python3 -m gemini_bridge
claude mcp list
```

Note the `--` separator — without it, `-m` is parsed as a `claude` option.

## Watching logs

The server writes to a daily rotating log file at startup:

```bash
tail -f ~/.config/gemini-bridge/logs/$(ls -t ~/.config/gemini-bridge/logs/*.log | head -1 | xargs basename)
```

Set `GEMINI_BRIDGE_LOG_LEVEL=DEBUG` before starting Claude Code for per-call detail. See [docs/logging.md](logging.md) for full reference.

## Code quality

```bash
# Lint + format
ruff check src/ tests/
ruff format src/ tests/

# Security scan
bandit -c pyproject.toml -r src/

# All pre-commit hooks
pre-commit run --all-files
```

## Adding a new tool

1. Create `src/gemini_bridge/tools/{name}.py` following the pattern in any existing tool file.
   Required: `register(mcp, client, transcript)` function, file header docstring, system prompt string.

2. Add `register as register_{name}` import to `src/gemini_bridge/tools/__init__.py`.

3. Call `register_{name}(mcp, client, transcript)` in `src/gemini_bridge/server.py`.

4. Add tests to `tests/test_tools.py` — at minimum verify the tool registers without error and
   that `call_gemini()` error passthrough works.

5. Document in `docs/tools.md`.

That's it. No other files need to change — this is the Open/Closed principle in action.

## Branching workflow

See `CLAUDE.md` in the repo root for the full GitOps workflow. Key points:
- All branches from `develop`; no direct commits to `develop` or `main`
- One issue = one branch = squash all WIP commits + `--no-ff` merge to develop
- `--no-verify` is only permitted on the `git merge --no-ff` step (bypasses no-commit-to-branch hook)
- PRs only for `develop → main`

## File header standard

Every `.py` file must begin with the module-level docstring following the template in
`plan.md` (File Header Standard section). Required fields: file path, one-line description,
Responsibilities, Design notes (SOLID callouts), Raises, Used by, Imports.
