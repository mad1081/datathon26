#!/usr/bin/env bash
# Run manually on an existing Ubuntu NVIDIA Deep Learning AMI. Never creates EC2 resources.
set -Eeuo pipefail
trap 'printf "bootstrap failed at line %s; inspect preceding output\n" "$LINENO" >&2' ERR

SOURCE_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
REPO_DIR="${FORTE_REPO_DIR:-$HOME/datathon26}"
REPO_URL="https://github.com/mad1081/datathon26.git"
MODEL="${VLM_MODEL:-Qwen/Qwen3.5-9B}"
PROFILE="${VLM_PROFILE:-eval}"
ENV_FILE=""
CHECK_ONLY=0
WAIT_SECONDS="${FORTE_WAIT_SECONDS:-3600}"
while (($#)); do
  case "$1" in
    --repo-dir) REPO_DIR="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --profile) PROFILE="$2"; shift 2 ;;
    --check-only) CHECK_ONLY=1; shift ;;
    --help|-h)
      cat <<'HELP'
Usage: bash deploy/ec2/bootstrap.sh [--repo-dir DIR] [--model HF_ID]
       [--profile eval|final] [--env-file FILE] [--check-only]
Uses an existing .env unchanged; when present it takes precedence over --model/--profile.
Without an existing .env, generates a new secret and pinned model settings.
--check-only checks the local AMI/Docker/GPU tools; no clone, build, download, or start.
Normal mode clones the repo, overlays this deployment bundle, exports the pinned backend,
builds images, downloads weights, starts Compose, waits for health, and runs three smokes.
No AWS API calls are made. Requires an already provisioned Ubuntu NVIDIA GPU machine.
HELP
      exit 0 ;;
    *) printf 'Unknown argument: %s\n' "$1" >&2; exit 2 ;;
  esac
done
case "$PROFILE" in eval|final) ;; *) echo 'Profile must be eval or final' >&2; exit 2 ;; esac
[[ "$WAIT_SECONDS" =~ ^[1-9][0-9]*$ ]] || { echo 'FORTE_WAIT_SECONDS must be positive'; exit 2; }

for command in docker git python3 nvidia-smi; do
  command -v "$command" >/dev/null || { printf 'Missing prerequisite: %s\n' "$command" >&2; exit 1; }
done
[[ -r /etc/os-release ]] || { echo 'Expected Ubuntu DLAMI' >&2; exit 1; }
# shellcheck disable=SC1091
source /etc/os-release
[[ "${ID:-}" == ubuntu ]] || { echo 'This script targets Ubuntu Deep Learning AMI' >&2; exit 1; }
docker compose version
docker info >/dev/null
docker info --format '{{json .Runtimes}}' | python3 -c 'import json,sys; assert "nvidia" in json.load(sys.stdin), "Docker NVIDIA runtime is not configured"'
if command -v nvidia-ctk >/dev/null; then
  nvidia-ctk --version
elif command -v nvidia-container-cli >/dev/null; then
  nvidia-container-cli --version
else
  echo 'NVIDIA Container Toolkit is missing; configure it before continuing.' >&2
  exit 1
fi
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
if ((CHECK_ONLY)); then echo 'AMI prerequisites checked. Nothing started.'; exit 0; fi

REPO_DIR="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$REPO_DIR")"
if [[ ! -d "$REPO_DIR/.git" ]]; then
  git clone "$REPO_URL" "$REPO_DIR"
fi
# The deployment is intentionally uncommitted. Copy it from the uploaded bundle,
# without requiring a push or touching the backend branch. Refuse changed-file overwrite.
python3 - "$SOURCE_ROOT" "$REPO_DIR" <<'PY'
import pathlib, shutil, sys
source, target = map(lambda s: pathlib.Path(s).resolve(), sys.argv[1:])
if source != target:
    files = [source / 'docker-compose.yml', source / '.env.vlm.example', source / '.gitignore']
    files += [p for p in (source / 'deploy').rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc']
    for p in files:
        dest = target / p.relative_to(source)
        if not dest.resolve().is_relative_to(target):
            raise SystemExit(f'Unsafe overlay path: {dest}')
        if dest.exists() and dest.read_bytes() != p.read_bytes():
            raise SystemExit(f'Refusing to replace existing different file: {dest}')
    for p in files:
        dest = target / p.relative_to(source)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copyfile(p, dest)
PY
cd -- "$REPO_DIR"
BACKEND_COMMIT="$(python3 -c 'import json; print(json.load(open("deploy/backend-source.json"))["commit"])')"
if ! git cat-file -e "$BACKEND_COMMIT^{commit}" 2>/dev/null; then
  git fetch origin backend
fi
git cat-file -e "$BACKEND_COMMIT^{commit}"
python3 deploy/export_backend.py

if [[ -z "$ENV_FILE" ]]; then ENV_FILE="$REPO_DIR/.env"; fi
ENV_FILE="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).expanduser().resolve())' "$ENV_FILE")"
if [[ ! -f "$ENV_FILE" ]]; then
  python3 deploy/vllm/serve.py --model "$MODEL" --profile "$PROFILE" --write-env "$ENV_FILE"
fi
chmod 600 "$ENV_FILE"
COMPOSE=(docker compose --project-directory "$REPO_DIR" --env-file "$ENV_FILE" -f "$REPO_DIR/docker-compose.yml")
"${COMPOSE[@]}" config --quiet
"${COMPOSE[@]}" build vlm app
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint python3 vlm -c 'import os; from serve import select_model,check_runtime; _,s,c=select_model(os.environ); check_runtime(s,c); print("Runtime, architecture and GPU count checked")'
"${COMPOSE[@]}" run --rm --no-deps -T --entrypoint python3 vlm /opt/forte/download_weights.py
# Dependencies use vlm /health. app's health endpoint is /api/v1/health, not /health.
"${COMPOSE[@]}" up -d --wait --wait-timeout "$WAIT_SECONDS"
"${COMPOSE[@]}" exec -T vlm python3 -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=10); print("vLLM /health OK")'
"${COMPOSE[@]}" exec -T app python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health", timeout=10); print("app /api/v1/health OK")'
SMOKE_RUN="$(date -u +%Y%m%dT%H%M%SZ)"
"${COMPOSE[@]}" exec -T app python /opt/forte/smoke_multi_image.py \
  --base-url http://vlm:8000/v1 --mode all --output-dir "/data/smoke/$SMOKE_RUN"
echo "Ready. Only app port 8000 is published by default. API_KEY is in $ENV_FILE (not printed)."
echo "Smoke artifacts: app-data volume /data/smoke/$SMOKE_RUN"
