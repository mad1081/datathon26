"""Resolve VLM_MODEL into pinned vLLM arguments. No shell interpolation.

--dry-run and --write-env work on a CPU host without importing vLLM.
Only normal container startup executes vLLM; this module never calls AWS.
"""
from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import sys

MANIFEST = Path(__file__).with_name("models.json")


def load_catalog():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def select_model(env):
    catalog = load_catalog()
    model_id = env.get("VLM_MODEL") or "Qwen/Qwen3.5-9B"
    if model_id not in catalog["models"]:
        raise ValueError(f"Unknown VLM_MODEL {model_id!r}. Use an exact ID from models.json.")
    return model_id, catalog["models"][model_id], catalog


def positive_int(env, name, default):
    value = int(env.get(name) or default)
    if value < 1:
        raise ValueError(f"{name} must be positive")
    return value


def build_argv(env):
    model_id, spec, catalog = select_model(env)
    defaults = catalog['defaults']
    tp = positive_int(env, "VLM_TP_SIZE", spec["default_tp"])
    images = positive_int(env, "VLM_MAX_IMAGES", defaults['limit_mm_per_prompt']['image'])
    videos = positive_int(env, "VLM_MAX_VIDEOS", defaults['limit_mm_per_prompt']['video'])
    max_len = positive_int(env, "VLM_MAX_MODEL_LEN", defaults['max_model_len'])
    batched = positive_int(env, "VLM_MAX_BATCHED_TOKENS", defaults['max_num_batched_tokens'])
    memory = float(env.get("VLM_GPU_MEMORY_UTILIZATION") or "0.90")
    if not 0 < memory < 1:
        raise ValueError("VLM_GPU_MEMORY_UTILIZATION must be between 0 and 1")
    profile = env.get('VLM_PROFILE') or 'eval'
    if profile not in catalog['profiles']:
        raise ValueError('VLM_PROFILE must be eval or final')
    eager = env.get("VLM_ENFORCE_EAGER") or str(catalog['profiles'][profile]['enforce_eager'])
    if eager not in {"0", "1"}:
        raise ValueError("VLM_ENFORCE_EAGER must be 0 or 1")
    argv = [
        "vllm", "serve", model_id,
        "--revision", spec["revision"],
        "--tokenizer-revision", spec["revision"],
        "--served-model-name", model_id,
        "--host", "0.0.0.0", "--port", "8000",
        "--dtype", "bfloat16",
        "--tensor-parallel-size", str(tp),
        "--max-model-len", str(max_len),
        "--max-num-seqs", str(positive_int(env, 'VLM_MAX_NUM_SEQS', defaults['max_num_seqs'])),
        "--max-num-batched-tokens", str(batched),
        "--gpu-memory-utilization", str(memory),
        "--limit-mm-per-prompt", json.dumps({"image": images, "video": videos}, separators=(",", ":")),
        "--generation-config", "vllm",
    ]
    if eager == "1":
        argv.append("--enforce-eager")
    if spec.get("trust_remote_code"):
        argv += ["--trust-remote-code", "--code-revision", spec["revision"]]
    if spec.get("processor_kwargs"):
        argv += ["--mm-processor-kwargs", json.dumps(spec["processor_kwargs"], separators=(",", ":"))]
    if spec.get('hf_overrides'):
        argv += ['--hf-overrides', json.dumps(spec['hf_overrides'], separators=(',', ':'))]
    if spec.get('request_defaults', {}).get('chat_template_kwargs'):
        argv += ['--default-chat-template-kwargs', json.dumps(spec['request_defaults']['chat_template_kwargs'], separators=(',', ':'))]
    argv += spec.get('extra_args', [])
    if env.get("VLLM_API_KEY"):
        argv += ["--api-key", env["VLLM_API_KEY"]]
    return argv


def redacted_argv(argv):
    result = list(argv)
    if "--api-key" in result:
        result[result.index("--api-key") + 1] = "<redacted>"
    return result


