#!/usr/bin/env bash
# Set up the software-team project: Python deps + (optionally) local Ollama models.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "==> Installing Python dependencies with uv"
uv sync --extra dev

if ! command -v ollama >/dev/null 2>&1; then
  cat <<'EOF'

==> Ollama is not installed.
    Install it from https://ollama.com/download, then re-run this script,
    or just use dry-run mode (no model needed):

      uv run software-team run --spec examples/sample_spec.md --dry-run

EOF
  exit 0
fi

CODER_MODEL="${SWTEAM_CODER_MODEL:-qwen2.5-coder:7b}"
NARRATIVE_MODEL="${SWTEAM_NARRATIVE_MODEL:-llama3.1:8b}"

echo "==> Pulling Ollama models ($CODER_MODEL, $NARRATIVE_MODEL)"
ollama pull "$CODER_MODEL"
ollama pull "$NARRATIVE_MODEL"

cat <<EOF

==> Done. Run the team live:

    uv run software-team run --spec examples/sample_spec.md

  or offline (no model):

    uv run software-team run --spec examples/sample_spec.md --dry-run
EOF
