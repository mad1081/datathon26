import argparse
import json
import sys
import time
from pathlib import Path

import config
from analyze import analyze_raw, to_contract
from prompt import build_system_prompt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", nargs="?", default=str(config.VIDEOS_DIR / "X-1.mov"))
    ap.add_argument("--temperature", type=float, default=None)
    ap.add_argument("--show-prompt", action="store_true")
    args = ap.parse_args()

    video = Path(args.video)
    if args.show_prompt:
        print(build_system_prompt())
        print("-" * 60)
    print(f"endpoint={config.VLM_BASE_URL} model={config.VLM_MODEL} fps={config.FPS} "
          f"max_frames={config.MAX_FRAMES} max_side={config.MAX_SIDE} thinking_off={config.DISABLE_THINKING}")
    t0 = time.time()
    raw = analyze_raw(video, temperature=args.temperature)
    t1 = time.time()
    print(f"frames={raw['n_frames']} decode={raw['frames_sec']:.1f}s vlm={raw['latency_sec']:.1f}s "
          f"attempts={raw['attempts']} usage={raw['usage']} error={raw['error']}")
    print("RAW TEXT:")
    print(raw["raw_text"])
    print("PARSED:", "ok" if raw["parsed"] is not None else "FAILED")
    contract = to_contract(raw, video)
    t2 = time.time()
    for v in contract["violations"]:
        for f in v["evidence_frames"]:
            f["image_base64"] = f"<{len(f['image_base64'])} b64 chars>"
    print("CONTRACT:")
    print(json.dumps(contract, ensure_ascii=False, indent=2))
    print(f"total={t2 - t0:.1f}s (analyze {t1 - t0:.1f}s, evidence {t2 - t1:.1f}s)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
