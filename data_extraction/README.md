# F01: Kandidatenschicht

Die Pipeline persistiert Titel, Lead, Ressort, Datum, Interaktionsmetriken und
Kandidaten in SQLite. Der Artikelkörper bleibt ausschliesslich im
Arbeitsspeicher und wird nach der Extraktion verworfen.

## Installation

Getestet mit Python 3.11.9. Im Repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-f01.txt
python -m pip install https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-3.8.0/de_core_news_lg-3.8.0-py3-none-any.whl
```

Das Modell wird nicht automatisch heruntergeladen. Parser, NER und Lemmatizer
müssen vorhanden sein; die Kandidaten verwenden ausschliesslich `span.text`.

## Bedienung

Eine neue Datenbank benötigt `--input` mit einer CSV mit den Spalten `url` und
`datum`. Die CSV wird gestreamt; Zeitraum und Stichprobe müssen bereits in der
Eingabedatei ausgewählt sein.

```sh
python -m data_extraction.fetch_articles --db data/articles.sqlite --input data/20min_artikel_sortiert.csv --dry-run
python -m data_extraction.fetch_articles --db data/articles.sqlite --input data/20min_artikel_sortiert.csv
```

Ohne `--input` setzt ein Neustart eine vorhandene Datenbank fort. `--dry-run`
zeigt den Plan, ohne das Modell zu laden oder zu schreiben.

`Ctrl+C` committet den begonnenen Batch und beendet den Prozess mit Exitcode 130.
Zum Fortsetzen denselben Befehl erneut aufrufen.

## Wiederaufnahme und Fehler

`pending` wird beim Neustart in begrenzten Batches gelesen. `done` und `skipped`
bleiben unberührt. `--retry-failed` setzt alle Fehler zurück; wiederholbares
`--retry-url URL` setzt nur die genannten fehlgeschlagenen URLs zurück.
Diese beiden Schalter sind Alternativen. Der Versuchsstand bleibt erhalten.

HTTP 404 und 410 werden `skipped`, andere fehlgeschlagene Abrufe und unbekannte
Layouts werden `failed`. `attempts` zählt Verarbeitungsläufe pro URL, nicht die
internen HTTP-Wiederholungen. Ein unbekannter Programm- oder Modellfehler rollt
den ganzen Batch zurück und beendet den Prozess, damit er nach Korrektur erneut
bearbeitbar ist.

SQLite nutzt WAL und Fremdschlüssel. Pro Datenbank ist ein schreibender Crawler
vorgesehen; gleichzeitig lesende Prozesse sind erlaubt. Beim Fortsetzen müssen
Modell und Parserregeln unverändert bleiben. F01 speichert keine Modellversion
in der Datenbank; die gewählte Version gehört in das Laufprotokoll.

## Abrufschicht

`HttpSource` ist die einzige Stelle mit Netzwerkzugriff. Sie setzt User-Agent
und Timeout, wiederholt Verbindungsfehler sowie 429 und 503 höchstens dreimal
mit exponentiellem Backoff und verfolgt keine Weiterleitungen.

Die Freigabe des Vollcrawls erfolgt durch das Team, nicht durch das Skript.

## Module

| Datei | Aufgabe |
|---|---|
| `sources.py` | HTTP-Abruf, Timeout, Backoff, Statuscode |
| `page_parser.py` | HTML zu Titel, Lead, Körper, Ressort, Datum, Metriken |
| `candidates.py` | spaCy NER und Nominalphrasen, ohne Normalisierung |
| `db.py` | SQLite-Schema, Transaktionen, Wiederaufnahme |
| `fetch_articles.py` | Ablauf, Batching, Signalbehandlung, CLI |
| `get_data.py` | separater Sitemap-Crawler, erzeugt die URL-Liste |

`handle_data.py` delegiert an denselben CLI. Kein Modul startet beim Import
Arbeit.
