# Configuration Reference

**Config file location:** `~/.config/gemini-bridge/config.json`

Created by `bash setup.sh`. Safe to edit by hand.

## Full example

```json
{
  "project": "my-gcp-project",
  "location": "global",
  "model": "gemini-2.5-flash",
  "default_thinking": "medium",
  "transcript_dir": "./session-summaries",
  "auth": {
    "method": "adc"
  }
}
```

## Field reference

### `project`

**Type:** string
**Example:** `"my-gcp-project"`
**Required when:** `auth.method` is `adc`, `env`, or `keychain`
**Omit when:** `auth.method = "api_key"` (Developer API does not use a GCP project)

Your GCP project ID. Must have the Vertex AI API enabled and `roles/aiplatform.user`
granted to your ADC credentials or service account.

---

### `location`

**Type:** string
**Default:** `"global"`
**Example:** `"us-central1"`

Vertex AI location. `"global"` works for all models and is the recommended default.

**Gemini 3.x models** (`gemini-3.*`) are **global-only** — they do not support specific
regional endpoints. If you set a region with a 3.x model, the server will fail to start
with a validation error.

**Gemini 2.5 models** (`gemini-2.5-flash`, `gemini-2.5-pro`) support `"global"` plus
specific regions: `us-central1`, `us-east4`, `europe-west1`, `asia-northeast1`, and
others. Use a specific region if you have data-residency requirements.

---

### `model`

**Type:** string
**Default:** `"gemini-2.5-flash"`
**Valid prefixes:** `gemini-2.*`, `gemini-3.*`

| Model | Speed | Cost | Notes |
|---|---|---|---|
| `gemini-2.5-flash` | Fast | Low | Default; good for most tasks |
| `gemini-2.5-pro` | Slower | Higher | Better for complex reasoning |
| `gemini-3.5-flash` | Fast | Low | Newest Flash generation |
| `gemini-3.1-pro-preview` | Slower | Higher | Newest Pro (preview) |

The model family (2.x vs 3.x) determines how thinking levels are translated to API parameters.
Mixing an unknown prefix causes a startup error.

---

### `default_thinking`

**Type:** string
**Default:** `"medium"`
**Valid values:** `none`, `low`, `medium`, `high`

Used when a tool call omits the `thinking` parameter. Claude overrides this per call when
it judges a different level is appropriate.

---

### `transcript_dir`

**Type:** string (path, `~` and `.` expanded relative to Claude Code's working directory)
**Default:** `"./session-summaries"`

Directory where transcript files are written. Created if it doesn't exist. Transcript files
are named `YYYYMMDD-HHMM-gemini-bridge-transcript.md` using the server startup time.

The default `./session-summaries` resolves relative to the project root where Claude Code
was launched — transcripts land in `your-project/session-summaries/` automatically, one
directory per project. Override with an absolute path (e.g. `"~/gemini-transcripts"`) to
collect transcripts globally instead.

---

### `auth.method`

**Type:** string
**Default:** `"adc"`
**Valid values:** `adc`, `env`, `keychain`, `api_key`

See [auth.md](auth.md) for full setup instructions for each method.

---

### `auth.keychain_service`

**Type:** string
**Default:** `"gemini-bridge"`
**Only used when:** `auth.method = "keychain"`

The service name used in `security find-generic-password -s {service}`.

---

### `auth.keychain_account`

**Type:** string
**Default:** `"vertex-sa"`
**Only used when:** `auth.method = "keychain"`

The account name used in `security find-generic-password -a {account}`.

---

### `auth.api_key_env`

**Type:** string
**Default:** `"GEMINI_API_KEY"`
**Only used when:** `auth.method = "api_key"`

The name of the environment variable holding your Google AI Studio API key. The key itself
is never stored in `config.json` — only the variable name. At server startup, the server
reads the key from this env var and raises an error if it is unset or empty.

Common values: `"GEMINI_API_KEY"` (AI Studio default), `"GOOGLE_API_KEY"` (alternative).
If both are set in your shell, `GOOGLE_API_KEY` takes precedence in the SDK.
