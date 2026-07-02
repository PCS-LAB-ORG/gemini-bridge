#!/usr/bin/env bash
# setup.sh — gemini-bridge interactive configuration wizard
# Run once after pip install -e . to create ~/.config/gemini-bridge/config.json
# Safe to re-run: overwrites existing config with new values. Existing values
# are read and used as prompt defaults so you only change what you want.

set -euo pipefail

CONFIG_DIR="$HOME/.config/gemini-bridge"
CONFIG_FILE="$CONFIG_DIR/config.json"

info()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
warn()  { printf '\033[0;33mWARN: %s\033[0m\n' "$*" >&2; }
error() { printf '\033[0;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

ask() {
    local prompt="$1" default="${2:-}"
    if [[ -n "$default" ]]; then
        printf '%s [%s]: ' "$prompt" "$default" >&2
    else
        printf '%s: ' "$prompt" >&2
    fi
    read -r REPLY
    echo "${REPLY:-$default}"
}

# --- load defaults from existing config ---
# Variables set here are used as prompt defaults throughout the wizard.
PREV_AUTH_METHOD="adc"
PREV_PROJECT=""
PREV_MODEL="gemini-2.5-flash"
PREV_LOCATION="global"
PREV_THINKING="medium"
PREV_TRANSCRIPT_DIR="~/session-summaries"
PREV_KEYCHAIN_SERVICE="gemini-bridge"
PREV_KEYCHAIN_ACCOUNT="vertex-sa"

if [[ -f "$CONFIG_FILE" ]]; then
    # shlex.quote ensures config values with spaces or special chars are safe to eval
    eval "$(python3 -c "
import json, shlex, sys
try:
    with open(sys.argv[1]) as f:
        d = json.load(f)
    auth = d.get('auth', {})
    fields = [
        ('PREV_AUTH_METHOD',      auth.get('method', 'adc')),
        ('PREV_PROJECT',          d.get('project', '')),
        ('PREV_MODEL',            d.get('model', 'gemini-2.5-flash')),
        ('PREV_LOCATION',         d.get('location', 'global')),
        ('PREV_THINKING',         d.get('default_thinking', 'medium')),
        ('PREV_TRANSCRIPT_DIR',   d.get('transcript_dir', '~/session-summaries')),
        ('PREV_KEYCHAIN_SERVICE', auth.get('keychain_service', 'gemini-bridge')),
        ('PREV_KEYCHAIN_ACCOUNT', auth.get('keychain_account', 'vertex-sa')),
    ]
    for k, v in fields:
        print(f'{k}={shlex.quote(str(v))}')
except Exception:
    pass
" "$CONFIG_FILE" 2>/dev/null || true)"
fi

# Map existing model string to menu choice number for the prompt default
case "$PREV_MODEL" in
    "gemini-2.5-flash")       PREV_MODEL_CHOICE="1" ;;
    "gemini-2.5-pro")         PREV_MODEL_CHOICE="2" ;;
    "gemini-3.5-flash")       PREV_MODEL_CHOICE="3" ;;
    "gemini-3.1-pro-preview") PREV_MODEL_CHOICE="4" ;;
    *)                        PREV_MODEL_CHOICE="1" ;;
esac

# Map existing auth method to menu choice number
case "$PREV_AUTH_METHOD" in
    "adc")      PREV_AUTH_CHOICE="1" ;;
    "env")      PREV_AUTH_CHOICE="2" ;;
    "keychain") PREV_AUTH_CHOICE="3" ;;
    *)          PREV_AUTH_CHOICE="1" ;;
esac

echo
info "=== gemini-bridge setup ==="
[[ -f "$CONFIG_FILE" ]] && info "(existing config loaded as defaults)"
echo

# --- auth method ---
echo "Auth method:"
echo "  1) adc     — Application Default Credentials (recommended)"
echo "  2) env     — GOOGLE_APPLICATION_CREDENTIALS env var (service account key file)"
echo "  3) keychain — Service account JSON stored in Apple Keychain (macOS only)"
AUTH_CHOICE=$(ask "Choice" "$PREV_AUTH_CHOICE")
case "$AUTH_CHOICE" in
    1|adc)      AUTH_METHOD="adc" ;;
    2|env)      AUTH_METHOD="env" ;;
    3|keychain) AUTH_METHOD="keychain" ;;
    *) error "Invalid choice: $AUTH_CHOICE" ;;
esac

if [[ "$AUTH_METHOD" == "adc" ]]; then
    info "Checking ADC..."
    if ! gcloud auth application-default print-access-token &>/dev/null; then
        error "ADC not configured. Run: gcloud auth application-default login"
    fi
    info "ADC OK"
fi

if [[ "$AUTH_METHOD" == "env" ]]; then
    if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
        warn "GOOGLE_APPLICATION_CREDENTIALS is not set in this shell."
        echo "  Set it before starting Claude Code:"
        echo "    export GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa-key.json"
        echo "  (Proceeding — you can set the env var later)"
    elif [[ ! -f "${GOOGLE_APPLICATION_CREDENTIALS}" ]]; then
        error "GOOGLE_APPLICATION_CREDENTIALS is set but file not found: ${GOOGLE_APPLICATION_CREDENTIALS}"
    else
        info "GOOGLE_APPLICATION_CREDENTIALS OK: ${GOOGLE_APPLICATION_CREDENTIALS}"
    fi
fi

# Keychain auth: prompt for service/account names and verify the item exists
KEYCHAIN_SERVICE="$PREV_KEYCHAIN_SERVICE"
KEYCHAIN_ACCOUNT="$PREV_KEYCHAIN_ACCOUNT"

