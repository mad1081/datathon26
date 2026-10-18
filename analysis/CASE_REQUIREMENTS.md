# ForteBank case requirements and dataset review

Reviewed on 17 October 2026. Sources: `C:\Users\123\Downloads\Кейс_ForteBank.docx`, all 10 numbered sections and all 35 FAQs; `C:\Users\123\Downloads\open.zip`; extracted `open/open_labels.xlsx` and all 42 MOV file containers. The archive is unpacked under `C:\Users\123\Desktop\DATATHON26\open`.

This case requires a deployed video analysis product with an exact jury API, local inference, grounded event explanations and evidence.

## Verified dataset findings

| Item | Observed result | Consequence |
| --- | --- | --- |
| Videos and labels | 42 MOV files and 42 label rows; every label has a matching file, with no unlabeled videos | All supplied records are accounted for |
| Class balance | 22 `нарушение`, 20 `без нарушения` | Nearly balanced at the file level |
| Unique contents | 40 unique SHA-256 hashes; 21 positive and 19 negative unique contents | Deduplicate or group by content hash before splitting |
| Positive duplicate | `Х-4.mov` and `Х-47.mov` are byte-identical, but labeled at 57 and 68 seconds | Preserve both annotations pending local review; could represent different events or an annotation inconsistency |
| Negative duplicate | `Х-5.mov` and `Х-48.mov` are byte-identical and both negative | Keep both in the same evaluation partition |
| Label fields | Filename, timestamp text, binary verdict | No event classes, bounding boxes, temporal intervals or rule IDs are supplied |
| Timestamp parsing | 22 positive timestamps; `1минута 8 секунда` means 68 seconds; all supplied timestamps fall inside the corresponding file duration | Normalize units, preserve original text, do not treat negative missing timestamps as zero |
| Naming | `X-1`, `X-2` use Latin X; remaining names use Cyrillic Х | Preserve exact identifiers and use an explicit mapping rather than assuming ASCII filenames |
| Duration | 11.634–142.534 seconds | Cover short clips and roughly 2.4 minute clips |
| Total duration | 1,444.181 seconds (24 min 4.181 sec), counting duplicate files; 1,299.881 seconds of unique file contents | Small dataset for developing broad temporal recognition |
| Sizes | 2,426,840–28,718,927 bytes per video; 292,870,994 video bytes total | Configure upload and proxy limits above the documented approximately 29 MB size |
| Codec | All 42 have `avc1` video (H.264) in MOV containers | Container and codec handling both matter |
| Resolution | All 42 coded at 464 × 848; identity display transform | Small visual details may be difficult; the local review must establish visibility |
| Timing | Mean FPS per video is approximately 29.758–30.000; 37 files have multiple sample durations in their timing tables | Use decoded presentation timestamps rather than assuming every frame is exactly 1/30 second |
| Audio | No audio tracks in any video | Matches the strictly visual task |

The machine-readable audit is `analysis/dataset_audit.json`. Its methods are label extraction, MOV container parsing and SHA-256 hashing. It does not establish that every frame decodes, identify observed violation types, or validate annotation semantics. All visual event review remains a local task.

Do not use filenames, clip duration, duplicate contents or staging patterns as shortcuts for detection. Split by complete video and duplicate group; inspect potential near-duplicate scenes locally before selecting a validation partition. Frames from one clip must not be distributed across training and validation.

## Mandatory requirements and acceptance evidence

The items below are obligations to implement or verify. None is marked complete merely because it is documented here.

