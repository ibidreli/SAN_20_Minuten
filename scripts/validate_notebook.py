"""Qualitaetsgate fuer src/02_analyse.ipynb.

Prueft nach jedem Lauf, dass das ausgefuehrte Notebook tatsaechlich das
enthaelt, was der Bericht behauptet. Der wichtigste Test ist der vierte: jede
Kennzahl im Fliesstext muss auch in einer Zellenausgabe stehen. Genau diese
Bedingung war in drei Review-Runden verletzt, weil Zahlen von Hand in die
Interpretation geschrieben und bei einem erneuten Lauf nicht nachgezogen
wurden.

Aufruf: python scripts/validate_notebook.py
Rueckgabewert 0 = alle Pruefungen bestanden.
"""
import json
import re
import sys
from pathlib import Path

import nbformat

NB = Path('src/02_analyse.ipynb')
FACTS = Path('data/notebook_facts.json')
PLOT_DIR = Path('out_plots')

PLACEHOLDER = re.compile(r'\{\{[a-z0-9_]+\}\}')
CONTROL = re.compile(r'[\t\x00\x07\x08\x0b\x0c\r]')
NUMBER = re.compile(r"\d[\d'’]*(?:\.\d+)?%?")

# Zahlen, die bewusst nicht aus einer Zelle dieses Notebooks stammen.
# Jeder Eintrag braucht eine Begruendung; ohne Eintrag schlaegt die Pruefung
# fehl, damit eine handgeschriebene Kennzahl nicht unbemerkt hereinrutscht.
ALLOWED_NUMBERS = {
    # Jahreszahlen aus Literaturangaben
    '1992': 'Burt (1992)',
    '2001': 'Newman (2001)',
    '2002': 'Newman (2002)',
    '2004': 'Burt (2004)',
    '2007': 'Liben-Nowell & Kleinberg (2007)',
    # Kennzahlen aus der Datenaufbereitung (src/01_cleaning.qmd, clean_dataset.py)
    '41.4%': 'Anteil fehlender Kommentarwerte, aus 01_cleaning.qmd',
    '166': 'entfernte institutionelle Knoten, aus clean_dataset.py',
    '947': 'Autor:innen vor der Agenturfilterung, aus clean_dataset.py',
    '214': 'Artikel von Agence France-Presse vor der Filterung',
    # Kennzahlen aus der Quelldaten-Validierung
    '98.3%': 'Datumsuebereinstimmung, aus data/ground_truth_validation.md',
    '60': 'Stichprobengroesse der Live-Validierung',
    # Methodengeschichte: Werte frueherer, korrigierter Staende
    '2.5': 'scheinbarer Broker-Vorsprung vor der Baseline-Korrektur',
    '94.7%': 'Kantenanteil unter p=0.01 in der alten Maximalgewicht-Normierung',
    '0.148': 'QAP-Korrelation vor der Korrektur auf volle Dyaden',
    '50': 'Groessenordnung der alten Fehlnormierung (Faktor)',
    # Konventionen und Konstanten
    '1.96': 'kritischer z-Wert, 95%',
    '0.05': 'Signifikanzniveau',
    '0.001': 'Signifikanzniveau',
    '300': 'DPI der Abbildungen',
    '6.2': 'Verweis auf Abschnitt 6.2',
    '3.3': 'Verweis auf Abschnitt 3.3',
    '17': 'Anzahl Unit-Tests in src/network_models.py',
}


def cell_outputs(cell):
    parts = []
    for out in cell.get('outputs', []):
        if out.output_type == 'stream':
            parts.append(out.text)
        elif out.output_type in ('execute_result', 'display_data'):
            parts.append(str(out.get('data', {}).get('text/plain', '')))
        elif out.output_type == 'error':
            parts.append('\n'.join(out.get('traceback', [])))
    return '\n'.join(parts)


