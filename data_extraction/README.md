# Datenextraktion 20 Minuten

Die Pipeline hat vier Schritte:

1. `get_data.py` sammelt die Artikel-URLs aus dem Tagesarchiv
   (`20min.ch/sitemap/JJJJ/MM/TT`) in `data/20min_artikel_neu.csv` und
   sortiert sie nach `data/20min_artikel_sortiert.csv`.
2. `fetch_articles.py` ruft die Artikel ab und speichert pro Artikel
   Metadaten, Autoren und alle Keyword-Kandidaten in SQLite.
3. `keywords.py` wählt aus den Kandidaten die besten Keywords pro Artikel
   und schreibt die Tabelle `keywords`.
4. `autoren.py` führt Autorennamen, Kürzel und IDs zu Personen zusammen und
   schreibt die Tabellen `personen` und `article_persons`.

Die Schritte 3 und 4 sind beliebig oft wiederholbar, ohne neu zu crawlen.
Die Analyse liegt in `src/` (siehe unten).

Der Artikeltext bleibt ausschliesslich im Arbeitsspeicher und wird nach der
Extraktion verworfen. Alles, was später aus ihm gebraucht wird (Wortanzahl,
Grundformen, Quellenkürzel), wird deshalb vorher berechnet.

## Gespeicherte Daten

**`articles`**, eine Zeile pro URL:

| Spalte | Inhalt |
|---|---|
| `titel` | sichtbare Überschrift (`h1`), nicht der Social-Media-Titel |
| `lead` | Lead unter der Überschrift |
| `ressort`, `ressort_pfad` | tiefste Kategorie bzw. ganzer Pfad, z. B. `Ausland > Donald Trump`; `unbekannt`, wenn 20min keine Kategorie vergibt |
| `datum`, `aktualisiert` | Publikation und letzte Änderung (ISO, UTC) |
| `likes`, `shares`, `kommentare`, `views` | Reaktionen, Shares, Kommentare, Aufrufe zum Zeitpunkt des Abrufs (`fetched_at`); `kommentare` ist leer, wenn Kommentare gesperrt sind |
| `wortanzahl` | Wörter im Fliesstext ohne Titel, Lead, Infobox, Umfragen, Bildtexte und Autorenbiografie; 0 bei Videos und Bildstrecken ohne Text |
| `format` | `artikel` oder `ticker` (Liveticker: alle Einträge der ersten Seite zusammengefasst) |
| `quelle_kuerzel` | Quellenzeile am Textende wie gedruckt, z. B. `chi/sep/sda`; zerlegt in `article_kuerzel` |

**`article_authors`**: Autoren aus dem Redaktionssystem in Seitenreihenfolge
mit Name, Kürzel, 20min-ID und Art. Kombinationen, die das CMS als einen
Autor führt (`AFP/sys`, `chi/sep`, `Marius Egger/rub`), werden zerlegt.

| `art` | Bedeutung | Beispiel |
|---|---|---|
| `person` | ausgeschriebener Name, meist mit ID | Jean-Claude Gerber, 40986771 |
| `kuerzel` | nur Redaktionskürzel bekannt, keine ID | jcg |
| `agentur` | Nachrichtenagentur oder Partnerdienst | SDA, Deutsche Presse-Agentur, spot on news |
| `20min` | Platzhalter der Redaktion | 20 Minuten Newsdesk |
| `sonstige` | nicht zuordenbar | Ortsangaben, Einzelfälle |

**`article_kuerzel`**: die Quellenzeile am Textende, zerlegt in einzelne
Einträge in gedruckter Reihenfolge. `(chi/sep/sda)` ergibt drei Zeilen:
`chi` und `sep` mit `art = redaktion` (Personenkürzel), `sda` mit
`art = agentur`. Weitere Arten sind `20min` (Quelle "20 Minuten") und `name`
(ausgeschriebener Name). Die Agenturliste steht in `page_parser.AGENCIES`;
jedes andere Kleinbuchstaben-Kürzel gilt als Person. Bildnachweise wie
"(Quelle: YouTube)" werden nicht erfasst.

