#!/usr/bin/env bash
# One GPU pod: local vLLM on 127.0.0.1:8001 + the analyzer app on 0.0.0.0:8000.
#   MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct API_KEY=secret bash deploy/start.sh
set -euo pipefail
cd "$(dirname "$0")/.."

: "${MODEL:?set MODEL to the HF model id, e.g. Qwen/Qwen3-VL-30B-A3B-Instruct}"
: "${API_KEY:?set API_KEY (clients send it as X-API-Key)}"
TP="${TP:-1}"
VLLM_PORT="${VLLM_PORT:-8001}"
APP_PORT="${APP_PORT:-8000}"
MAX_MODEL_LEN="${MAX_MODEL_LEN:-65536}"
MAX_NUM_SEQS="${MAX_NUM_SEQS:-8}"
GPU_MEM="${GPU_MEM:-0.90}"
LOG_DIR="${LOG_DIR:-/workspace/logs}"
export HF_HOME="${HF_HOME:-/workspace/hf}"
export DATA_DIR="${DATA_DIR:-/workspace/data}"
mkdir -p "$LOG_DIR" "$HF_HOME" "$DATA_DIR"

models_url="http://127.0.0.1:${VLLM_PORT}/v1/models"
vllm_up() {
  python3 -c "import sys, urllib.request; urllib.request.urlopen(sys.argv[1], timeout=5).read()" "$models_url" 2>/dev/null
}

# Install only what the vLLM image lacks, so its own fastapi/numpy/openai pins stay untouched.
missing=()
python3 -c "import fastapi" 2>/dev/null || missing+=("fastapi>=0.110")
python3 -c "import uvicorn" 2>/dev/null || missing+=("uvicorn[standard]>=0.29")
python3 -c "import multipart" 2>/dev/null || missing+=("python-multipart>=0.0.9")
python3 -c "import cv2" 2>/dev/null || missing+=("opencv-python-headless==4.10.0.84")
python3 -c "import openai" 2>/dev/null || missing+=("openai>=1.40")
if [ "${#missing[@]}" -gt 0 ]; then
  echo "installing: ${missing[*]}"
  pip install --no-cache-dir "${missing[@]}"
fi
command -v ffmpeg >/dev/null || echo "note: ffmpeg not found; videos OpenCV cannot decode will fail"

if vllm_up; then
  echo "vLLM already running on :${VLLM_PORT}"
else
  args=(serve "$MODEL" --host 127.0.0.1 --port "$VLLM_PORT"
        --max-model-len "$MAX_MODEL_LEN"
        --limit-mm-per-prompt '{"image":256,"video":0}'
        --max-num-seqs "$MAX_NUM_SEQS"
        --gpu-memory-utilization "$GPU_MEM")
  if [ "$TP" -gt 1 ]; then
    args+=(--tensor-parallel-size "$TP")
  fi
  # shellcheck disable=SC2206
  args+=(${EXTRA_VLLM_ARGS:-})
  echo "starting: vllm ${args[*]}"
  nohup vllm "${args[@]}" > "$LOG_DIR/vllm.log" 2>&1 &
  VLLM_PID=$!
  echo "waiting for vLLM (pid $VLLM_PID, log $LOG_DIR/vllm.log)"
  until vllm_up; do
    if ! kill -0 "$VLLM_PID" 2>/dev/null; then
      echo "vLLM exited during startup:"; tail -n 60 "$LOG_DIR/vllm.log"; exit 1
    fi
    sleep 5
  done
fi
echo "vLLM is up at $models_url"

export VLM_BASE_URL="http://127.0.0.1:${VLLM_PORT}/v1"
export VLM_MODEL="$MODEL"
export DISABLE_THINKING="${DISABLE_THINKING:-0}"
export N_SAMPLES="${N_SAMPLES:-5}"
export WORKERS="${WORKERS:-2}"
echo "starting app on 0.0.0.0:${APP_PORT} (N_SAMPLES=$N_SAMPLES DISABLE_THINKING=$DISABLE_THINKING WORKERS=$WORKERS)"
python3 -m uvicorn app.main:app --host 0.0.0.0 --port "$APP_PORT" 2>&1 | tee -a "$LOG_DIR/app.log"
