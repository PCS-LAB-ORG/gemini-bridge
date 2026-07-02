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

# --- location ---
LOCATION=$(ask "Location" "us-central1")

# --- model ---
echo
echo "Model:"
echo "  1) gemini-2.5-flash        — fast, cheap (recommended)"
echo "  2) gemini-2.5-pro          — more capable"
echo "  3) gemini-3.5-flash        — newest Flash"
echo "  4) gemini-3.1-pro-preview  — newest Pro (preview)"
MODEL_CHOICE=$(ask "Choice" "1")
case "$MODEL_CHOICE" in
    1) MODEL="gemini-2.5-flash" ;;
    2) MODEL="gemini-2.5-pro" ;;
    3) MODEL="gemini-3.5-flash" ;;
    4) MODEL="gemini-3.1-pro-preview" ;;
    *) error "Invalid choice: $MODEL_CHOICE" ;;
esac

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
echo "  claude mcp add -s user gemini-bridge python -m gemini_bridge"
echo "  claude mcp list"
echo
info "Done. Restart Claude Code to activate gemini-bridge."
