# Video model research and bounded benchmark plan

Checked 17 October 2026 against authors' Hugging Face cards, code repositories and papers. No competition video or frame was uploaded or inspected through a cloud model. No GPU was rented, model installed or inference benchmark run during this research. Hardware figures below are planning estimates, not measured requirements.

**Serving compatibility update:** [the pinned vLLM audit](VLLM_COMPATIBILITY.md) supersedes inference-path assumptions below. Stable 0.31.0 has native Cosmos3 understanding support without the older plugin architecture override. MiniCPM-V 4.7 requires the audited newer development build and Transformers 5.18.0. Multi-image support was verified in source; GPU execution remains untested. Compose and presets are in `deploy/vllm/`.

## Updated recommendation: all eight first-wave models in parallel, then stop workers

User clarification: AWS budget is **$5,000**. The priority is the earliest comparative result: prepare the shortlist and evaluator, provision independent capacity for **all eight first-wave models simultaneously**, run their assigned evaluations, save results, and stop each experimental instance as soon as it finishes. There is no 24-hour rental requirement. Rotation is optional for later experiments; it must not serialize the first wave. Final-serving capacity is a separate phase. The historical sections below preserve earlier research; this update supersedes their allocation and screening recommendations.

### Shortlist with release provenance

Dates are public release dates, not training-data cutoffs. Strengths describe documented design or author evaluations. Suitability for Forte is an engineering hypothesis; no footage inference or comparative benchmark has been run.

