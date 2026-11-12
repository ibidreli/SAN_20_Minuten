"""Baut, fuehrt aus und synchronisiert src/02_analyse.ipynb.

Die Interpretationszellen enthalten keine handgeschriebenen Kennzahlen, sondern
Platzhalter der Form {{schluessel}}. Die Werte entstehen erst beim Ausfuehren:
jede Zahl laeuft im Notebook durch fact(), landet in data/notebook_facts.json
und wird erst danach in den Fliesstext eingesetzt.

Dadurch kann ein erneuter Lauf keine veralteten Zahlen im Text zuruecklassen.
Genau diese Fehlerklasse (Prosa sagt A, die Zelle darueber druckt B) trat in
drei aufeinanderfolgenden Review-Runden auf.

Aufruf:
    python scripts/run_notebook.py              # bauen, ausfuehren, ersetzen
    python scripts/run_notebook.py --no-build   # vorhandenes Notebook ausfuehren
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

NB = Path('src/02_analyse.ipynb')
FACTS = Path('data/notebook_facts.json')
BUILDER = Path('scripts/build_analysis_notebook.py')
PLACEHOLDER = re.compile(r'\{\{([a-z0-9_]+)\}\}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--no-build', action='store_true',
                    help='vorhandenes Notebook ausfuehren statt neu zu bauen')
    args = ap.parse_args()

    if not args.no_build:
        print(f'Baue {NB} neu aus {BUILDER} ...')
        subprocess.run([sys.executable, str(BUILDER)], check=True)

    nb = nbformat.read(NB, as_version=4)

    n_ph = sum(len(PLACEHOLDER.findall(c.source))
               for c in nb.cells if c.cell_type == 'markdown')
    if n_ph == 0:
        sys.exit(
            f'ABBRUCH: {NB} enthaelt keine Platzhalter mehr. Das Notebook wurde '
            'bereits ersetzt; eine erneute Ausfuehrung wuerde die alten Zahlen '
            'im Fliesstext stehen lassen. Ohne --no-build erneut aufrufen.'
        )
    print(f'{n_ph} Platzhalter im Fliesstext gefunden.')

    if FACTS.exists():
        FACTS.unlink()

    print(f'Fuehre {NB} aus ...')
    NotebookClient(nb, timeout=1800, kernel_name='python3').execute()

    if not FACTS.exists():
        sys.exit(f'ABBRUCH: {FACTS} wurde nicht geschrieben. Die Registry-Zelle '
                 'ist nicht gelaufen.')
    facts = json.loads(FACTS.read_text(encoding='utf-8'))

    missing = set()
    n_sub = 0

    def substitute(match):
        nonlocal n_sub
        key = match.group(1)
        if key not in facts:
            missing.add(key)
            return match.group(0)
        n_sub += 1
        return facts[key]

    for cell in nb.cells:
        if cell.cell_type == 'markdown':
            cell.source = PLACEHOLDER.sub(substitute, cell.source)

    if missing:
        sys.exit('ABBRUCH: keine berechneten Werte fuer: ' + ', '.join(sorted(missing)))

    with NB.open('w', encoding='utf-8') as f:
        nbformat.write(nb, f)

    print(f'{n_sub} Platzhalter aus {len(facts)} Kennzahlen ersetzt.')
    print(f'{NB} mit Ausgaben gespeichert.')


if __name__ == '__main__':
    main()