| ID | Source | Requirement | Acceptance evidence |
| --- | --- | --- | --- |
| R01 | Sections 1–2, 4–5 | Working frontend and backend that accept a new video without manual code execution | Upload an unseen video through the browser and obtain the final result |
| R02 | Section 4 | Display processing status | Visible progress/status through success and failure |
| R03 | Sections 4–5, 10 | Exactly two completed analysis verdicts | `no_violation` or `violation`; UI shows the corresponding no-violation or possible-violation wording |
| R04 | Sections 4–5 | Support multiple possible violations in one video | A list of independently inspectable event results |
| R05 | Sections 4–5 | Type, timecode and description for each event | Every emitted event has nonempty type/description and a timestamp in seconds from the video start |
| R06 | Sections 4–5, 10 | Concrete evidence from the source video | Each event has 1–3 JPEG frames encoded in base64 with actual source timestamps |
| R07 | Sections 4–7 | Explain what is visible and why it may indicate a violation | Explanation uses observable facts; no invented motive, hidden transaction details or unseen actions |
| R08 | Sections 4, 6, 8 | Cite the rule and normative source and connect it to the visible evidence | Verified document title, rule text/summary, URL and applicable paragraph/section where available |
| R09 | Sections 3, 6 | Research and define the supported event taxonomy | Locally reviewed events mapped to publicly supportable rules; no assumed closed class list |
| R10 | Section 7 | Work with video and public information only | No dependency on bank systems, accounting records, internal logs or ForteBank infrastructure |
| R11 | Section 7 | Human review assistance, not a final legal or disciplinary finding | User wording states possible violation and describes evidence limits |
| R12 | Sections 2, 7; FAQ 21 | All inference runs inside the team's deployed service | No cloud LLM, vision, recognition or other AI processing of videos, frames or their descriptions |
| R13 | Section 7 | Offline portability after initial weight download | Run the processing stack with internet egress blocked and local weights/assets available |
| R14 | Sections 8, 10; FAQ 23 | Public UI and public API reachable by the jury | Verify both addresses from outside the host network |
| R15 | Section 10 | API protected by `X-API-Key` | Missing and incorrect keys rejected on upload and job-result routes |
| R16 | Section 10 | `POST /api/v1/analyze`, multipart field `file`, MOV input, returns `job_id` | Contract check using the supplied curl shape |
| R17 | Section 10 | `GET /api/v1/jobs/{job_id}` returns `processing`, `done` or `failed` | Pollable job lifecycle; technical failure is not a no-violation verdict |
| R18 | Section 10 | Completed JSON follows the published schema | Check keys, types, verdict/list consistency, timestamp bounds and decodable JPEG evidence |
| R19 | Section 10; FAQ 14 | Result within 5 minutes; downtime also counts as unprocessed | Measure upload-to-result time including queue delay and inference; target headroom below 300 seconds |
| R20 | Section 10 | Jury test videos cannot be used for training, published or given to third parties | Inference-only path, no adaptation or training writes from submitted test footage |
| R21 | Section 8 | Deliver UI URL, API URL and jury API key | Complete submission record with usable credentials |
| R22 | Section 8 | Startup and usage instructions | Reproducible installation/startup and upload/API examples |
| R23 | Section 8 | Explain architecture, approach and models | Component diagram or concise architecture description plus exact model/version list |
| R24 | Section 8 | Document normative sources and mapping method | Source catalogue with event-rule-evidence relationships |
| R25 | Section 8 | List supported violation types | Clear description and observable conditions for each supported type |
| R26 | Section 8 | List limitations and known error cases | Evidence-backed limitations from local validation, including occlusion and changed camera views |
| R27 | FAQs 6, 28, 29 | Hackathon-only data use, no audio analysis and no facial identification | Data handling instructions; no audio or face recognition components |
| R28 | FAQs 24, 34–35 | Permitted reuse and commercial compatibility | License inventory for code, models and weights; original case-specific solution; no prohibited ready-made solution |
| R29 | FAQs 4, 9; section 9 | Unseen videos, changed viewpoint and potentially unseen event types | Grouped holdout evaluation and explicit description of unsupported situations |

## Exact jury contract

```http
POST /api/v1/analyze
X-API-Key: <jury key>
Content-Type: multipart/form-data

file=<MOV bytes>
```

Returns a `job_id`. Poll `GET /api/v1/jobs/{job_id}` with the same key. The required completed shape is:

```json
{
  "job_id": "example",
  "status": "done",
  "verdict": "violation",
  "violations": [
    {
      "type": "Supported event type",
      "timecode_sec": 44.2,
      "description": "Visible observation, reason for possible violation, and verified source reference.",
      "evidence_frames": [
        {"timestamp_sec": 44.2, "image_base64": "<raw base64 JPEG>"}
      ]
    }
  ]
}
```

For `no_violation`, `violations` is empty. Do not include markdown fences in the actual API response, an image URL instead of base64, or an unsupported third verdict. The status response format for failures beyond `status: failed`, HTTP success codes and concurrency expectations are not fully specified in the brief.

The schema has no dedicated source field. Keep the required keys intact and include the verified citation in `description`; show structured source details in the UI. Additional API keys should be added only if the jury contract permits them. Numeric timestamps must correspond to the original video's timeline, including any decode or seek offsets.

## All 35 FAQs and their consequences

