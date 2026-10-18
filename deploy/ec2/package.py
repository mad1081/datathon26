"""Package uncommitted deployment files for upload; excludes .env, data, logs, weights."""
from __future__ import annotations

import argparse
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'results/forte-deploy.tar.gz')
    args = parser.parse_args()
    files = [ROOT / 'docker-compose.yml', ROOT / '.env.vlm.example', ROOT / '.gitignore']
    files += sorted(p for p in (ROOT / 'deploy').rglob('*')
                    if p.is_file() and (p.suffix in {'.py', '.json', '.sh', '.md'} or p.name == 'Dockerfile'))
    files = [p for p in files if '__pycache__' not in p.parts]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(args.output, mode='x:gz') as archive:
        for p in files:
            archive.add(p, arcname=p.relative_to(ROOT).as_posix(), recursive=False)
    print(f'Created {args.output}: {len(files)} files. No .env, dataset, or weights.')


if __name__ == '__main__':
    main()
