#!/usr/bin/env bash
# Serve a local GGUF with llama.cpp for opencode.
# Loads the GGUF directly (no conversion). 128k context.
set -euo pipefail

LLAMA_SERVER="${LLAMA_SERVER:-/home/apoman123/llama.cpp/build/bin/llama-server}"
GGUF_DIR="/home/apoman123/SoftwareTeam/ggufs"

# Model to serve. Override with: MODEL=...IQ4_NL.gguf ./serve-llama.sh
# MODEL="${MODEL:-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf}"
MODEL="${MODEL:-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ4_NL.gguf}"

# The id opencode sends in requests; must match the model key in opencode.jsonc.
# ALIAS="${ALIAS:-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-Q4_K_M}"
ALIAS="${ALIAS:-Qwen3.6-35B-A3B-Uncensored-HauhauCS-Aggressive-IQ4_NL}"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8090}"
CTX="${CTX:-262144}"   # 32k context window (overridable: CTX=... ./serve-llama.sh)

# This is a ~21GB MoE model but the GPU has only 16GB VRAM, so full offload won't fit.
# --cpu-moe keeps the (large) Mixture-of-Experts weights on CPU RAM while -ngl 99 puts
# the rest (attention/shared layers) on the GPU. Flash-attn + q8_0 KV cache keep the
# context's KV footprint small so it fits in the remaining VRAM. Lower CTX or raise it
# back to 131072 if you have headroom.
exec "$LLAMA_SERVER" \
  --model "$GGUF_DIR/$MODEL" \
  --alias "$ALIAS" \
  --host "$HOST" --port "$PORT" \
  --ctx-size "$CTX" \
  --parallel 1 \
  --n-gpu-layers 99 \
  --flash-attn on \
  --cache-type-k q4_0 \
  --cache-type-v q4_0 \
  --jinja \
  -fit off \
  --metrics
