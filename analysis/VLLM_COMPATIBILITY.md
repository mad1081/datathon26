# vLLM 0.31.0: first wave compatibility audit

Checked 2026-10-17. Source/configuration verification only; no GPU inference, AWS action, Docker build/up, or weight download.
All seven selected checkpoints declare Apache-2.0. Exact weight/tokenizer revisions are pinned below. Runtime: vLLM 0.31.0 + Transformers 5.17.0.

| Exact HF ID | Weight/tokenizer revision | Server | TP | Status |
|---|---|---|---:|---|
| [Qwen/Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/blob/cc594898137f460bfe9f0759e9844b3ce807cfb5/README.md) | `cc594898137f460bfe9f0759e9844b3ce807cfb5` | g6e.2xlarge | 1 | first_wave |
| [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b/README.md) | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | g6e.2xlarge | 1 | first_wave |
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/README.md) | `c202236235762e1c871ad0ccb60c8ee5ba337b9a` | g6e.2xlarge | 1 | first_wave |
| [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md) | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | g7e.4xlarge | 1 | first_wave |
| [Qwen/Qwen3-VL-32B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct/blob/0cfaf48183f594c314753d30a4c4974bc75f3ccb/README.md) | `0cfaf48183f594c314753d30a4c4974bc75f3ccb` | g7e.12xlarge | 2 | first_wave |
| [OpenGVLab/InternVL3_5-38B](https://huggingface.co/OpenGVLab/InternVL3_5-38B/blob/de99855be3642cd44fe97c9b72d70e5ce2c07f69/README.md) | `de99855be3642cd44fe97c9b72d70e5ce2c07f69` | g7e.12xlarge | 2 | first_wave |
| [Qwen/Qwen3-VL-235B-A22B-Instruct-FP8](https://huggingface.co/Qwen/Qwen3-VL-235B-A22B-Instruct-FP8/blob/7fbcd8c9e2ad011808ed8a57d64c462605c3e381/README.md) | `7fbcd8c9e2ad011808ed8a57d64c462605c3e381` | g7e.24xlarge | 4 | optional |

## Support evidence

[v0.31.0 registry](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py) contains each exact architecture from its pinned HF config.

[Qwen2VLProcessingInfo](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen2_vl.py#L865) returns image=None, video=None (multiple items supported, subject to configured limits). Qwen2.5 and Qwen3 inherit this processor; Qwen3.5/3.8 inherit Qwen3 video/image handling.

[InternVL processor](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/internvl.py#L323) enables video for Qwen3 text_config when video_pad exists in the tokenizer. The pinned 38B tokenizer contains video_pad id 151656. Image and video fields are handled together; its transformer processor combines image_inputs and video_inputs in one BatchFeature.

| Model | Architecture | Multiple images | MP4 video | Images + video in one request |
|---|---|---|---|---|
| Qwen/Qwen2.5-VL-7B-Instruct | `Qwen2_5_VLForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |
| Qwen/Qwen3-VL-8B-Instruct | `Qwen3VLForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |
| Qwen/Qwen3.5-9B | `Qwen3_5ForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |
| Qwen/Qwen3.8-27B | `Qwen3_5ForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |
| Qwen/Qwen3-VL-32B-Instruct | `Qwen3VLForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |
| OpenGVLab/InternVL3_5-38B | `InternVLChatModel` | source verified | source verified | source verified; GPU smoke pending |
| Qwen/Qwen3-VL-235B-A22B-Instruct-FP8 | `Qwen3VLMoeForConditionalGeneration` | source verified | source verified | source verified; GPU smoke pending |

### Source links per model

- **Qwen/Qwen2.5-VL-7B-Instruct**: [pinned config](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct/blob/cc594898137f460bfe9f0759e9844b3ce807cfb5/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen2_5_vl.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).
- **Qwen/Qwen3-VL-8B-Instruct**: [pinned config](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen3_vl.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).
- **Qwen/Qwen3.5-9B**: [pinned config](https://huggingface.co/Qwen/Qwen3.5-9B/blob/c202236235762e1c871ad0ccb60c8ee5ba337b9a/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen3_5.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).
- **Qwen/Qwen3.8-27B**: [pinned config](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen3_5.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).
- **Qwen/Qwen3-VL-32B-Instruct**: [pinned config](https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct/blob/0cfaf48183f594c314753d30a4c4974bc75f3ccb/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen3_vl.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).
- **OpenGVLab/InternVL3_5-38B**: [pinned config](https://huggingface.co/OpenGVLab/InternVL3_5-38B/blob/de99855be3642cd44fe97c9b72d70e5ce2c07f69/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/internvl.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py), [vLLM source 3](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/transformers_utils/processors/internvl.py), [vLLM source 4](https://huggingface.co/OpenGVLab/InternVL3_5-38B/blob/de99855be3642cd44fe97c9b72d70e5ce2c07f69/tokenizer_config.json).
- **Qwen/Qwen3-VL-235B-A22B-Instruct-FP8**: [pinned config](https://huggingface.co/Qwen/Qwen3-VL-235B-A22B-Instruct-FP8/blob/7fbcd8c9e2ad011808ed8a57d64c462605c3e381/config.json), [vLLM source 1](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/qwen3_vl.py), [vLLM source 2](https://github.com/vllm-project/vllm/blob/v0.31.0/vllm/model_executor/models/registry.py).

## Material exceptions and limits

- **InternVL TP2:** vision encoder has 25 attention heads. Use `--mm-encoder-tp-mode data` (native supported flag), keeping decoder TP2. Do not split the vision heads across two ranks.
- **InternVL 64K:** checkpoint declares 40,960 tokens, with 32K multimodal SFT in the author card. The preset applies nested llm_config overrides with max_position_embeddings=65536 and YaRN factor=2, original_max_position_embeddings=32768. This adapts the [Qwen3-32B author guidance](https://huggingface.co/Qwen/Qwen3-32B#processing-long-texts) to its decoder; it is experimental for InternVL and must be validated. `VLLM_ALLOW_LONG_MAX_MODEL_LEN` is not used to bypass checks.
- **InternVL resolution:** generic max_pixels is unsupported. Config min_dynamic_patch=4 retains detail via an image canvas 896x1792 (+ thumbnail) for 464x848 input. Native video remains one 448x448 tile per frame in v0.31.0. The backend sends separate images. The image/video preprocessing difference is not concealed.
- **Qwen resolution:** min_pixels=400000 and max_pixels=524288; pinned smart_resize code tested on CPU. Original 464x848 becomes 476x868 (factor 28) or 480x864 (factor 32), avoiding downscale for backend image input. Native video may impose additional frame/total-token budgets.
- **235B FP8:** checkpoint has quant_method=fp8, dynamic activations, 128x128 weight blocks. Auto-detect checkpoint quantization; --dtype bfloat16 does not dequantize the checkpoint to BF16 weights.
- **Count vs token budget:** 160 image attachments + 1 video is allowed by the server count limit, but the tokenized request still must fit 65,536. Memory use at concurrency eight and multimodal startup profiling is unmeasured.
- **Backend:** exact origin/backend snapshot fc1af4d3660b942c9aa27502cbcd2bec71fb116b, unmodified. It uses images + timestamps, not native video. /api/v1/health alone does not prove model connectivity; Compose also waits for vLLM /health.

## Local evidence / pending GPU work

Local: 14 Compose/profile renders, exact metadata license/SHA checks, Python/Bash syntax, backend snapshot hashes; real synthetic MP4 encoding/decoding; HTTP images/video/mixed smoke against a CPU stub; actual backend health/auth/upload/job integration against the same stub. See [configuration report](vllm_config_validation.json) and [CPU report](vllm_cpu_validation.json).

Not run: container image build/pull, model loading, vLLM inference, semantic smoke on any model, VRAM/throughput measurement, TP/FP8 kernels, InternVL YaRN64K quality, final CUDA graphs, dataset evaluation, EC2 provisioning. No successful-model-run claim is made.

## Retained outside first wave

All previous candidates remain in models.json as not_first_wave. MiniCPM-V-4.7 still needs its separately pinned nightly; that nightly is not used by any selected first-wave model. These retained presets have not been requalified for the new 160-images/video/64K serving limits.

All seven pinned chat templates were also rendered locally with two images plus one video; the image/video markers were checked. This is Jinja rendering, not vLLM tokenization. [Template report](vllm_template_validation.json).

Full launch flags, bootstrap and smoke usage: [deployment README](../deploy/vllm/README.md).