**`candidates`**: alle Keyword-Kandidaten pro Artikel (im Test etwa 70),
nicht nur die späteren Keywords.

| Spalte | Inhalt |
|---|---|
| `phrase` | Originaltext, z. B. `die geplanten Parkhäuser` |
| `label` | `PER`, `ORG`, `LOC`, `MISC` (spaCy-NER) oder `NOUN_CHUNK` |
| `lemma` | Grundform ohne Artikel und Anführungszeichen, z. B. `geplant Parkhaus`; Namen nur ohne Flexionsendung (`Bidens` -> `Biden`) |
| `kopf` | Kopfnomen einer Nominalphrase, z. B. `Parkhaus` |
| `count`, `in_titel`, `in_lead` | Häufigkeit im Artikel, Vorkommen in Titel oder Lead |

Pronomen und Phrasen ohne grossgeschriebenes Nomen werden nicht gespeichert.

**`keywords`**: bis zu 8 Keywords pro Artikel plus die Stufen des
Ressort-Pfads (`typ = RESSORT`). Gebildet aus Namen (Grundform) und
Kopfnomen, Nachnamen auf den vollen Namen im Artikel abgebildet, Stoppliste
für Zeitangaben, Allerweltswörter und Boilerplate, bewertet mit TF-IDF und
Bonus für Titel, Lead und Namen. Ein Keyword muss in mindestens zwei Artikeln
vorkommen (`--min-df`). `typ` (`PER`, `ORG`, `LOC`, `MISC`, `THEMA`) stammt
aus der spaCy-Erkennung und ist in etwa 10–15 % der Fälle falsch.

**`personen`** und **`article_persons`** (aus `autoren.py`): eine Person pro
Mensch statt pro Schreibweise. Namen mit ID werden über die ID vereinigt,
abgekürzte Namen (`B. Zanni`) über Initiale und Nachname, Kürzel (`jcg`) über
alle Artikel, in denen Name und Kürzel gemeinsam stehen. Mehrdeutige Kürzel
entscheidet die zeitlich nächste Person (höchstens ein Jahr Abstand).
Unauflösbare Kürzel bleiben als `kürzel:xyz` eine eigene Person. `rolle` ist
`autor` (Byline) oder `quelle` (Kürzel in der Quellenzeile, z. B. `dpa/roy`),
`methode` sagt, wie die Person bestimmt wurde (`id`, `name`, `initiale`,
`kuerzel`, `kuerzel_zeit`, `mehrdeutig`, `ungeloest`). Agenturen, "20 Minuten"
und Ortsangaben ("aus Davos") sind keine Personen.

Metriken, Autoren und Ressort-Pfad stammen aus dem eingebetteten
Next.js-Zustand (`__NEXT_DATA__`) bzw. dem JSON-LD-Breadcrumb, weil die Seite
die Buttons erst im Browser rendert.

Den Fliesstext erkennt der Parser über das `type`-Attribut, mit dem das CMS
jeden Inhaltsblock markiert: `textBlockArray` (Absätze) und
`interviewSegment` gelten als Text; `infobox`, `poll`, `ad`, `image`,
`embed`, `quote` und Ähnliches nicht. Die Quellenzeile steht teils als eigener
Block `agencies`. Fehlen diese Attribute (ältere Layouts, manche
Ticker-Einträge), wählt eine Rückfallebene die Absatzklasse mit der grössten
Textmenge. In Artikel eingebettete Artikel-Karten werden ignoriert. Nur
Seiten ohne `<article>` (Themen- und Sonderseiten) landen als `failed`.

## Eigenschaften der Quelle

Diese Punkte sind keine Fehler der Extraktion, sondern so liefert 20min die
Daten. Sie bestimmen, welche Aussagen die Analyse machen kann.

