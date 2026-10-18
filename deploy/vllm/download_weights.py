"""Download only the selected pinned snapshot. Invoked explicitly by bootstrap."""
from __future__ import annotations

import json
import os
from pathlib import Path

from serve import select_model


def main():
    from huggingface_hub import snapshot_download

    model, spec, _ = select_model(os.environ)
    snapshot = snapshot_download(repo_id=model, revision=spec['revision'],
                                 token=os.environ.get('HF_TOKEN') or None,
                                 max_workers=8,
                                 ignore_patterns=['*.bin', '*.pt', '*.pth', '*.gguf', '*.onnx', '*.h5', '*.msgpack'])
    expected = spec['revision']
    if Path(snapshot).name != expected:
        raise RuntimeError(f'Unexpected snapshot path {snapshot}; expected {expected}')
    print(json.dumps({'model': model, 'revision': expected, 'snapshot': snapshot}))


if __name__ == '__main__':
    main()
