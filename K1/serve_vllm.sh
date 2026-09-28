#!/usr/bin/env bash
# Start one vLLM judge server. Usage: serve_vllm.sh <judge-name> <gpu> <port>
# Records the PID in $K1_WORKDIR/servers/<judge>.pid so it can be stopped by PID (kill "$(cat ...)").
# Agent-written (Claude Opus 5.5), 2026-09-28.
set -euo pipefail
JUDGE=$1; GPU=$2; PORT=$3
K1_WORKDIR=${K1_WORKDIR:?set K1_WORKDIR to a writable work directory}
HUB=${HF_HUB_CACHE:-$HOME/.cache/huggingface/hub}
case "$JUDGE" in
  qwen2.5-32b) REPO=models--RedHatAI--Qwen2.5-32B-Instruct-FP8-dynamic ;;
  llama3.1-8b) REPO=models--RedHatAI--Meta-Llama-3.1-8B-Instruct-FP8-dynamic ;;
  *) echo "unknown judge $JUDGE" >&2; exit 2 ;;
esac
[ "${K1_FALLBACK:-0}" = 1 ] && case "$JUDGE" in
  qwen2.5-32b) REPO=models--Qwen--Qwen2.5-32B-Instruct-AWQ ;;
  llama3.1-8b) REPO=models--hugging-quants--Meta-Llama-3.1-8B-Instruct-AWQ-INT4 ;;
esac
SNAP=$(ls -d $HUB/$REPO/snapshots/*/ | head -1)
mkdir -p "$K1_WORKDIR/servers" "$K1_WORKDIR/cache/tmp"
# Keep every cache under the work directory.
export VLLM_CACHE_ROOT=$K1_WORKDIR/cache/vllm XDG_CACHE_HOME=$K1_WORKDIR/cache TMPDIR=$K1_WORKDIR/cache/tmp \
  TRITON_CACHE_DIR=$K1_WORKDIR/cache/triton TORCHINDUCTOR_CACHE_DIR=$K1_WORKDIR/cache/inductor \
  VLLM_NO_USAGE_STATS=1 DO_NOT_TRACK=1
HF_HUB_OFFLINE=1 CUDA_VISIBLE_DEVICES=$GPU nohup vllm serve "$SNAP" \
  --served-model-name "$JUDGE" --port "$PORT" --host 127.0.0.1 \
  --max-model-len 32768 --gpu-memory-utilization 0.90 --enable-prefix-caching \
  --generation-config vllm --seed 20260928 \
  > "$K1_WORKDIR/servers/$JUDGE.log" 2>&1 &
echo $! > "$K1_WORKDIR/servers/$JUDGE.pid"
echo "started $JUDGE pid $(cat "$K1_WORKDIR/servers/$JUDGE.pid") gpu $GPU port $PORT model $REPO"
