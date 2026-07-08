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

## Method 2: Env File SA

Use a service account key file on disk. Set the environment variable **before starting Claude Code** — the server reads it at startup:

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json
```

The SDK picks up `GOOGLE_APPLICATION_CREDENTIALS` automatically as part of ADC credential discovery.

**Setup steps:**
1. Create or download a service account key in GCP IAM → Service Accounts → Keys
2. Grant the SA `roles/aiplatform.user` on your project
3. Store the JSON file in a secure location (e.g. `~/.config/gemini-bridge/sa-key.json`, mode 600)
4. Export the env var in your shell profile or before starting Claude Code
5. Run `bash setup.sh` and select option 2

**Config written by setup.sh:**
```json
{"auth": {"method": "env"}}
```

`setup.sh` verifies the env var is set and the file exists. If the var is not set in the setup shell, it warns but continues — you can set it later before starting Claude Code.

**Caution:** The key file persists on disk. Use only on full-disk-encrypted machines with restricted file permissions (`chmod 600`).

---

## Method 3: Apple Keychain (macOS only)

Store the service account JSON in Apple Keychain. The server reads it once at startup into memory — the raw JSON is never written to disk after the initial store, and disappears when the process exits.

**Why Keychain over a disk file:** A SA JSON on disk is a persistent secret at rest. Keychain provides OS-managed storage with ACL enforcement. This is the preferred service account path for DLP-sensitive environments.

**One-time setup — store the SA JSON:**
```bash
security add-generic-password \
  -s "gemini-bridge" \
  -a "vertex-sa" \
  -w "$(cat /path/to/sa-key.json)"
rm /path/to/sa-key.json   # remove disk copy immediately
```

**Run setup.sh and select option 3.** The wizard prompts for the service and account names, then verifies the item exists and contains valid JSON before writing config.

**Config written by setup.sh:**
```json
{
  "auth": {
    "method": "keychain",
    "keychain_service": "gemini-bridge",
    "keychain_account": "vertex-sa"
  }
}
```

**Minimum SA role:** `roles/aiplatform.user` — grants `aiplatform.endpoints.predict` only.

macOS only. The `security` CLI is not available on Linux.

---

## Method 4: API Key (Google AI Studio)

The simplest path — no GCP project, no `gcloud` setup, no service account. Get a key from
[aistudio.google.com/apikey](https://aistudio.google.com/apikey) and set an environment variable.

**One-time setup:**
```bash
export GEMINI_API_KEY=AIza...
```

Set this in your shell profile (e.g. `~/.zshrc`) or inject it via the Claude Code MCP env
config (recommended — keeps the key out of shell history):
```bash
claude mcp add -s user gemini-bridge -e GEMINI_API_KEY=AIza... -- python3 -m gemini_bridge
```

**Run setup.sh and select option 4.** The wizard asks for the env var name (default:
`GEMINI_API_KEY`) and warns if it is not currently set in the shell.

**Config written by setup.sh:**
```json
{
  "default_thinking": "medium",
  "transcript_dir": "./session-summaries",
  "auth": {
    "method": "api_key",
    "api_key_env": "GEMINI_API_KEY"
  }
}
```

`project` and `location` are omitted — they are not required by the Google AI Studio
(Developer API) endpoint.

**Positioning:**
- Use this method for personal use, quick setup, or when you don't have a GCP project
- ADC and Keychain methods remain first-class for team/enterprise use — they support larger
  quota tiers, org-managed access control, and service account rotation
- The API key is read from the env var at server startup and held in memory; it is never
  written to `config.json`

**Quota:** Google AI Studio free tier supports ~1,500 requests/day. Paid tier available.
Quota limits are lower than Vertex AI service account access.

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
| `'GEMINI_API_KEY' is not set or is empty` | API key env var missing | `export GEMINI_API_KEY=<your-key>` or set via MCP env config |
