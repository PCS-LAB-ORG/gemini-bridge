# Configuration Reference

**Config file location:** `~/.config/gemini-bridge/config.json`

Created by `bash setup.sh`. Safe to edit by hand.

## Full example

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

## Field reference

### `project` (required)

**Type:** string
**Example:** `"my-gcp-project"`

Your GCP project ID. Must have the Vertex AI API enabled and `roles/aiplatform.user`
granted to your ADC credentials or service account.

---

### `location`

**Type:** string
**Default:** `"us-central1"`
**Example:** `"us-east4"`

Vertex AI region. Must support the Gemini model you're using. `us-central1` has the
widest model availability.

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

**Type:** string (path, `~` expanded)
**Default:** `"~/session-summaries"`

Directory where transcript files are written. Created if it doesn't exist. Transcript files
are named `YYYYMMDD-HHMM-gemini-transcript.md` using the server startup time.

For project-specific routing, update this to the active project's `session-summaries/`
directory. The v3 `gemini_set_transcript_dir` tool will allow per-session routing without
a config edit.

---

### `auth.method`

**Type:** string
**Default:** `"adc"`
**Valid values:** `adc`, `env`, `keychain`

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
