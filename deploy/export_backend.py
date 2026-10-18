"""Copy the pinned backend snapshot without checkout, reset, or branch edits."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def export(root=ROOT):
    lock = json.loads((root / 'deploy/backend-source.json').read_text(encoding='utf-8'))
    commit = lock['commit']
    archive = subprocess.run(
        ['git', '-c', f'safe.directory={root.as_posix()}', '-C', str(root),
         'archive', '--format=tar', commit, 'service'], check=True, capture_output=True,
    ).stdout
    files = {}
    with tarfile.open(fileobj=io.BytesIO(archive), mode='r:') as source:
        for member in source.getmembers():
            name = PurePosixPath(member.name)
            if name.is_absolute() or '..' in name.parts or name.parts[0] != 'service':
                raise ValueError(f'Unsafe archive path: {name}')
            if member.isdir():
                continue
            if not member.isfile():
                raise ValueError(f'Unsupported archive member: {name}')
            target = root.joinpath(*name.parts)
            # Reject symlinks/junctions escaping the checkout, including parent dirs.
            if not target.resolve().is_relative_to(root.resolve()):
                raise ValueError(f'Target escapes repository: {name}')
            data = source.extractfile(member).read()
            if target.exists() and target.read_bytes() != data:
                raise FileExistsError(f'Refusing to overwrite modified backend file: {target}')
            files[name.as_posix()] = data
    # Validate everything before writing any file.
    for name, data in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(data)
    report = {'commit': commit, 'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    out = root / '.validation/backend-export.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(f'Backend {commit}: {len(files)} files verified byte-for-byte in service/.')
    return report


if __name__ == '__main__':
    export()
