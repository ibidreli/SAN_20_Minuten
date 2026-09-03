"""
Builds the submission package in the folder structure the Projektbeschreibung
prescribes, and zips it for the Bsc-Data-Science download-link submission.

    Meilenstein/   ausgefuellter Meilenstein
    Praesentation/ aufgezeichnete Praesentation (max. 30 Minuten)
    Source/        Fetcher, Verarbeitungs-Skripte, Jupyter Notebooks
    Rohdaten/      Rohdaten-Ausgaben
    Graphen/       exportierte Graphen

Run from the repository root:

    python scripts/package_submission.py --dry-run   # nur auflisten
    python scripts/package_submission.py             # bauen und zippen
"""
import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from pathlib import Path

OUT_ROOT = Path('submission')
PACKAGE_NAME = 'SAN-Projekt_20min_Netzwerkanalyse'

# (source, destination inside the package). Directories are copied wholesale.
LAYOUT = [
    ('docs/SAN-Meilensteine.md', 'Meilenstein/SAN-Meilensteine.md'),
    ('src', 'Source/src'),
    ('scripts', 'Source/scripts'),
    ('data_extraction', 'Source/data_extraction'),
    ('out_plots', 'Source/out_plots'),
    ('README.md', 'Source/README.md'),
    ('requirements.txt', 'Source/requirements.txt'),
    ('data/20min_artikel_neu.csv', 'Rohdaten/20min_artikel_neu.csv'),
    ('data/20min_artikel_sortiert.csv', 'Rohdaten/20min_artikel_sortiert.csv'),
    ('data/20min_metadaten_keywords.csv', 'Rohdaten/20min_metadaten_keywords.csv'),
    ('data/20min_cleaned_post2020.parquet', 'Rohdaten/20min_cleaned_post2020.parquet'),
    ('data/manifest.json', 'Rohdaten/manifest.json'),
    ('data/data_dictionary.json', 'Rohdaten/data_dictionary.json'),
    ('data/ground_truth_validation.md', 'Rohdaten/ground_truth_validation.md'),
    ('data/ground_truth_validation.json', 'Rohdaten/ground_truth_validation.json'),
    ('graphen', 'Graphen'),
]

# Die aufgezeichnete Praesentation wird NICHT unter submission/ aufbewahrt.
# build() loescht das Paketverzeichnis bei jedem Lauf komplett; eine dort
# abgelegte Aufnahme waere beim naechsten Paketieren still verschwunden.
# Ablageort ausserhalb des Pakets, von hier wird sie hineinkopiert:
PRESENTATION_SOURCE_DIR = Path('praesentation')
PRESENTATION_SUFFIXES = {'.mp4', '.mov', '.m4v', '.mkv', '.webm', '.pdf', '.pptx'}

REQUIRED_DIRS = ['Meilenstein', 'Praesentation', 'Source', 'Rohdaten', 'Graphen']

EXCLUDE_NAMES = {'__pycache__', '.DS_Store', '.ipynb_checkpoints'}

PRESENTATION_PLACEHOLDER = """# Praesentation fehlt noch

Hier gehoert die aufgezeichnete Praesentation hin (max. 30 Minuten).

WICHTIG: Die Aufnahme NICHT direkt in dieses Verzeichnis legen. Es wird bei
jedem Lauf von scripts/package_submission.py neu erzeugt. Die Aufnahme gehoert
nach praesentation/ im Repository-Wurzelverzeichnis und wird von dort
automatisch ins Paket kopiert.

Vorgegebener Ablauf gemaess Projektbeschreibung:

1. Datenbeschaffung
2. Explorative Datenanalyse
3. Modellierung
4. Soziale Netzwerkanalyse
5. Ausblick
6. Lessons Learned

Siehe TODO.md im Repository.
"""


def _ignore(_dir, names):
    return [n for n in names if n in EXCLUDE_NAMES]


def human(n):
    for unit in ('B', 'KiB', 'MiB', 'GiB'):
        if n < 1024 or unit == 'GiB':
            return f'{n:.1f} {unit}'
        n /= 1024


