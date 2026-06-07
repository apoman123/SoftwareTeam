#!/usr/bin/env bash
# Set up the software-team project to run on a local GGUF model via llama.cpp.
#
# Two ways to use llama.cpp with this project, and this script prepares both:
#   1. In-process  — SWTEAM_LLM_PROVIDER=llama_cpp loads the GGUF directly through
#                     llama-cpp-python (installed by `uv sync --extra llama-cpp`).
#   2. HTTP server — ggufs/serve-llama.sh runs the compiled `llama-server`, which is
#                     OpenAI-compatible; point the project at it with the `openai`
#                     provider + OPENAI_BASE_URL. This needs the binary built, which is
#                     what the "Build llama.cpp" step below does.
set -euo pipefail

cd "$(dirname "$0")/.."

# Where to clone/build llama.cpp. Must match the LLAMA_SERVER path in ggufs/serve-llama.sh.
LLAMA_CPP_DIR="${LLAMA_CPP_DIR:-$HOME/llama.cpp}"
LLAMA_SERVER="$LLAMA_CPP_DIR/build/bin/llama-server"
GGUF_DIR="$(pwd)/ggufs"

echo "==> Installing Python dependencies with uv (incl. the llama-cpp extra)"
uv sync --extra dev --extra llama-cpp --extra search --extra dev --extra openai

# --- Locate a local GGUF -----------------------------------------------------------
GGUF_PATH="/home/apoman123/SoftwareTeam/ggufs" # modify your gguf file path
if [[ -d "$GGUF_DIR" ]]; then
  GGUF_PATH="$(find "$GGUF_DIR" -maxdepth 1 -name '*.gguf' | sort | head -n 1)"
fi

if [[ -z "$GGUF_PATH" ]]; then
  cat <<EOF

==> No .gguf file found in $GGUF_DIR
    Download a GGUF model into that directory (or set SWTEAM_CODER_MODEL /
    SWTEAM_NARRATIVE_MODEL to a .gguf path elsewhere) before running the team.
EOF
else
  echo "==> Found local GGUF: $GGUF_PATH"
fi

# --- Usage -------------------------------------------------------------------------
cat <<EOF

==> Done. Run the team on llama.cpp one of two ways:

  1) In-process (llama-cpp-python) — point the provider at the GGUF file:

       export SWTEAM_LLM_PROVIDER=llama_cpp
       export SWTEAM_CODER_MODEL="${GGUF_PATH:-/path/to/coder.gguf}"
       export SWTEAM_NARRATIVE_MODEL="${GGUF_PATH:-/path/to/narrative.gguf}"
       uv run software-team run --spec examples/sample_spec.md

  2) HTTP server (OpenAI-compatible) — serve the GGUF, then use the openai provider:

       ./ggufs/serve-llama.sh        # starts llama-server on 127.0.0.1:8090
       # in another shell:
       export SWTEAM_LLM_PROVIDER=openai
       export OPENAI_BASE_URL=http://127.0.0.1:8090/v1
       export OPENAI_API_KEY=sk-local        # any non-empty value
       export SWTEAM_CODER_MODEL="$(basename "${GGUF_PATH:-model}" .gguf)"
       export SWTEAM_NARRATIVE_MODEL="$(basename "${GGUF_PATH:-model}" .gguf)"
       uv run software-team run --spec examples/sample_spec.md

  Or offline (no model at all):

       uv run software-team run --spec examples/sample_spec.md --dry-run
EOF
