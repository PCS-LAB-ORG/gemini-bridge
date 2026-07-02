#!/usr/bin/env bash
# setup.sh — gemini-bridge interactive configuration wizard
# Run once after pip install -e . to create ~/.config/gemini-bridge/config.json
# Safe to re-run: overwrites existing config with new values.

set -euo pipefail

CONFIG_DIR="$HOME/.config/gemini-bridge"
CONFIG_FILE="$CONFIG_DIR/config.json"

info()  { printf '\033[0;32m%s\033[0m\n' "$*"; }
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

echo
info "=== gemini-bridge setup ==="
echo

# --- auth method ---
echo "Auth method:"
echo "  1) adc — Application Default Credentials (recommended)"
echo "  2) env — GOOGLE_APPLICATION_CREDENTIALS env var"
AUTH_CHOICE=$(ask "Choice" "1")
case "$AUTH_CHOICE" in
    1|adc) AUTH_METHOD="adc" ;;
    2|env) AUTH_METHOD="env" ;;
    *) error "Invalid choice: $AUTH_CHOICE" ;;
esac

if [[ "$AUTH_METHOD" == "adc" ]]; then
    info "Checking ADC..."
    if ! gcloud auth application-default print-access-token &>/dev/null; then
        error "ADC not configured. Run: gcloud auth application-default login"
    fi
    info "ADC OK"
fi

# --- project ---
DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || true)
PROJECT=$(ask "GCP project" "$DEFAULT_PROJECT")
[[ -z "$PROJECT" ]] && error "GCP project is required."

# --- model (before location — location options depend on model family) ---
echo
echo "Model:"
echo "  1) gemini-2.5-flash        — fast, cheap (recommended)"
echo "  2) gemini-2.5-pro          — more capable"
echo "  3) gemini-3.5-flash        — newest Flash (global endpoint only)"
echo "  4) gemini-3.1-pro-preview  — newest Pro, preview (global endpoint only)"
MODEL_CHOICE=$(ask "Choice" "1")
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
    LOCATION=$(ask "Location" "global")
    if [[ -z "$LOCATION" ]]; then
        error "Location is required."
    fi
fi

# --- thinking level ---
echo
echo "Default thinking level:"
echo "  none   — no extended thinking (fastest)"
echo "  low    — light reasoning"
echo "  medium — balanced (recommended)"
echo "  high   — deep reasoning"
THINKING=$(ask "Level" "medium")
case "$THINKING" in
    none|low|medium|high) ;;
    *) error "Invalid thinking level: $THINKING" ;;
esac

# --- transcript dir ---
echo
TRANSCRIPT_DIR=$(ask "Transcript directory" "~/session-summaries")

# --- write config ---
mkdir -p "$CONFIG_DIR"
cat > "$CONFIG_FILE" <<EOF
{
  "project": "$PROJECT",
  "location": "$LOCATION",
  "model": "$MODEL",
  "default_thinking": "$THINKING",
  "transcript_dir": "$TRANSCRIPT_DIR",
  "auth": {
    "method": "$AUTH_METHOD"
  }
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