- **Interaktionen** gibt es erst ab Juni 2020 (Reaktionssystem des neuen CMS).
  Vorher liefert die Seite 0 Likes und Shares und keine Kommentare; das ist
  nicht gemessen, nicht "keine Reaktion". `src/daten.py` setzt diese Werte
  deshalb auf fehlend (`REAKTIONEN_AB`). Fehlende `kommentare` heissen auch
  später: Kommentarfunktion aus (die Seite meldet dann 0). Neue Artikel
  sammeln in den ersten Tagen noch Reaktionen; für Vergleiche nur Artikel
  verwenden, die beim Abruf mindestens eine Woche alt waren.
- **Autoren** hängen vom Redaktionssystem ab: 2003–2009 oft der Platzhalter
  "20 Minuten Newsdesk", etwa 2008–2020 nur Kürzel ohne ID, 2003–2018 häufig
  eine Quellenzeile am Textende.
- **Ressorts**: Die Einteilung hat sich geändert ("Regionen", "Lifestyle" und
  "Community" erst ab etwa 2017). Für Zeitvergleiche die erste Stufe von
  `ressort_pfad` verwenden.
- **`views`** ist nicht als Seitenaufrufe interpretierbar: Im Test lag der
  Median bei 25, bei 78 % der Artikel unter den Likes. Das CMS liefert das
  Feld als `community.views`; seine Bedeutung ist unklar. Nicht verwenden,
  ohne es vorher zu klären.