| FAQ | Organizer answer | Implementation or planning consequence |
| --- | --- | --- |
| 1 | At least 40 MOV clips, 10–145 seconds, FPS from 29, no audio, about 29 MB | Actual supplied set is 42 clips; support the entire stated range and realistic file-size overhead |
| 2 | Binary violation label and timestamp; event type omitted | Create event taxonomy and richer annotations through local review |
| 3 | Staged recordings; overhead single camera and single cash desk; cashier, customers and collectors | Treat this as the described collection setup, not a guarantee that role or authority is inferable from appearance |
| 4 | Test clips are similar; final verification changes camera angle | Avoid fixed pixel-coordinate or background shortcuts; evaluate viewpoint sensitivity |
| 5 | Dataset link available from the start on the site | Provided archive is available locally; track provenance |
| 6 | Data use only within the hackathon | Do not repurpose or publish footage; the answer does not grant post-event retention permission |
| 7 | Own footage, synthetic data and open datasets are welcome | Supplement if useful, with compatible rights and no prohibited cloud processing of the supplied footage |
| 8 | No closed type list; training categories undisclosed | Build a defensible taxonomy rather than assume an organizer-provided list |
| 9 | Test can contain types absent from training | State supported coverage; assess broader observable rules where feasible |
| 10 | Omission-event timestamp is the team's choice | Document a consistent convention, such as the point when a required visible step can no longer be completed within the observed sequence |
| 11 | If a violation is found and another fragment is unclear, follow the mandatory scenario | Return `violation` for a supported event; do not fabricate findings in the unclear fragment |
| 12 | Final evaluation has 5+ clips | Expect at least five; the upper count is unspecified |
| 13 | Jury uploads remotely through the team's link | Verify public reachability independently of the developer machine |
| 14 | Five-minute per-video limit | Instrument latency and queue time; benchmark the longest accepted clip |
| 15 | Detection score is per whole-video verdict; unjustified use of insufficient-data is penalized | Optimize/evaluate the binary video verdict; resolve inconsistency with the two-verdict contract as described below |
| 16 | Minimize false positives; missing violations is unacceptable | Track both false positives and false negatives; this aspiration does not establish an achievable zero-error guarantee or a scoring formula |
| 17 | Specific evidence frame and timestamp required | No numerical localization tolerance is supplied; use actual source frame timestamps |
| 18 | Automated evaluation using the common JSON schema | API validity is a required gate; no separate assumption of manual correction |
| 19 | Shortlisted teams pitch for 5 minutes plus 2 minutes Q&A; slides optional | Prepare a short demo/pitch after the service and API work |
| 20 | Pitching resolves ties | Be ready to explain evidence, limitations and architecture |
| 21 | Paid closed cloud APIs such as GPT, Gemini and Claude prohibited; local solution required | Use locally executed eligible models for the product; no cloud fallback |
| 22 | No provided GPUs or cloud credits | Select and benchmark the inference model against team-owned resources |
| 23 | Public URL mandatory | A localhost-only demonstration does not qualify |
| 24 | Prior code, templates and pretrained models allowed if open source and commercially usable | Review licenses for each dependency and model/weight artifact |
| 25 | MOV, about 29 MB | Configure frontend, backend and reverse proxy consistently; preserve MOV compatibility |
| 26 | UI and explanation language chosen by team | Russian is a practical initial choice given the brief; keep language consistent |
| 27 | Login, history, report export and batch upload unnecessary | These are optional product features; mandatory API-key authentication still applies |
| 28 | No sound; strictly visual analysis | Do not use audio features |
| 29 | Facial recognition and identity recognition forbidden | No face identification or biometric matching; avoid identifying named people |
| 30 | Only Kazakhstan acts, including NBK and Adilet | Verify authoritative Kazakhstan sources and applicable current versions |
| 31 | References without a precise paragraph and public documents of other banks accepted | Prefer precise applicable Kazakhstan sources; treat other-bank documents as supplemental context rather than automatically binding on ForteBank |
| 32 | No dataset violation requires an unavailable internal ForteBank rule | Look for publicly supportable rules rather than invent hidden policies |
| 33 | Deadline at 12:00 | Calendar date and timezone are absent; confirm them from the event schedule |
| 34 | ForteBank reserves commercial use rights | Keep dependencies and model weights compatible with commercial use; this is not an assertion of exclusive ownership transfer |
| 35 | Cloud API solutions or ready-made solutions cause disqualification | Build the case-specific solution; interpret alongside permitted reusable components in FAQ 24 |

## Conflicts and missing details to track