| First-wave candidate | Public release | Why test / principal tradeoff | Initial BF16 planning target |
| --- | --- | --- | --- |
| [Qwen/Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B) | 2026-03-02 | Compact hybrid-attention multimodal baseline; establishes whether larger models add value. Small-model capacity and frame/token budget may limit difficult action interpretation. | 48 GB sufficient planning class; 96/141 GB pooled worker gives headroom |
| [Qwen/Qwen3.8-27B](https://huggingface.co/Qwen/Qwen3.8-27B) | 2026-08-14 | Newer dense model with native video and switchable thinking. Release improvements emphasize general/agentic work; do not assume proportional gains on cash actions. | 96 GB with bounded input, or 141 GB with more margin |
| [Qwen/Qwen3-VL-32B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-32B-Instruct) | 2025-10-21 | Explicit timestamp alignment and visual-detail architecture; useful temporal-localization baseline. More weight/cache memory than 8B; Instruct and Thinking are distinct checkpoints. | 96–141 GB |
| [openbmb/MiniCPM-V-4_5](https://huggingface.co/openbmb/MiniCPM-V-4_5) | 2025-08-26 | 3D resampler compresses groups of video frames; tests whether denser sampling helps short gestures. More frames still cost vision-encoder work; compression/detail tradeoff must be measured. | 48 GB class; shared 96/141 GB worker |
| [openbmb/MiniCPM-V-4.7-35B-A3B](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B) | 2026-10-12 | Recent MoE with early visual compression and selectable 4x/16x compression. Tests newer efficiency architecture. Only five days old; allow a bounded compatibility test. Its 3B active count does not make weights 3B. | Prefer 141 GB; 96 GB may fit bounded video, unmeasured |
| [zai-org/GLM-4.6V-Flash](https://huggingface.co/zai-org/GLM-4.6V-Flash) | 2025-12-08 | Independent 9B visual family and grounding/tool-use capabilities. Authors acknowledge overthinking, repetition and counting limitations. GLM-V repository maintenance ended 2026-09-02; serving-library support still exists. | 48 GB class; shared 96/141 GB worker |
| [nvidia/Cosmos3-Nano](https://huggingface.co/nvidia/Cosmos3-Nano), **Reasoner path only** | 2026-05-31 | Physical-world, action and temporal interpretation. Full checkpoint is 16B; reasoner tower is 8B. Use the documented reasoner architecture override, not video generation. Authors warn of wrong object states, causal relations and temporal order; only BF16 officially tested. | 96/141 GB worker; actual reasoner-only load to verify |
| [Qwen/Qwen3.5-122B-A10B](https://huggingface.co/Qwen/Qwen3.5-122B-A10B) | 2026-02-24 | Large-capacity test. About 244–250 GB BF16 weights including the discrepancy between language-model name and full artifact. More memory, model-loading and tensor-parallel complexity; test whether quality gain warrants it. | 4×96 GB or conservatively 4×141 GB, supported tensor parallelism |

Release evidence: [Qwen release history](https://github.com/QwenLM/Qwen3.8#news), [Qwen3-VL history](https://github.com/QwenLM/Qwen3-VL#news), [MiniCPM history](https://github.com/OpenBMB/MiniCPM-V/blob/main/docs/changelog_en.md), [GLM author announcement](https://z.ai/blog/glm-4.6v), [GLM Chinese history](https://github.com/zai-org/GLM-V/blob/main/README_zh.md). Cosmos date is in its model card. Exact checkpoint revisions must still be pinned at download time.

The Qwen/MiniCPM first-wave weights declare Apache-2.0; GLM Flash weights declare MIT (repository code Apache-2.0). Cosmos3 declares OpenMDW1.1 and commercial use; this is a separate license to retain/check, not Apache-2.0. Do not infer all derivatives have the same license.

### Longlist and explicit reasons for postponement

| Candidate | Date / scope | Decision |
| --- | --- | --- |
| [OpenGVLab/InternVL3_5-38B](https://huggingface.co/OpenGVLab/InternVL3_5-38B) | Family released 2025-08-26; Apache-2.0 weights, MIT repository | First reserve for a different visual encoder/tiling route. About 76 GB raw weights; use 141 GB or multiple GPUs for margin. The author demo samples only eight frames: replace that example sampling for our task; preserve true timestamps. This is a demo setting, not a model frame limit. |
| [nvidia/Cosmos3-Super](https://huggingface.co/nvidia/Cosmos3-Super) | 2026-05-31; 32B reasoner, 64B full two-tower artifact | Reserve if Nano shows useful action recognition. Author reasoner recipe uses tensor parallel size 4; reasoner-only loading must be verified. Do not use generation timings as video-understanding timings. |
| [nvidia/Cosmos-Reason2-8B](https://huggingface.co/nvidia/Cosmos-Reason2-8B) | Initial 2025-12-19; updated checkpoint 2026-03-10 | Useful fallback with Qwen3-VL base and physical-reasoning post-training. NVIDIA specifies minimum 32 GB and validated Hopper/Blackwell targets. Card describes motion blur, occlusion and simultaneous actions as failure modes. Gated download and NVIDIA Open Model License with attribution terms; not automatically equivalent to Apache. |
| [Qwen/Qwen3-VL-8B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct) | 2025-10-15 | Fast fallback and useful control against Cosmos-Reason2, which shares its base. |
| [Qwen/Qwen3.6-35B-A3B](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) | 2026-04-16 | Optional MoE control against MiniCPM4.7; prioritize a different family before many adjacent Qwen versions. Verify exact video runner before inclusion. |
| [zai-org/GLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash) | 2026-08-26; 320B total / 18B active, MIT | Track, but not first-wave: inspected card confirms multimodal image capability but did not establish a ready video inference path. FP8 artifact still needs roughly hundreds of GB. Name Flash is not a memory specification. |
| [openbmb/MiniCPM-V-4.6](https://huggingface.co/openbmb/MiniCPM-V-4.6) | 2026-05-11; about 1.3B | Edge-focused model; reserve for local fallback, not a mandatory quality-first candidate. |

InternVL date: [author history](https://github.com/OpenGVLab/InternVL#news-). Cosmos hardware: [NVIDIA prerequisites](https://docs.nvidia.com/cosmos/latest/prerequisites.html). GLM5.3 date/maintenance status: [author history](https://github.com/zai-org/GLM-V#project-updates).

A concrete scale tradeoff: Qwen's own comparison reports VideoMME without subtitles at 83.9 for Qwen3.5-122B-A10B versus 82.8 for Qwen3.5-27B. This is an author benchmark, not our accuracy and not a Qwen3.8 comparison. It motivates measuring marginal gain rather than assuming a fivefold weight footprint yields fivefold task quality. [Author table](https://huggingface.co/Qwen/Qwen3.5-122B-A10B#benchmark-results)

### Memory model and hardware pool

`VRAM ≈ resident weights + vision activations + attention/state caches + runtime workspace + concurrent-request overhead`.

Weights alone: BF16 about 2 bytes/parameter, FP8 about 1, INT4 about 0.5 plus scales/metadata. Model names sometimes omit vision modules. Quantization may change accuracy and kernel support; use BF16 first when memory permits. CPU RAM is separate and cannot replace GPU memory without transfer overhead. Prefer 128 GiB host RAM for single-GPU 27–38B workers. Keep frame count/resolution/context bounded even on large GPUs. Disk: reserve about 1–2 TB for the shortlist, caches and containers, plus durable result storage.

**Proposed first wave: eight instances, twelve GPUs, eight simultaneous model evaluations.** These are planning allocations with memory headroom, not measured minimums.

| Count | EC2 type | GPU / host RAM per instance | Assigned models | Combined hourly compute |
| --- | --- | --- | --- | --- |
| 6 | `g7e.4xlarge` | 1×96 GB / 128 GiB | Qwen3.5-9B; Qwen3.8-27B; Qwen3-VL-32B; MiniCPM4.5; GLM4.6V-Flash; Cosmos3-Nano reasoner, one model per host | $23.98896 |
| 1 | `g7e.12xlarge` | 2×96 GB / 512 GiB | MiniCPM4.7-35B-A3B, with supported tensor parallelism verified before the full run | $8.28608 |
| 1 | `g7e.24xlarge` | 4×96 GB / 1 TiB | Qwen3.5-122B-A10B, with supported tensor parallelism | $16.57216 |

Total **$48.84720/hour**, **$97.69/two hours**, **$146.54/three hours**, **$195.39/four hours** compute. This requires **240 G/VT-category vCPUs** in the region. A multi-GPU machine does not automatically combine its VRAM: the chosen runtime must support the model's parallel execution. If MiniCPM4.7 cannot use this route promptly, change its allocation/runtime or substitute the reserve; do not block the other seven models.

An alternative with more GPU memory and H200/NVSwitch is **two** `p5en.48xlarge` hosts: sixteen H200 GPUs with 141 GB each, 2 TiB host RAM per host, **$126.592/hour**, **$379.78/three hours**; requires 384 P-category vCPUs. Allocate independent lanes for all eight models and use remaining capacity for replicas. One eight-GPU P5en host with four GPUs assigned to the largest model only provides five initial model lanes and therefore does not meet the all-eight-parallel plan. Hardware selection depends on actual capacity, quotas and supported containers; memory alone does not establish throughput.

Hardware: [AWS P5/P5en](https://aws.amazon.com/ec2/instance-types/p5/), [AWS G7e](https://aws.amazon.com/ec2/instance-types/g7e/). Rates were extracted from the saved official AWS feed published 2026-10-15 for us-east-1 Linux On-Demand; see `aws_gpu_prices.json`. Disks, transfer and IPs excluded. Account capacity, credit applicability and quotas remain unverified. These are alternatives, not simultaneous purchase instructions.

### AWS billing: idle is billed, stopped compute is not

For the proposed ordinary Linux On-Demand instances, AWS bills every running second with a 60-second minimum per start. A running instance is billed even with no GPU utilization and no SSH connection. There is no 24-hour minimum. Completing Python, stopping Docker or closing SSH does not stop the EC2 instance. Issue **Stop instance** through EC2 and verify its state. Normal stopping/stopped instances do not accrue instance compute charges. Retained EBS volumes and allocated Elastic IPs continue to cost money; termination also requires checking which storage resources remain. Save results before stopping: local instance-store NVMe is erased. [AWS lifecycle and billing](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html)

### Parallel experiment lifecycle and credible timing

Prepare container adapters and the shared evaluator before renting the whole pool. Start all first-wave model workers in parallel; each performs its own short loading/decoding/schema/latency check before continuing its full evaluation. Do not wait for one model's complete evaluation before starting another. Cache/download approved revisions and isolate incompatible dependencies in separate containers. A task is `(model revision, preprocessing, prompt/rules version, split, repetition seed)` with explicit GPU-count/memory requirements. Reuse a loaded model for its assigned repeats. A finished worker either runs an immediately scheduled follow-up or saves results and stops its EC2 instance.

Save predictions, errors, real evidence references, timestamps, model/config revisions, latency and peak VRAM to durable private storage before stopping a host. Local instance-store NVMe is disposable. A worker only becomes idle after results are verified saved. On a single eight-GPU EC2 instance, idle individual GPUs cannot be stopped for a partial billing reduction: the whole instance is the billing unit. Switch to the smaller final-serving instance after experiments and rerun latency/contract checks there. Preserve final-service availability through judging.

Timing estimate for interchangeable single-GPU jobs: `wall time >= total job seconds / parallel workers`, plus download/load/warmup/stragglers; multi-GPU jobs need separate accounting. Eight models × 40 videos × ten repeats = 3,200 video jobs. At one minute each this is 53.3 worker-hours; even eight independent workers need about 6.7 hours before setup. One minute is an example, not a measured latency.

Report a first complete dev pass immediately, then update statistics as repeats finish. Ten repeats are possible; size replicas from measured throughput instead of promising their completion within three hours. For illustration, forty videos × ten repeats = 400 jobs per model: 30 seconds/video requires 3h20m on one sequential worker, 60 seconds requires 6h40m, and 180 seconds requires 20 hours, before setup. Finishing those 400 jobs in three hours requires at most 27 seconds/video or sufficient independent replicas. A 28-video dev split requires 280 jobs and at most 38.6 seconds/video for the same three-hour budget, excluding setup. Different model workers run concurrently, so the slowest lane controls completion.

Use identical video splits and documented input coverage for every candidate. Average per-run metrics, measure per-video verdict stability, and inspect event/timecode agreement; do not numerically average unrelated text answers or timestamps for different events. Repeating deterministic decoding ten times is not ten independent measurements of generalization. Keep model-selection data separate from the untouched holdout and report cold-start/setup separately from warm inference. A first ranking in 1–2 hours is conditional on measured runtime; forty videos cannot establish every edge case.

## Initial recommendation (historical, superseded by the update above)

Start with **Qwen3.5-9B**, **MiniCPM-V-4_5**, and **Qwen3.8-27B**. With the newly verified 96 GB EC2 option, use the original Qwen3.8 BF16 checkpoint first; if limited to a 48 GB GPU, use **Qwen3.8-27B-FP8**. This compares two compact model architectures with a larger-capacity candidate. Keep Qwen3-VL-8B-Instruct as an integration fallback and InternVL3_5-8B as an optional independent family. Three working evaluations are more valuable in this deadline than thirty partially installed checkpoints.

The winner is whichever satisfies our observed event recognition, temporal localization, evidence, false-positive and five-minute latency requirements. Generic video benchmark leaderboards do not establish the winner on this bank dataset. No current accuracy estimate is defensible before human review and local testing.

## Shortlist and licenses

| Exact model ID | Purpose | Video support and inference path | Weights / repository code |
| --- | --- | --- | --- |
| `Qwen/Qwen3.5-9B` | First compact baseline | Native image/video input; Transformers, vLLM or SGLang. Disable thinking initially and cap output/context to measure latency. | Apache-2.0 / Apache-2.0 |
| `openbmb/MiniCPM-V-4_5` | Different visual compression approach | Video frames plus temporal IDs; 3D resampler jointly compresses groups of frames. Author Transformers example with custom model code; official INT4 checkpoint exists. | Apache-2.0 / Apache-2.0 |
| `Qwen/Qwen3.8-27B-FP8` | Larger candidate on 48 GB hardware | Native video input; official fine-grained FP8 checkpoint; vLLM/SGLang/Transformers. Thinking can be disabled. | Apache-2.0 / Apache-2.0 |
| `Qwen/Qwen3.8-27B` | Same candidate without weight quantization on 96 GB hardware | Original BF16 checkpoint; one GPU with bounded video context and concurrency. | Apache-2.0 / Apache-2.0 |
| `Qwen/Qwen3-VL-8B-Instruct` | Mature fallback; timestamp-oriented architecture | Native video, explicit text/timestamp alignment; Transformers/vLLM/SGLang. The Instruct checkpoint avoids a separate long thinking phase. | Apache-2.0 / Apache-2.0 |
| `OpenGVLab/InternVL3_5-8B` | Optional different model family | Author example samples ordered frames and chats over their image embeddings; Transformers custom code or LMDeploy. Supply original timestamps ourselves. | Apache-2.0 model card / MIT root code repository |

Primary model sources: [Qwen3.5-9B](https://huggingface.co/Qwen/Qwen3.5-9B), [MiniCPM-V 4.5](https://huggingface.co/openbmb/MiniCPM-V-4_5), [official MiniCPM INT4](https://huggingface.co/openbmb/MiniCPM-V-4_5-int4), [Qwen3.8-27B FP8](https://huggingface.co/Qwen/Qwen3.8-27B-FP8), [Qwen3-VL-8B](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct), [InternVL3.5-8B](https://huggingface.co/OpenGVLab/InternVL3_5-8B).

Code licenses checked: [Qwen3.8 repository](https://github.com/QwenLM/Qwen3.8/blob/main/LICENSE) (the former Qwen3.5 repository redirects here), [Qwen3-VL repository](https://github.com/QwenLM/Qwen3-VL/blob/main/LICENSE), [MiniCPM repository](https://github.com/OpenBMB/MiniCPM-V/blob/main/LICENSE), [InternVL repository](https://github.com/OpenGVLab/InternVL/blob/main/LICENSE). Preserve applicable notices and record exact downloaded revisions. The model artifact and code repository have separate licenses; InternVL illustrates why both need checking.

Newest does not automatically mean best for a 22-hour build: [MiniCPM-V-4.7-35B-A3B](https://huggingface.co/openbmb/MiniCPM-V-4.7-35B-A3B) is another current Apache-2.0 video-capable option, with BF16/FP8/INT4 variants. Treat it as a reserve only after the first benchmark works. Its 3B active parameters do **not** imply only 3B parameters must fit in GPU memory; the full checkpoint is about 35B parameters. Its mobile memory claims rely on specialized expert scheduling and do not transfer directly to an ordinary CUDA deployment.

## What fits on which GPU

Model weights alone consume roughly `parameter_count × bytes_per_parameter`: 9B BF16 is roughly 18 GB; 27B BF16 roughly 54 GB; 27B FP8 roughly 27 GB. Actual memory is higher: vision components, tensors not quantized, quantization metadata, video activations, attention/KV caches, runtime workspaces and concurrency also consume VRAM. GB and GiB reporting differ. Quantization availability does not guarantee runtime or GPU-kernel compatibility.

| Model | Approximate planning envelope | 24 GB L4/A10G | 48 GB L40S | 80 GB A100 |
| --- | --- | --- | --- | --- |
| Qwen3.5-9B | Roughly 20–28+ GB BF16 for bounded video requests; quantized estimate roughly 10–18 GB | BF16 may fit with short windows; quantization gives headroom | Comfortable planning target for BF16, still cap frames | Plenty of headroom for bounded BF16 |
| MiniCPM-V 4.5 | Roughly 20–30+ GB BF16 depending on frames; INT4 roughly 9–16 GB | Prefer official INT4; limited BF16 may fit | Prefer BF16 first for fewer quantization variables | Bounded BF16 feasible |
| Qwen3.8-27B FP8 | Roughly 32–44+ GB for bounded video requests | Does not fit FP8 weights alone; separate 4-bit conversion may fit but adds setup/quality risk | Primary target for official FP8 | BF16 original model is a simpler alternative; FP8 kernel support must be checked |
| Qwen3-VL-8B | Roughly 20–28+ GB BF16; quantized roughly 9–16 GB | Short windows or quantization | BF16 target | Bounded BF16 feasible |
| InternVL3.5-8B | Roughly 20–28+ GB BF16; quantized roughly 9–16 GB | Short windows or quantization | BF16 target | Bounded BF16 feasible |

All ranges are engineering estimates, **not author guarantees or measured minimums**. Frame resolution/count can move usage outside these ranges. A runtime that reserves most VRAM for cache will show high allocation even when the model itself needs less. Use one request per GPU initially. With an actual GPU selected, measure peak allocation and process the longest supplied video before declaring the configuration viable. System RAM is separate: 32 GB RAM is workable for compact checkpoints, while 64 GB is a safer planning target for downloading/loading larger models. Container images and multiple weight copies can need well over 100 GB disk.

The local RTX 4050 with 6 GB VRAM is useful for decoding, UI work and small-model experiments; it is not a comfortable target for these full checkpoints with multi-frame context. Do not extrapolate phone demonstrations to a five-minute end-to-end guarantee.

### Follow-up: 96 GB EC2 option

The root agent checked current AWS data and saved `analysis/aws_gpu_prices.json`: `g7e.2xlarge` offers one RTX PRO 6000 Blackwell GPU with 96 GB VRAM and 64 GiB system RAM at $3.36312/hour in us-east-1 Linux on-demand. Pairing it with `g6e.2xlarge` (48 GB L40S, $2.24208/hour) for 22 hours is approximately **$123.31 compute**. This excludes storage, transfer, tax and continued operation after those 22 hours; credits and quotas remain account-specific. Hardware source: [AWS G7e](https://aws.amazon.com/ec2/instance-types/g7e/); rate source is recorded in the local price snapshot.

Updated preference: run **Qwen3.8-27B BF16 on the 96 GB worker**, and alternate Qwen3.5-9B/MiniCPM-V-4_5 BF16 on the 48 GB worker. The 27B model has roughly 54 GB raw BF16 weights; an initial bounded-request planning allowance of roughly 62–85+ GB is plausible but unmeasured. 96 GB buys room to test unquantized weights, longer visual context and safe memory margins; it does not guarantee better task accuracy or permit unlimited context. Keep concurrency at one initially. Loading a roughly 54 GB checkpoint into 64 GiB system RAM needs streamed/sharded loading; avoid a loader that creates a full extra CPU copy.

Blackwell adds a software gate: use a current driver/container explicitly supporting that GPU, compatible PyTorch/CUDA, and current inference kernels. Official vLLM installation documentation describes Blackwell CUDA requirements and recommends predownloading FlashInfer kernels; otherwise startup may download/compile them, which matters for the offline requirement. Cache these before disabling egress. Do not copy a 2025 model card's old dependency pins indiscriminately. [vLLM GPU installation](https://docs.vllm.ai/en/latest/getting_started/installation/gpu/)

BF16 avoids quantization-specific conversion and kernel variables for the first accuracy baseline. Official FP8 remains a useful second configuration for throughput or the 48 GB fallback; benchmark rather than assuming zero accuracy loss. If the Blackwell stack is not functioning within a short setup budget, continue the known-compatible 48 GB compact-model baseline and test Qwen3.8 FP8 there. No setup or performance has yet been measured.

Model identity/date cross-check: the author's release log dates **Qwen3.5-9B to 2 March 2026** and **Qwen3.8-27B to 14 August 2026**. Both are published checkpoints, with explicit Apache-2.0 license files in their weight repositories. [Qwen release log](https://github.com/QwenLM/Qwen3.8#news), [Qwen3.5 weight license](https://huggingface.co/Qwen/Qwen3.5-9B/blob/main/LICENSE), [Qwen3.8 weight license](https://huggingface.co/Qwen/Qwen3.8-27B/blob/main/LICENSE). MiniCPM-V-4_5 is the video model from the 2025 report, not the similarly named MiniCPM-o-4_5 omnifunctional model; its current model card explicitly licenses weights and code under Apache-2.0. An exact MiniCPM-V-4_5 release day was not established here. We retain it for architecture diversity and an available inference recipe, not because it is the newest release.

## How a video VLM works

For an LLM developer, the useful conceptual chain is:

`MOV → decoder → sampled frames + timestamps → vision encoder → projector/resampler → visual tokens + text tokens → language model → structured event output`

The decoder turns H.264 into images. The model does not read the compressed MOV bytes as ordinary text. A vision encoder splits frames into patches and converts them into feature vectors. A projector maps features into the language model's representation; a resampler may compress many features into fewer tokens. The language model attends to the visual sequence together with our instructions and rule definitions, then generates text or JSON.

Temporal position matters. An ordered collection of still images can expose action changes, but timestamp encoding and temporal training help the model connect before/after relationships. Qwen3-VL includes interleaved spatial/temporal positions and timestamp alignment; its technical report discusses these architecture components. [Qwen3-VL technical report](https://arxiv.org/abs/2511.21631)

A model can answer questions about a video and generate descriptions, but its fluent answer is not itself evidence of reliable event detection. It can invent events, miss small objects, mix the roles of people, or assert that an unobserved action did not occur. Legal citation generation should be deterministic from a verified rule catalogue rather than invented by the VLM.

Sampling is a central tradeoff. A 120-second clip at 30 FPS contains 3,600 frames; sampling at 2 FPS leaves 240. More frames and more pixels cost visual tokens, GPU memory and processing time. An action lasting 0.3 seconds may disappear between sampled frames. Increasing the frame rate over a short candidate interval can resolve it. Cropping may reveal a small object but removes context and can miss events outside the crop.

Proposed processing: scan the whole video in overlapping windows at a bounded resolution/frame rate, produce candidate events, then inspect short candidate windows at greater frame density. Preserve original presentation timestamps at every stage. Ask for observable actions and supporting frame indices first; map those observations to supported rules second. Return 1–3 real decoded JPEGs, never generated evidence images. This is our proposed architecture, not a measured optimal setting.

The coarse scan can miss brief events, so it must be tested explicitly; a refinement pass cannot recover a candidate that was never proposed. One experiment should compare denser uniform sampling with the two-pass method rather than assume two-pass is superior.

## Initial experiment plan

1. Human/local review establishes observable classes, ambiguous labels and grouped splits. There are 40 unique clips, not 42 independent examples. Keep duplicates and related staged sequences together. Binary labels and isolated timestamps cannot evaluate class explanations or legal grounding by themselves.
2. Choose a development subset, freeze a small final holdout before prompts/model selection, and keep that holdout out of tuning. For instance, 28 unique clips for development and 12 for a final check if grouping and class balance permit. With this small dataset, report counts and errors; one clip changes a 12-clip result by 8.3 percentage points. Grouped cross-validation can be used on development data if time permits.
3. Run a smoke test on 2–4 development clips, including the longest and a negative. Record decode correctness, JSON validity, elapsed time, peak VRAM and whether timestamps resolve to actual source frames. Stop broken or consistently over-time configurations early.
4. Evaluate the three candidates on the same development clips and observable rule definitions. Give each a controlled frame/token budget, log checkpoint revision and prompt hash, and record failed jobs as failures. Include both no-thinking and bounded-thinking only if the latter has time headroom.
5. Compare whole-video confusion counts, precision/recall, timestamp absolute error for unambiguous matched labels, source-frame relevance and total job latency. Additional valid events can be unlabelled; human adjudication is needed before calling every extra event a false positive. The jury has not supplied a numerical timestamp tolerance.
6. Select one model and configuration, then run the frozen holdout once. Repeat only after a real bug is fixed, clearly recording that the holdout influenced further development. Repeatedly selecting among thirty models on the same forty clips can overfit model selection even without any gradient training.
7. Keep at least several hours for the API, source links, failure handling, offline test, deployment and submission. There is no need to keep every benchmark server alive until the deadline. Shut down experimental capacity after results are saved; retain the final service and a recovery path.

Suggested first hardware allocation after the AWS follow-up: one 96 GB worker for Qwen3.8 BF16 and one 48 GB worker alternating the compact candidates; the fallback is one 48 GB worker for Qwen3.8 FP8 and one 24–48 GB worker for compact models. Actual region, quota, GPU availability and credit applicability require account checks. A server priced at $0.80/hour is useful only if its GPU and VRAM match the model; the hourly price alone says nothing about inference suitability.

Synthetic data is optional after a baseline identifies a concrete gap. Refilming a few observable actions from a second angle can test viewpoint transfer. Crops, lighting variation and resizing test limited robustness; they do not create new independent evidence of accuracy. Never use transformed copies of validation videos for training, and do not treat a generative model's simulated bank procedure as authoritative ground truth.

## Reusable research and bank-adjacent work

[VadCLIP](https://github.com/nwpu-zxr/VadCLIP) and its [AAAI paper](https://arxiv.org/abs/2308.11681) adapt frozen CLIP features to weakly supervised temporal anomaly detection. It is useful for understanding lightweight temporal scoring; its crime/violence benchmarks are different from subtle cash-handling procedure violations. The inspected repository does not establish a clean commercial license for every released artifact, so it is a research reference, not an approved dependency.

[VideoMAEv2](https://github.com/OpenGVLab/VideoMAEv2) provides generic video representation and action recognition components, with MIT repository code. Its [author weight repository](https://huggingface.co/OpenGVLab/VideoMAE2/blob/main/README.md) declares Apache-2.0. These are feature/action models rather than conversational models that automatically explain bank procedures. They would need a task head and adequate labels; do not prioritize new training ahead of a working VLM baseline under this deadline.

An author [ATM anomaly-detection repository](https://github.com/kmehant/ATM-Video-Anomaly-Detection) exists for ATM vestibules, but it is not a bank's public cash-discipline production system; its visible root has no license file. It does not solve our exact case and is not approved for reuse. No verified openly licensed production bank-cashier compliance solution was found in this bounded search. This is not a claim that none exists.

FAQ 24 permits pretrained components, whereas FAQ 35 rejects ready-made solutions. Use authors' inference components and general papers, build our own case-specific observation logic, temporal handling, normative mapping, UI and jury API, and document attribution. A public GitHub repository is not by itself a commercial-use license.

## Deployment interpretation

A private model process on a rented EC2 GPU is self-hosted inference. A backend request to our own model server can use an OpenAI-compatible protocol without calling OpenAI or any external model provider. After dependencies/weights are downloaded, block inference egress and verify processing still succeeds. Use local file/frame paths rather than the internet-hosted example URLs in model cards.

This architecture matches the brief's stated goals of in-service inference and later bank-network deployment; the brief does not explicitly name EC2 as an approved hosting provider. Hosting interpretation and organizer wording should be stated honestly, rather than claiming an explicit AWS approval. The restriction on sending supplied video, frames and descriptions to cloud AI applies as written; hiding a development step from judges does not establish permission.