- **Liveticker** (`format = ticker`) sammeln Reaktionen über viele Einträge
  (im Test bis 265'000 Likes) und verzerren Mittelwerte; getrennt auswerten.
- **Zeitangaben** sind UTC und für Auswertungen nach Uhrzeit nach
  `Europe/Zurich` umzurechnen; ältere Artikel sind nur minutengenau.
- Die alte Datei `data/20min_metadaten_keywords_clean.csv` enthält bei etwa
  10 % der Artikel zehnfach zu hohe Likes, Shares und Kommentare.

## Installation

Getestet mit Python 3.11.9. Die Extraktion benötigt Beautiful Soup, Requests,
spaCy und das deutsche Sprachmodell `de_core_news_lg`. Alle vier
Abhängigkeiten stehen in `requirements.txt`. Installation in PowerShell im
Repository:

```powershell
# Nur erstellen, wenn noch keine virtuelle Umgebung existiert:
python -m venv .venv

.\.venv\Scripts\python.exe -m pip install --only-binary=:all: -r requirements.txt
```

Das Modell wird bei der Installation der Requirements heruntergeladen, nicht
beim Start des Crawlers. Parser, NER und Lemmatizer müssen vorhanden sein.
Die folgenden Bedienbeispiele setzen eine aktivierte virtuelle Umgebung voraus.

## Bedienung

URL-Liste ab dem letzten gespeicherten Tag ergänzen (setzt selbständig fort,
ohne Dubletten):

```sh
python -m data_extraction.get_data
```

Artikel abrufen. Eine neue Datenbank benötigt `--input` mit einer CSV mit den
Spalten `url` und `datum`. Die CSV wird gestreamt; Zeitraum und Stichprobe
müssen bereits in der Eingabedatei ausgewählt sein.

```sh
python -m data_extraction.fetch_articles --db data/articles.sqlite --input data/20min_artikel_sortiert.csv --dry-run
python -m data_extraction.fetch_articles --db data/articles.sqlite --input data/20min_artikel_sortiert.csv
```

Keywords bilden (schreibt die Tabelle `keywords` neu):

```sh
python -m data_extraction.keywords --db data/articles.sqlite --top-k 8 --min-df 2
```

Personen zusammenführen (schreibt `personen` und `article_persons` neu):

```sh
python -m data_extraction.autoren --db data/articles.sqlite
```

Ohne `--input` setzt ein Neustart eine vorhandene Datenbank fort. `--dry-run`
zeigt den Plan, ohne das Modell zu laden oder zu schreiben. Ältere
Datenbanken erhalten neu hinzugekommene Spalten beim Öffnen automatisch.

`Ctrl+C` committet den begonnenen Batch und beendet den Prozess mit Exitcode 130.
Zum Fortsetzen denselben Befehl erneut aufrufen.

Richtwerte aus den Tests: etwa 4 Artikel pro Sekunde und 23 KB pro Artikel,
davon knapp 90 % für `candidates`. Eine Stichprobe von 70'000 Artikeln braucht
rund 5 Stunden und 1,6 GB, alle Artikel rund 33 Stunden und 11 GB.
Datenbanken sind über `.gitignore` von Git ausgeschlossen.

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
Modell und Parserregeln unverändert bleiben. Die Datenbank speichert keine
Modellversion; die gewählte Version gehört in das Laufprotokoll.

## Abrufschicht

`HttpSource` ist die einzige Stelle mit Netzwerkzugriff. Sie setzt User-Agent
und Timeout, wiederholt Verbindungsfehler sowie 429 und 503 höchstens dreimal
mit exponentiellem Backoff und verfolgt keine Weiterleitungen.

Die Freigabe des Vollcrawls erfolgt durch das Team, nicht durch das Skript.

## Module

| Datei | Aufgabe |
|---|---|
| `get_data.py` | separater Sitemap-Crawler, erzeugt die URL-Liste |
| `sources.py` | HTTP-Abruf, Timeout, Backoff, Statuscode |
| `page_parser.py` | HTML zu Titel, Lead, Körper, Ressort, Datum, Metriken, Autoren, Quellenzeile |
| `candidates.py` | spaCy NER und Nominalphrasen mit Grundform und Kopfnomen |
| `db.py` | SQLite-Schema, Migration, Transaktionen, Wiederaufnahme |
| `fetch_articles.py` | Ablauf, Batching, Signalbehandlung, CLI |
| `keywords.py` | Keyword-Auswahl aus den Kandidaten, CLI |
| `autoren.py` | Personen aus Namen, Kürzeln und IDs, CLI |

`handle_data.py` delegiert an denselben CLI. Kein Modul startet beim Import
Arbeit.

## Analyse (`src/`)

| Datei | Inhalt |
|---|---|
| `daten.py` | lädt die Tabellen als DataFrames (nur lesend, auch während eines Crawls); Jahr/Monat in Schweizer Zeit, Reaktionen vor Juni 2020 fehlend, `hauptressort` (elf Hauptressorts, Rest „andere“) |
| `netzwerk.py` | Projektionen (Kookkurrenz, Newman, Salton), Keyword-, Co-Autoren- und Autoren-Themennetz, Backbone, Kennzahlen, Zentralitäten, Communities, Assortativität mit Permutationstest, Nullmodell, Link Prediction, Export (GEXF + CSV) |
| `grafik.py` | einheitlicher Stil (`grafik.stil()`), feste Ressortfarben, Netzzeichnung, Balken, Heatmaps, Permutationstest |
| `01_eda.ipynb` | Datenqualität, Verteilungen, Plausibilitätsstichprobe, Vergleich mit der alten CSV, Massnahmen |
| `02_keyword_netz.ipynb` | Themennetz, H1–H3 |
| `03_autoren_netz.ipynb` | Co-Autorschaft, thematische Nähe, Reaktionen nach Thema, H4 |
| `keyword_landkarte.py` | Keyword-Landkarte im Stil von SpiegelMining (Gewicht „gegenseitige Wichtigkeit“, lokale Ausdünnung, Ressortfarben) als GEXF für Gephi: `python src/keyword_landkarte.py` |

Die Notebooks wählen die Datenbank selbst (`daten.standard_db()`):
`data/articles.sqlite`, sobald dort Keywords und Personen gebildet sind, sonst
die Kopie `data/articles_snapshot.sqlite`. Die Umgebungsvariable `SAN_DB` hat
Vorrang. Jeder Abschnitt beginnt mit der Frage, dem Grund und unserer Erwartung,
danach folgen Code, Werte und Grafiken und erst dann die Reflexion der Ergebnisse. Die Grafiken stehen nur im Notebook; Netze für Gephi landen in `Graphen/`.
