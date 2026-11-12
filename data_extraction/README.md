# F01: Kandidatenschicht

Die Pipeline persistiert Titel, Lead, Ressort, Datum, Interaktionsmetriken
(Reaktionen, Shares, Kommentare), Wortanzahl, Autoren und Kandidaten in SQLite.
Der Artikelkörper bleibt ausschliesslich im Arbeitsspeicher und wird nach der
Extraktion verworfen; die Wortanzahl wird vorher aus ihm gezählt.

Die Metriken und Autoren stammen aus dem eingebetteten Next.js-Zustand
(`__NEXT_DATA__`), weil die Seite die Buttons erst im Browser rendert. Die
Autoren landen roh in `article_authors` (Reihenfolge, Name, Kürzel, ID);
ältere Artikel tragen oft nur ein Kürzel, Agenturen wie dpa stehen als
gewöhnliche Einträge in der Liste.

## Installation

Getestet mit Python 3.11.9. Die aktuelle Extraktion benötigt Beautiful Soup,
Requests, spaCy und das deutsche Sprachmodell `de_core_news_lg`. Alle vier
Abhängigkeiten stehen in `requirements.txt`. Installation in PowerShell im
Repository:

```powershell
# Nur erstellen, wenn noch keine virtuelle Umgebung existiert:
python -m venv .venv

.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
```

Das Modell wird bei der Installation der Requirements heruntergeladen, nicht
beim Start des Crawlers. Parser, NER und Lemmatizer müssen vorhanden sein;
die Kandidaten verwenden ausschliesslich `span.text`.
Die folgenden Bedienbeispiele setzen eine aktivierte virtuelle Umgebung voraus.

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