def collect(dry_run):
    missing = []
    planned = []
    for src, dest in LAYOUT:
        s = Path(src)
        if not s.exists():
            missing.append(src)
            continue
        size = (sum(f.stat().st_size for f in s.rglob('*') if f.is_file())
                if s.is_dir() else s.stat().st_size)
        planned.append((s, dest, size))
    return planned, missing


def build(dry_run=False):
    planned, missing = collect(dry_run)

    print(f'Paket: {PACKAGE_NAME}')
    print(f'{"Quelle":<45} {"Ziel im Paket":<40} {"Groesse":>10}')
    print('-' * 97)
    for s, dest, size in planned:
        print(f'{str(s):<45} {dest:<40} {human(size):>10}')
    total = sum(size for _, _, size in planned)
    print('-' * 97)
    print(f'{"TOTAL":<86} {human(total):>10}')

    if missing:
        print('\nFEHLT (nicht ins Paket aufgenommen):')
        for m in missing:
            print(f'  - {m}')

    if dry_run:
        print('\n--dry-run: nichts geschrieben.')
        return 0

    pkg = OUT_ROOT / PACKAGE_NAME
    if pkg.exists():
        shutil.rmtree(pkg)
    for d in REQUIRED_DIRS:
        (pkg / d).mkdir(parents=True, exist_ok=True)

    for s, dest, _ in planned:
        target = pkg / dest
        target.parent.mkdir(parents=True, exist_ok=True)
        if s.is_dir():
            shutil.copytree(s, target, ignore=_ignore, dirs_exist_ok=True)
        else:
            shutil.copy2(s, target)

    # Aufzeichnung aus dem Quellordner uebernehmen, falls vorhanden
    recordings = []
    if PRESENTATION_SOURCE_DIR.is_dir():
        recordings = sorted(f for f in PRESENTATION_SOURCE_DIR.iterdir()
                            if f.is_file() and f.suffix.lower() in PRESENTATION_SUFFIXES)
        for f in recordings:
            shutil.copy2(f, pkg / 'Praesentation' / f.name)
            print(f'Praesentation uebernommen: {f} ({human(f.stat().st_size)})')
    if recordings:
        print(f'{len(recordings)} Datei(en) in Praesentation/.')
    else:
        (pkg / 'Praesentation' / 'PLATZHALTER.md').write_text(
            PRESENTATION_PLACEHOLDER, encoding='utf-8')
        print(f'Keine Aufzeichnung in {PRESENTATION_SOURCE_DIR}/ gefunden, '
              f'Platzhalter geschrieben.')

    # Verify the raw data survived the copy unchanged
    print('\nIntegritaetspruefung gegen data/manifest.json:')
    manifest = json.loads(Path('data/manifest.json').read_text())
    ok = True
    for name, entry in manifest.items():
        copied = pkg / 'Rohdaten' / Path(name).name
        if not copied.exists():
            print(f'  FEHLT    {copied}')
            ok = False
            continue
        h = hashlib.sha256()
        with open(copied, 'rb') as f:
            for block in iter(lambda: f.read(1 << 20), b''):
                h.update(block)
        if h.hexdigest() == entry['sha256']:
            print(f'  OK       {copied.name}')
        else:
            print(f'  MISMATCH {copied.name}')
            ok = False

    zip_path = OUT_ROOT / f'{PACKAGE_NAME}.zip'
    print(f'\nSchreibe {zip_path} ...')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(pkg.rglob('*')):
            if f.is_file():
                z.write(f, f.relative_to(OUT_ROOT))
    print(f'Fertig: {zip_path} ({human(zip_path.stat().st_size)})')

    print('\nNaechste Schritte (siehe TODO.md):')
    print('  1. Aufgezeichnete Praesentation nach praesentation/ legen (nicht ins Paket)')
    print('  2. docs/KI-Deklaration.md mit Prompts ergaenzen')
    print('  3. Neu paketieren und den Download-Link per MS Teams schicken')
    return 0 if ok else 1


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dry-run', action='store_true', help='nur auflisten, nichts schreiben')
    args = ap.parse_args()
    sys.exit(build(dry_run=args.dry_run))