1. **Two verdicts versus insufficient data.** Sections 4, 5 and 10 explicitly allow only two analysis verdicts; FAQ 15 mentions a third. Implement the published binary interface. Keep quality limitations visible without inventing an API verdict. `failed` describes technical job failure, not a substitute classification. Organizer clarification would be useful for genuinely uninterpretable footage.
2. **Exact legal paragraph versus relaxed citations.** Section 4 requests a paragraph/section, while FAQ 31 allows references without it. Prefer exact verified references wherever possible and never generate a fabricated paragraph.
3. **Kazakhstan acts versus other banks' documents.** FAQ 30 sets the jurisdiction; FAQ 31 permits other-bank documents. The defensible default is an applicable Kazakhstan primary source, with bank documents clearly identified as supplementary.
4. **Reuse versus ready-made solutions.** FAQ 24 permits reusable open-source components; FAQ 35 disqualifies ready-made solutions. Build original orchestration, event logic, source mapping and product integration rather than submit an existing turnkey cash-discipline product. The boundary is not defined further.
5. **Public hosting versus local inference.** A public URL and offline-capable inference are compatible: expose the team's self-contained service to the jury while keeping all models inside it. The document does not define whether every form of rented server/GPU infrastructure is acceptable; choose team-controlled hardware by default and clarify hosting if needed.
6. **No regulatory field in JSON.** Put the citation in the required `description` field and provide a structured UI citation. Do not silently omit source evidence or assume arbitrary extra fields are accepted.
7. **Deadline and traffic.** Only 12:00 is given; date, timezone, concurrent requests and maximum test count are unspecified. Do not infer that noon on the review date is the submission deadline.
8. **Duplicate timestamps.** The identical positive files have two timestamps, 11 seconds apart. Verify both windows locally; neither automatic correction nor merging into one timestamp is justified yet.
9. **Cloud coding assistance.** Video-processing restrictions are explicit; code-only assistance is not explicitly addressed. Keep all video content, evidence frames and scene descriptions out of cloud tools.

## Scoring and priorities

| Criterion | Maximum | What to demonstrate |
| --- | ---: | --- |
| Detection | 25 | Correct whole-video violation/no-violation verdict |
| Localization | 15 | Correct event time and relevant source evidence |
| Classification | 15 | Correct event type |
| Rule grounding | 15 | Accurate sources and interpretation, without invented legal claims |
| Robustness | 10 | Unseen clips and changed camera viewpoint |
| Product readiness | 10 | Reliable uploads, clear status and usable results |
| Technical solution | 10 | Practical, extensible architecture and local execution |
| Total | 100 | All seven dimensions |

Detection, localization, classification and rule grounding account for 70 points. Product polish cannot compensate for unsupported event types or fabricated sources. Public reachability, the API contract and the five-minute limit are prerequisites to receiving processed results at all.

## Recommended implementation sequence

1. Review the 40 unique videos locally, retaining original annotation IDs and both timestamps on the duplicate positive. Record observable event types, precise source timestamps, event windows, uncertainty and normal counterexamples. Do not claim to know the violation taxonomy before this review.
2. Research the public Kazakhstan sources for each proposed type and record exact applicability. Distinguish visible evidence from conditions that cannot be assessed on video. No specific legal rule has yet been researched or validated in this audit.
3. Establish actual inference hardware, VRAM and available time. Choose commercially eligible local vision models and benchmark decoding plus inference on the longest clips. Do not choose a specific deployed model solely from a coding-assistant comparison.
4. Build the exact asynchronous API and a minimal upload/status/results UI. Use an internal queue if needed while keeping public status values compatible. Ensure failures and timeouts are visible.
5. Implement temporal analysis with source timestamps, event aggregation and retrieval of 1–3 real JPEG evidence frames. Use a locally stored, verified rule catalogue to produce explanations and citations.
6. Validate by whole-video/scene groups, keeping exact and near duplicates together. Report video recall/precision or confusion counts, event types, localization errors, evidence relevance and latency. Do not claim reliable unseen-type performance from the 40 unique clips alone.
7. Run with inference egress blocked, verify absence of remote AI calls and confirm cached weights/configurations/assets are sufficient. Test the public API from an external machine with valid and invalid keys and the maximum-duration clip.
8. Deliver the URLs, jury key, startup/use instructions, model and architecture description, source catalogue, supported types and known errors. Prepare the optional five-minute pitch and two-minute Q&A.

## Current completion boundary

Completed: safe extraction of the archive; reading the full case and every FAQ; reading all labels; matching all labels to files; hashing every video; inspecting all MOV containers; documenting obligations, inconsistencies, data issues and current coding-model options.

Remaining for solution development: local visual review and decoding validation; actual event taxonomy; legal source research; inference hardware/model choice; implementation; model evaluation; deployment; jury contract checks and submission. These steps have not been represented as already done.
