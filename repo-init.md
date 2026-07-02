# gemini-bridge — Repo Initialization Checklist

Run these steps once after the repo is created. Each step is idempotent — safe to re-run.

## Step 1 — Push main branch

The push hook has an exception for initial repo creation. Claude can run this directly:

```bash
git push -u origin main  # INITIAL-REPO-SETUP
```

The `# INITIAL-REPO-SETUP` marker tells the hook this is a first-push exception.
Without it the hook blocks. Do not reuse this marker for any other push to main.

## Step 2 — Make the repo public

No company IP, no internal config, no PANW-specific logic. The Vertex/ADC approach
is a genuine gap in the open-source MCP ecosystem. Branch protection requires a public repo
on the free GitHub plan.

```bash
gh repo edit PCS-LAB-ORG/gemini-bridge --visibility public
```

Confirm: https://github.com/PCS-LAB-ORG/gemini-bridge should show as Public.

## Step 3 — Set develop as the default branch

All new PRs and clones should default to develop, not main.

```bash
gh repo edit PCS-LAB-ORG/gemini-bridge --default-branch develop
```

## Step 4 — Configure branch protection: main

Via GitHub UI: Settings → Branches → Add rule → Branch name pattern: `main`

- [x] Require a pull request before merging
- [x] Require approvals: 1 (or 0 if solo — adjust to taste)
- [x] Require status checks to pass before merging (add CI checks once GitHub Actions is wired)
- [x] Do not allow bypassing the above settings
- [ ] Require linear history — leave OFF (we use --no-ff merge commits intentionally)

Or via API:
```bash
gh api repos/PCS-LAB-ORG/gemini-bridge/branches/main/protection \
  --method PUT \
  --field required_status_checks=null \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1}' \
  --field restrictions=null
```

## Step 5 — Configure branch protection: develop

Prevents direct commits to develop (backs up the pre-commit hook with a remote enforcement layer).

Via GitHub UI: Settings → Branches → Add rule → Branch name pattern: `develop`

- [x] Restrict pushes that create matching branches — only allow via PR or merge
- [ ] Require pull request — leave OFF (feature branches merge to develop without a PR)

Or via API:
```bash
gh api repos/PCS-LAB-ORG/gemini-bridge/branches/develop/protection \
  --method PUT \
  --field required_status_checks=null \
  --field enforce_admins=true \
  --field required_pull_request_reviews=null \
  --field restrictions='{"users":[],"teams":[]}'
```

## Step 6 — Verify

```bash
gh repo view PCS-LAB-ORG/gemini-bridge --json visibility,defaultBranchRef \
  --jq '"Visibility: \(.visibility) | Default branch: \(.defaultBranchRef.name)"'

gh api repos/PCS-LAB-ORG/gemini-bridge/branches/main/protection --jq '.required_pull_request_reviews'
```

Expected output: `Visibility: PUBLIC | Default branch: develop`

## Step 7 — Clone fresh (optional, verify everything works)

```bash
cd ~/dev/github
git clone https://github.com/PCS-LAB-ORG/gemini-bridge.git gemini-bridge-verify
cd gemini-bridge-verify
git branch -a
# Should show: main, develop, remotes/origin/main, remotes/origin/develop
# Default checkout should be: develop
rm -rf ../gemini-bridge-verify
```

---

Once all steps are complete, start the implementation session from `~/dev/github/gemini-bridge/`.
See `session-summaries/20260702-gemini-bridge-design-repo-setup.md` for full context.
