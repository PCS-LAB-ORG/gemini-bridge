# gemini-bridge — Project Instructions

Claude Code instructions for this repository. Overrides global `~/.claude/CLAUDE.md`
where explicitly noted.

## What this project is

An MCP server that gives Claude Code a live Gemini counterpart via Vertex AI. Five
specialized tools (brainstorm, review, debug, architect, ask) share a persistent chat
session per Claude Code process lifetime. Transcripts are appended to
`session-summaries/YYYYMMDD-HHMM-gemini-transcript.md`.

See `plan.md` for full specification. See `docs/` for detailed documentation.

## GitOps Workflow (overrides global CLAUDE.md)

### Branch model
```
main       ← PR from develop only; never a commit target
develop    ← integration; no direct commits (hook enforced)
  └── feature/issue-{N}-short-description
  └── fix/issue-{N}-short-description
```

### One issue = one branch = one squash commit

Before merging a feature branch to develop, squash all working commits to one:

```bash
git rebase -i develop          # squash all WIP commits to one clean commit
git checkout develop
git merge --no-ff --no-verify feature/issue-N-name   # no-verify: permitted ONLY here
git push origin develop
git branch -d feature/issue-N-name
```

### --no-verify policy
- **Permitted ONLY**: `git merge --no-ff --no-verify` when merging a feature branch to develop
- **Never permitted**: on feature branch commits, on develop → main PRs, or to skip ruff/mypy

### PR workflow
- PRs only for `develop → main`
- Feature branches merge directly to develop (squash + no-ff, no PR)
- PR body: `Relates to #N` — never `Closes #N`

## Code Standards

- SOLID throughout — see plan.md Code Quality Standards section
- All files begin with the module-level docstring header (see plan.md File Header Standard)
- `ruff check` and `mypy --strict` must pass clean before any PR
- No bare `except Exception`, no `# type: ignore` without comment, no `TODO` in merged code
- Tests live in `tests/` — one test file per source module

## Startup Checklist

1. Read `plan.md` for full spec
2. Read `docs/README.md` for documentation index (when populated)
3. Check open issues: `gh issue list --repo PCS-LAB-ORG/gemini-bridge`
4. Verify current branch: `git branch --show-current`

## Authentication (local dev)

```bash
gcloud auth application-default login
python -m gemini_bridge   # server starts using ADC automatically
```

See `docs/auth.md` for full auth setup including Keychain option (v2).
