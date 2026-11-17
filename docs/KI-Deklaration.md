# KI-Deklaration

**Projekt:** Soziale Netzwerkanalyse 20 Minuten · **Team:** Elias, Luca · **Modul:** SAN, FHNW

Gemäss Projektbeschreibung (S. 4) deklarieren wir hier jede Verwendung von KI-Werkzeugen mit den verwendeten Prompts.
Die Prompts stehen vollständig und chronologisch in den Dateien `docs/KI-Prompts*.md`. Diese erzeugt `python scripts/ki_prompts.py`
direkt aus den gespeicherten Sitzungen.

> **Pflege:** Nach jeder KI-Sitzung `python scripts/ki_prompts.py` ausführen (Luca mit `--autor Luca --ausgabe docs/KI-Prompts-Luca.md`)
> und die Tabelle unten ergänzen. Andere Werkzeuge (z. B. ChatGPT im Browser) von Hand mit Datum und Prompt in eine eigene Datei eintragen.

## Verwendete Werkzeuge

| Werkzeug | Person | Zeitraum | Prompts |
|---|---|---|---|
| Claude Code (Anthropic), Modell Claude Opus, in VS Code | Elias | ab 12.11.2026 | [KI-Prompts.md](KI-Prompts.md) |
| *(ergänzen)* | Luca | | `KI-Prompts-Luca.md` |

## Wofür KI verwendet wurde

| Bereich | Was die KI gemacht hat | Dateien |
|---|---|---|
| Planung | Aufgabenstellung und Skript ausgewertet, Roadmap entworfen | `docs/ROADMAP.md` |
| Datenbeschaffung | Parser an das aktuelle Layout von 20min.ch angepasst: Reaktionen aus `__NEXT_DATA__`, typisierte Textblöcke, Liveticker, Autoren und Quellenkürzel, Textlänge, Aktualisierung; Testläufe und Fehleranalyse | `data_extraction/page_parser.py`, `db.py`, `fetch_articles.py` |
| Keywords | Methode vorgeschlagen (NER + Nominalphrasen, Grundform, Alias-Auflösung, Stoppliste, TF-IDF mit Titel-/Lead-Bonus) und umgesetzt | `data_extraction/candidates.py`, `keywords.py` |
| Personen | Zusammenführung von Namen, Kürzeln und IDs zu Personen | `data_extraction/autoren.py` |
| Datenqualität | Prüfung aller Tabellen, Plausibilitätschecks gegen die Live-Seite, Befund „Reaktionen erst ab Juni 2020“ | `src/01_eda.ipynb` |
| Analyse-Code | Lade-, Netzwerk- und Analysefunktionen (Projektion, Nullmodell, Zentralitäten, Communities, Assortativität mit Permutationstest, Link Prediction, Export) und Notebook-Gerüste | `src/daten.py`, `src/netzwerk.py`, `src/0*.ipynb` |
| Dokumentation | README, Entwurf Meilenstein, diese Deklaration (Gerüst) | `data_extraction/README.md`, `docs/Meilenstein.md` |

## Eigenleistung und Kontrolle

Die Grundversion des Scrapers wurde von Hand geplant und implementiert. Da es sehr viele Sonderfälle gibt und die Daten inkosistent sind, haben wir die KI eingesetzt, um die Extraktion zu verbessern und die Qualität der Daten zu prüfen. Die KI hat Vorschläge gemacht, die wir geprüft und teilweise übernommen haben. Alle Änderungen wurden von uns kontrolliert und getestet. Zudem

## Grenzen

- Die Interpretation der Analysen im Bezug auf den Anwendungsfall stammt vom Team.
- KI-generierter Code wurde an Testdaten ausgeführt und geprüft. Die Prüfungen sind in den Notebooks und der README dokumentiert.