if [[ "$AUTH_METHOD" == "keychain" ]]; then
    if [[ "$(uname)" != "Darwin" ]]; then
        error "Keychain auth requires macOS. Use adc or env on Linux."
    fi
    echo
    echo "Keychain item to read at server startup:"
    KEYCHAIN_SERVICE=$(ask "Keychain service name" "$PREV_KEYCHAIN_SERVICE")
    KEYCHAIN_ACCOUNT=$(ask "Keychain account name" "$PREV_KEYCHAIN_ACCOUNT")
    # Reject chars that would break JSON string interpolation in config.json
    if [[ "$KEYCHAIN_SERVICE" =~ [\"\\] ]] || [[ "$KEYCHAIN_ACCOUNT" =~ [\"\\] ]]; then
        error "Keychain service/account names must not contain quotes or backslashes."
    fi
    echo
    info "Verifying keychain item..."
    if ! SECRET=$(security find-generic-password -s "$KEYCHAIN_SERVICE" -a "$KEYCHAIN_ACCOUNT" -w 2>/dev/null); then
        echo "  Keychain item not found."
        echo "  Store your service account JSON first:"
        echo "    security add-generic-password \\"
        echo "      -s \"$KEYCHAIN_SERVICE\" \\"
        echo "      -a \"$KEYCHAIN_ACCOUNT\" \\"
        echo "      -w \"\$(cat /path/to/sa-key.json)\""
        echo "    rm /path/to/sa-key.json   # remove disk copy"
        error "Keychain item '$KEYCHAIN_SERVICE'/'$KEYCHAIN_ACCOUNT' not found. Store it first, then re-run setup."
    fi
    if ! echo "$SECRET" | python3 -c "import sys,json; json.load(sys.stdin)" 2>/dev/null; then
        error "Keychain item found but is not valid JSON. Re-store the service account key."
    fi
    info "Keychain item OK"
fi

# --- project ---
# Prefer gcloud active project; fall back to existing config value
DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
[[ -z "$DEFAULT_PROJECT" && -n "$PREV_PROJECT" ]] && DEFAULT_PROJECT="$PREV_PROJECT"
PROJECT=$(ask "GCP project" "$DEFAULT_PROJECT")
[[ -z "$PROJECT" ]] && error "GCP project is required."

# --- model (before location — location options depend on model family) ---
echo
echo "Model:"
echo "  1) gemini-2.5-flash        — fast, cheap (recommended)"
echo "  2) gemini-2.5-pro          — more capable"
echo "  3) gemini-3.5-flash        — newest Flash (global endpoint only)"
echo "  4) gemini-3.1-pro-preview  — newest Pro, preview (global endpoint only)"
MODEL_CHOICE=$(ask "Choice" "$PREV_MODEL_CHOICE")
case "$MODEL_CHOICE" in
    1) MODEL="gemini-2.5-flash" ;;
    2) MODEL="gemini-2.5-pro" ;;
    3) MODEL="gemini-3.5-flash" ;;
    4) MODEL="gemini-3.1-pro-preview" ;;
    *) error "Invalid choice: $MODEL_CHOICE" ;;
esac

# --- location (gemini-3.x is global-only; gemini-2.x allows regions) ---
echo
if [[ "$MODEL" == gemini-3.* ]]; then
    LOCATION="global"
    info "Location: global (required for $MODEL)"
else
    echo "Location (gemini-2.x supports 'global' or a specific region):"
    echo "  global — recommended; routes to lowest-latency region automatically"
    echo "  us-central1, us-east4, europe-west1, asia-northeast1, etc."
    LOCATION=$(ask "Location" "$PREV_LOCATION")
    [[ -z "$LOCATION" ]] && error "Location is required."
fi

# --- thinking level ---
echo
echo "Default thinking level:"
echo "  none   — no extended thinking (fastest)"
echo "  low    — light reasoning"
echo "  medium — balanced (recommended)"
echo "  high   — deep reasoning"
THINKING=$(ask "Level" "$PREV_THINKING")
case "$THINKING" in
    none|low|medium|high) ;;
    *) error "Invalid thinking level: $THINKING" ;;
esac

# --- transcript dir ---
echo
TRANSCRIPT_DIR=$(ask "Transcript directory" "$PREV_TRANSCRIPT_DIR")

# --- write config ---
mkdir -p "$CONFIG_DIR"

# Build auth JSON block — keychain method includes service/account fields
if [[ "$AUTH_METHOD" == "keychain" ]]; then
    AUTH_JSON="\"auth\": {
    \"method\": \"keychain\",
    \"keychain_service\": \"$KEYCHAIN_SERVICE\",
    \"keychain_account\": \"$KEYCHAIN_ACCOUNT\"
  }"
else
    AUTH_JSON="\"auth\": {
    \"method\": \"$AUTH_METHOD\"
  }"
fi

cat > "$CONFIG_FILE" <<EOF
{
  "project": "$PROJECT",
  "location": "$LOCATION",
  "model": "$MODEL",
  "default_thinking": "$THINKING",
  "transcript_dir": "$TRANSCRIPT_DIR",
  $AUTH_JSON
}
EOF

info "Config written to $CONFIG_FILE"
echo
info "=== Next steps ==="
echo
echo "  pip install -e ."
echo "  claude mcp add -s user gemini-bridge -- python3 -m gemini_bridge"
echo "  claude mcp list"
echo
info "Done. Restart Claude Code to activate gemini-bridge."