def check_runtime(spec, catalog):
    runtime = catalog["runtimes"][spec["runtime"]]
    installed = importlib.metadata.version("vllm")
    if not (installed == runtime["version"] or installed.startswith(runtime["version"] + ".")):
        raise RuntimeError(
            f"Expected vLLM {runtime['version']}, found {installed}. "
            "Generate the matching .env with --write-env and rebuild the selected image."
        )
    transformers = importlib.metadata.version("transformers")
    if transformers != runtime["transformers"]:
        raise RuntimeError(f"Expected Transformers {runtime['transformers']}, found {transformers}")
    if runtime.get("commit") and os.environ.get("VLLM_BUILD_COMMIT") != runtime["commit"]:
        raise RuntimeError("Nightly build commit does not match the audited image")
    from vllm import ModelRegistry
    if spec["architecture"] not in ModelRegistry.get_supported_archs():
        raise RuntimeError(f"Architecture {spec['architecture']} is absent from this runtime")
    import torch
    available = torch.cuda.device_count()
    tp = positive_int(os.environ, "VLM_TP_SIZE", spec["default_tp"])
    if available < tp:
        raise RuntimeError(f"Tensor parallel size {tp} needs at least {tp} visible GPUs; found {available}")


def write_env(path, env):
    model_id, spec, catalog = select_model(env)
    runtime = catalog["runtimes"][spec["runtime"]]
    build_argv(env)
    api_key = env.get('API_KEY') or secrets.token_urlsafe(32)
    if not re.fullmatch(r'[A-Za-z0-9_+/:=.-]{16,256}', api_key):
        raise ValueError('API_KEY must be 16-256 dotenv-safe characters; omit to generate one')
    values = {
        "VLM_MODEL": model_id,
        "VLLM_BASE_IMAGE": runtime["image"],
        "TRANSFORMERS_VERSION": runtime["transformers"],
        "VLM_IMAGE_TAG": runtime["local_image"],
        "VLM_TP_SIZE": str(positive_int(env, "VLM_TP_SIZE", spec["default_tp"])),
        "VLM_PROFILE": env.get('VLM_PROFILE') or 'eval',
        "VLM_ENFORCE_EAGER": env.get('VLM_ENFORCE_EAGER') or str(catalog['profiles'][env.get('VLM_PROFILE') or 'eval']['enforce_eager']),
        "VLM_MAX_IMAGES": str(positive_int(env, 'VLM_MAX_IMAGES', 160)),
        "VLM_MAX_VIDEOS": str(positive_int(env, 'VLM_MAX_VIDEOS', 1)),
        "VLM_MAX_MODEL_LEN": str(positive_int(env, 'VLM_MAX_MODEL_LEN', 65536)),
        "VLM_MAX_NUM_SEQS": str(positive_int(env, 'VLM_MAX_NUM_SEQS', 8)),
        "API_KEY": api_key,
        "APP_PORT": '8000',
    }
    if runtime.get('commit'):
        values['VLLM_BUILD_COMMIT'] = runtime['commit']
    # Exclusive creation protects existing user settings and secrets.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as target:
        target.write("# Generated from deploy/vllm/models.json; no resources were started.\n")
        target.write("\n".join(f"{key}={value}" for key, value in values.items()) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", help="Exact HF ID; overrides VLM_MODEL for this invocation")
    parser.add_argument('--profile', choices=['eval', 'final'], help='eval: eager=1; final: eager=0')
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true", help="Print argv only; no imports/downloads/launch")
    modes.add_argument("--write-env", metavar="PATH", help="Create a Compose env file; refuses overwrite")
    args = parser.parse_args()
    env = dict(os.environ)
    if args.model:
        env["VLM_MODEL"] = args.model
    if args.profile:
        env['VLM_PROFILE'] = args.profile
        env.pop('VLM_ENFORCE_EAGER', None)
    try:
        model_id, spec, catalog = select_model(env)
        if args.write_env:
            write_env(args.write_env, env)
            print(f"Created {args.write_env} for {model_id}")
            return
        argv = build_argv(env)
        if args.dry_run:
            print(json.dumps({"runtime": catalog["runtimes"][spec["runtime"]], "argv": redacted_argv(argv)}, indent=2))
            return
        os.environ.update(env)
        if spec.get('context_extension'):
            print('NOTE: InternVL 64K uses experimental YaRN; validate accuracy and memory on GPU.', flush=True)
        check_runtime(spec, catalog)
        print(shlex.join(redacted_argv(argv)), flush=True)
        os.execvp(argv[0], argv)
    except (ValueError, RuntimeError, FileExistsError, importlib.metadata.PackageNotFoundError) as error:
        parser.exit(2, f"Configuration error: {error}\n")


if __name__ == "__main__":
    main()

