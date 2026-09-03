"""
Regenerates data/manifest.json.

Hashes both the raw source CSVs and the derived parquet, so the reproducibility
claim ("raw and clean data hashes match the manifest") can actually be checked.
Run from the repository root:

    python scripts/build_manifest.py           # write the manifest
    python scripts/build_manifest.py --check   # verify without writing
"""
import hashlib
import json
import sys
from pathlib import Path

MANIFEST_PATH = Path('data/manifest.json')
TRACKED_FILES = [
    'data/20min_artikel_neu.csv',
    'data/20min_artikel_sortiert.csv',
    'data/20min_metadaten_keywords.csv',
    'data/20min_cleaned_post2020.parquet',
]


def sha256_of(path, chunk_size=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk_size), b''):
            h.update(block)
    return h.hexdigest()


def count_lines(path, chunk_size=1 << 20):
    total = 0
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(chunk_size), b''):
            total += block.count(b'\n')
    return total


def describe(path):
    p = Path(path)
    size = p.stat().st_size
    entry = {
        'size_bytes': size,
        'size_mb': round(size / (1024 * 1024), 2),
        'sha256': sha256_of(p),
    }
    if p.suffix == '.csv':
        entry['line_count'] = count_lines(p)
    return entry


def main():
    check_only = '--check' in sys.argv
    missing = [f for f in TRACKED_FILES if not Path(f).exists()]
    if missing:
        print('Missing, not hashed: ' + ', '.join(missing))

    current = {f: describe(f) for f in TRACKED_FILES if Path(f).exists()}

    if check_only:
        if not MANIFEST_PATH.exists():
            print('No manifest to check against.')
            return 1
        stored = json.loads(MANIFEST_PATH.read_text())
        failed = False
        for name, entry in current.items():
            old = stored.get(name)
            if old is None:
                print(f'NEW      {name} (not in manifest)')
                failed = True
            elif old.get('sha256') != entry['sha256']:
                print(f'MISMATCH {name}')
                failed = True
            else:
                print(f'OK       {name}')
        return 1 if failed else 0

    MANIFEST_PATH.write_text(json.dumps(current, indent=2) + '\n')
    print(f'Wrote {MANIFEST_PATH} with {len(current)} entries')
    for name, entry in current.items():
        print(f'  {name}: {entry["size_mb"]} MB, sha256 {entry["sha256"][:16]}...')
    return 0


if __name__ == '__main__':
    sys.exit(main())