def main():
    failures = []
    warnings = []

    nb = nbformat.read(NB, as_version=4)
    md_cells = [c for c in nb.cells if c.cell_type == 'markdown']
    code_cells = [c for c in nb.cells if c.cell_type == 'code']

    # 1 -- Ausfuehrungsfehler
    n_err = sum(1 for c in code_cells for o in c.get('outputs', [])
                if o.output_type == 'error')
    if n_err:
        failures.append(f'{n_err} Zelle(n) mit Ausfuehrungsfehler')
    print(f'[1] Ausfuehrungsfehler          : {n_err}')

    # 2 -- offene Platzhalter
    open_ph = [p for c in md_cells for p in PLACEHOLDER.findall(c.source)]
    if open_ph:
        failures.append(f'nicht ersetzte Platzhalter: {sorted(set(open_ph))}')
    print(f'[2] offene Platzhalter          : {len(open_ph)}')

    # 3 -- Steuerzeichen im Fliesstext (verunglueckte Backslash-Escapes)
    ctrl = [c.source[max(0, m.start() - 40):m.start() + 20]
            for c in md_cells for m in CONTROL.finditer(c.source)]
    if ctrl:
        failures.append(f'Steuerzeichen im Markdown: {ctrl}')
    print(f'[3] Steuerzeichen im Markdown   : {len(ctrl)}')

    # 4 -- jede Kennzahl im Text steht auch in einer Ausgabe oder in der
    #      Registry der berechneten Werte
    facts = json.loads(FACTS.read_text(encoding='utf-8')) if FACTS.exists() else {}
    haystack = '\n'.join(cell_outputs(c) for c in code_cells)
    haystack += '\n' + '\n'.join(facts.values())
    haystack_norm = haystack.replace(',', '').replace("'", '')
    unbacked = {}
    for cell in md_cells:
        for tok in NUMBER.findall(cell.source):
            raw = tok.rstrip('%').replace("'", '').replace('’', '')
            if raw in haystack_norm or tok in haystack:
                continue
            if tok in ALLOWED_NUMBERS or raw in ALLOWED_NUMBERS:
                continue
            unbacked.setdefault(tok, cell.source[:60].replace('\n', ' '))
    if unbacked:
        failures.append('Zahlen ohne Deckung in einer Zellenausgabe: '
                        + ', '.join(f'{k} (in "{v}...")' for k, v in unbacked.items()))
    print(f'[4] ungedeckte Zahlen im Text   : {len(unbacked)}')

    # 5 -- Abbildungen: erzeugt, vorhanden, referenziert
    on_disk = sorted(p.name for p in PLOT_DIR.glob('*.png'))
    # Die Nummerierung steckt im Dateinamen (01_... bis 14_...) und ist damit
    # die verbindliche Liste, unabhaengig davon, ob eine Abbildung direkt per
    # savefig oder ueber draw_network geschrieben wurde.
    on_disk_numbers = sorted({int(n.split('_')[0]) for n in on_disk
                              if n.split('_')[0].isdigit()})
    md_all = '\n'.join(c.source for c in md_cells)
    ref_pat = re.compile(r'Abbildung(?:en)?\s+((?:\d+\s*(?:und|bis|,)\s*)*\d+)')
    fig_numbers = set()
    for m in ref_pat.finditer(md_all):
        fig_numbers.update(int(x) for x in re.findall(r'\d+', m.group(1)))
    fig_numbers = sorted(fig_numbers)
    gaps = [n for n in range(1, (max(on_disk_numbers) + 1) if on_disk_numbers else 1)
            if n not in on_disk_numbers]
    unreferenced = [n for n in on_disk_numbers if n not in fig_numbers]
    if gaps:
        failures.append(f'Luecken in der Abbildungsnummerierung: {gaps}')
    if unreferenced:
        failures.append(f'Abbildungen nicht im Text referenziert: {unreferenced}')
    inline = sum(1 for c in code_cells for o in c.get('outputs', [])
                 if o.output_type == 'display_data' and 'image/png' in o.get('data', {}))
    if inline < len(on_disk_numbers):
        failures.append(f'nur {inline} von {len(on_disk_numbers)} Abbildungen inline sichtbar')
    print(f'[5] Abbildungen                 : {len(on_disk_numbers)} nummeriert, '
          f'{inline} inline, Luecken: {gaps or "keine"}, '
          f'alle referenziert: {not unreferenced}')

    # 6 -- Interpretationsdeckung: auf jede Abbildungszelle folgt Interpretation
    uncovered = []
    for i, cell in enumerate(nb.cells):
        if cell.cell_type != 'code' or 'savefig' not in cell.source:
            continue
        nxt = [c for c in nb.cells[i + 1:i + 3] if c.cell_type == 'markdown']
        if not any('Interpretation' in c.source for c in nxt):
            uncovered.append(i)
    if uncovered:
        failures.append(f'Abbildungszellen ohne folgende Interpretation: {uncovered}')
    n_interp = sum(1 for c in md_cells if c.source.lstrip().startswith('**Interpretation'))
    print(f'[6] Interpretationszellen       : {n_interp}, ohne Deckung: {len(uncovered)}')

    # 7 -- Registry
    if not FACTS.exists():
        failures.append(f'{FACTS} fehlt')
        print('[7] Zahlen-Registry             : FEHLT')
    else:
        unused = sorted(k for k in facts
                        if not re.search(re.escape(facts[k]), md_all))
        if unused:
            warnings.append(f'registriert, aber nicht im Text verwendet: {unused}')
        print(f'[7] Zahlen-Registry             : {len(facts)} Kennzahlen')

    print()
    for w in warnings:
        print(f'HINWEIS: {w}')
    if failures:
        print()
        for f in failures:
            print(f'FEHLER: {f}')
        return 1
    print('Alle Pruefungen bestanden.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
