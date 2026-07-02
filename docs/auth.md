# Authentication

## The critical distinction: `gcloud auth login` vs ADC

These are **separate credential stores** and **separate re-auth timelines**:

| Command | Authenticates | Stored at | Expiry |
|---|---|---|---|
| `gcloud auth login` | gcloud CLI only | `~/.config/gcloud/credentials.db` | Short-lived; org session-timeout policy |
| `gcloud auth application-default login` | SDKs and APIs | `~/.config/gcloud/application_default_credentials.json` | Refresh token; typically months |

The MCP server uses **ADC only**. When your gcloud CLI session expires and you re-auth with
`gcloud auth login`, the MCP server is **unaffected**. You only need to re-run
`gcloud auth application-default login` if ADC itself expires (rare on a personal machine).

**Verify ADC is working:**
```bash
gcloud auth application-default print-access-token
```
If this returns a token, the MCP server will authenticate successfully.

---

## Method 1: ADC (Default, Recommended)

**One-time setup:**
```bash
gcloud auth application-default login
```

This opens a browser and stores a refresh token at
`~/.config/gcloud/application_default_credentials.json`. The SDK auto-refreshes access tokens
from this refresh token — no repeated re-auth.

**Config:**
```json
{"auth": {"method": "adc"}}
```

**Minimum GCP permissions:** `roles/aiplatform.user` on the project.

---

## Method 2: Env File SA (v1 Fallback)

Set an environment variable pointing to a service account key file **before starting Claude Code**:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
```

The SDK picks up `GOOGLE_APPLICATION_CREDENTIALS` automatically as part of ADC fallback.

**Config:**
```json
{"auth": {"method": "env"}}
```

**Caution:** The key file persists on disk. Use only on full-disk-encrypted machines.

---

## Method 3: Apple Keychain (v2.5 Roadmap)

Store the service account JSON in macOS Keychain — loaded to memory at startup, zero disk artifact.

**One-time setup:**
```bash
security add-generic-password \
  -s "gemini-bridge" \
  -a "vertex-sa" \
  -w "$(cat /path/to/sa-key.json)"
rm /path/to/sa-key.json   # remove disk copy immediately
```

**Config:**
```json
{
  "auth": {
    "method": "keychain",
    "keychain_service": "gemini-bridge",
    "keychain_account": "vertex-sa"
  }
}
```

macOS only. The `security` CLI is not available on Linux.

---

## Troubleshooting

| Error message | Cause | Fix |
|---|---|---|
| `no ADC credentials found` | ADC not configured | `gcloud auth application-default login` |
| `token refresh failed` | ADC refresh token expired | `gcloud auth application-default login` |
| `GOOGLE_APPLICATION_CREDENTIALS not set` | Env var missing | `export GOOGLE_APPLICATION_CREDENTIALS=...` |
| `Keychain item not found` | Secret not stored | Re-run the `security add-generic-password` command |
| `not valid service account JSON` | Keychain value corrupted | Re-store the SA JSON key |
| `'security' CLI not found` | Not macOS | Keychain method is macOS-only |
