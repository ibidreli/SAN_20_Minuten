# F01: Kandidatenschicht

Die Pipeline persistiert Titel, Lead, Ressort, Datum, Interaktionsmetriken und
Kandidaten in SQLite. Der Artikelkörper bleibt im Arbeitsspeicher.
Der vollständige technische Nachweis steht im
[Fixture- und Pilotbericht](../docs/features/F01-pilotbericht.md).

## Installation

Getestet mit Python 3.11.9. Im Repository:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --dry-run -r requirements-dev.txt
python -m pip install -r requirements-dev.txt
python -m pip install --dry-run https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-3.8.0/de_core_news_lg-3.8.0-py3-none-any.whl
python -m pip install https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-3.8.0/de_core_news_lg-3.8.0-py3-none-any.whl
pytest tests/
```

Für reine Laufzeitabhängigkeiten genügt `requirements-f01.txt` plus Modell.
Das Modell wird nicht automatisch heruntergeladen. Parser, NER und Lemmatizer
müssen vorhanden sein; die Kandidaten verwenden ausschliesslich `span.text`.

## Vollständiger Offline-Lauf

Ein neues Verzeichnis verhindert die Vermischung mit Produktionsdaten:

```sh
run_dir=$(mktemp -d /private/tmp/f01-fixtures.XXXXXX)
python -m data_extraction.fetch_articles --source fixtures --db "$run_dir/articles.sqlite" --fixture-count 650 --dry-run
python -m data_extraction.fetch_articles --source fixtures --db "$run_dir/articles.sqlite" --fixture-count 650
```

`Ctrl+C` committet den begonnenen Batch und beendet den Prozess mit Exitcode 130.
Zum Fortsetzen denselben Befehl erneut aufrufen. `FixtureSource` bildet die 13
lokalen Seiten deterministisch auf eindeutige `fixture://`-URLs ab. Bei 650
Einträgen sind 600 erfolgreiche Seiten und 50 HTTP-410-Fehlerfälle enthalten.
Es gibt keinen HTTP-Fallback.

Automatischer Nachweis mit zwei Datenbanken, Netzwerksperre und echtem Signal:

```sh
check_dir=$(mktemp -d /private/tmp/f01-check.XXXXXX)
python -m scripts.verify_f01 --output-dir "$check_dir" --dry-run
python -m scripts.verify_f01 --output-dir "$check_dir"
```

Das Skript erzeugt `uninterrupted.sqlite`, `resumed.sqlite` und `evidence.json`.
Es vergleicht alle Zeilen, ausser den notwendigerweise verschiedenen
Abrufzeitpunkten, und sucht per SQL nach gespeicherten Artikelkörpern.
Vorhandene Nachweisdateien werden nicht überschrieben.

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

## Produktionsschnittstelle, noch nicht ausgeführt

`--source http` wählt den dünnen HTTP-Adapter. Eine neue Datenbank benötigt
`--input` mit einer CSV mit den Spalten `url` und `datum`. Ohne `--input` setzt
ein Neustart eine vorhandene HTTP-Datenbank fort. Die CSV wird gestreamt;
Zeitraum und Pilotstichprobe müssen bereits in der Eingabedatei ausgewählt sein.
Fixture- und HTTP-Datenbanken dürfen nicht vermischt werden.

Der Adapter setzt User-Agent und Timeout, wiederholt Verbindungsfehler sowie
429/503 höchstens dreimal mit exponentiellem Backoff und verfolgt keine
Weiterleitungen. HTTP ist ausschliesslich mit gemockten Antworten getestet.
Die Freigabe des produktiven Piloten beziehungsweise Vollcrawls erfolgt durch
das Team. Die hier dokumentierten Ausführungsbeispiele bleiben offline.

Die alte Datei `handle_data.py` delegiert an denselben CLI und verlangt ebenfalls
eine explizite Quelle. `get_data.py` ist weiterhin der separate Sitemap-Crawler;
sein Import startet keine Arbeit.
