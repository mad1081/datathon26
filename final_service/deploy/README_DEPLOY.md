# Deploy on one RunPod GPU pod (vLLM + app in one container)

Everything runs inside the pod: vLLM listens on `127.0.0.1:8001` (not exposed), the app on `0.0.0.0:8000`
(exposed as HTTP port). The app refuses any non-local `VLM_BASE_URL`.

## 1. Create the pod

| Setting | Value |
|---|---|
| Image | `vllm/vllm-openai:v0.31.0` |
| GPU | 1x 80 GB (H100/A100) for a ~30B MoE model; for 2 GPUs set `TP=2` |
| Container disk | 40 GB |
| Volume | 150 GB mounted at `/workspace` (model weights, jobs, logs) |
| Exposed HTTP ports | `8000` |
| Entrypoint override | `bash -c` (the image's own entrypoint is `vllm serve`) |
| Start command | see below |

Environment variables:

| Var | Example | Notes |
|---|---|---|
| `MODEL` | `Qwen/Qwen3-VL-30B-A3B-Instruct` | HF id; also the served model name |
| `API_KEY` | long random string | clients send `X-API-Key` |
| `TP` | `1` | tensor parallel size |
| `DISABLE_THINKING` | `0` / `1` | `1` for hybrid-reasoning models (Qwen3.5/3.6/3.8) |
| `N_SAMPLES` | `1` | `3` = majority vote of 3 parallel calls (temperature `SAMPLE_TEMPERATURE`, default 0.6) |
| `HF_HOME` | `/workspace/hf` | default in start.sh |
| `HF_TOKEN` | | only for gated models |

Optional: `THRESHOLD_OFFSET` (default 0), `WORKERS` (default 2), `MAX_FRAMES` (default 250),
`MAX_MODEL_LEN` (65536), `MAX_NUM_SEQS` (8), `GPU_MEM` (0.90), `EXTRA_VLLM_ARGS`, `TIME_BUDGET_SEC` (285, counted from upload).

Start command (code from git):

```bash
set -e; [ -d /workspace/repo ] || git clone --depth 1 -b <BRANCH> <REPO_URL> /workspace/repo; cd /workspace/repo/final_service && bash deploy/start.sh
```

Without git access: start the pod with start command `sleep infinity`, copy the folder
(`runpodctl send final_service` locally, `runpodctl receive <code>` in the pod under `/workspace`), then:

```bash
cd /workspace/final_service
MODEL=Qwen/Qwen3-VL-30B-A3B-Instruct API_KEY=secret nohup bash deploy/start.sh > /workspace/start.log 2>&1 &
tail -f /workspace/start.log
```

`start.sh` pip-installs only the packages the vLLM image lacks (python-multipart, opencv-python-headless, ...),
starts `vllm serve $MODEL --host 127.0.0.1 --port 8001 --max-model-len 65536
--limit-mm-per-prompt '{"image":256,"video":0}' --max-num-seqs 8 --gpu-memory-utilization 0.90 [--tensor-parallel-size $TP]`,
waits for `http://127.0.0.1:8001/v1/models`, then runs uvicorn on `0.0.0.0:8000`.
Logs: `/workspace/logs/vllm.log`, `/workspace/logs/app.log`.
If vLLM is already up on 8001 (e.g. app restart), it is reused.

## 2. Check

```bash
URL=https://<POD_ID>-8000.proxy.runpod.net
curl $URL/api/v1/health
curl -H "X-API-Key: $API_KEY" -F file=@X-1.mov $URL/api/v1/analyze          # -> 202 {"job_id": ...}
curl -H "X-API-Key: $API_KEY" $URL/api/v1/jobs/<job_id>                      # processing -> done | failed
```

UI: open `$URL/` in a browser, paste the API key.

## 3. Offline mode

After the first start has downloaded the weights into `/workspace/hf`, restart with `HF_HUB_OFFLINE=1`
(and `TRANSFORMERS_OFFLINE=1`) so nothing is fetched from the internet at runtime. The volume must stay
attached for that, otherwise the weights are gone.

## Notes

- Any model / transport / JSON failure gives `status: "failed"` with `error`, never `no_violation`.
- Long videos: frames are capped at `MAX_FRAMES`; if the prompt still exceeds `--max-model-len`, the app
  retries once with 60% of the frames. Lower `MAX_FRAMES` if the model's image tokens are larger.
- Pod restarts: unfinished jobs in `/workspace/data` are resumed; their time budget is already spent,
  so they run with a single sample.
