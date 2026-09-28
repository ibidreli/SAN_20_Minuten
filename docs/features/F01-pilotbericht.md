# F01: Fixture-Nachweis und vorläufiger Pilotbericht

Stand: 27.09.2026. **Technisch offline verifiziert, Teamabnahme offen.**

Dieser Bericht verwendet zwölf unterschiedliche Artikelseiten aus sechs Jahrgängen
und eine gespeicherte HTTP-410-Seite. Die 650 Pseudo-Artikel sind Wiederholungen
dieser Fixtures, keine 650 unabhängigen Artikel. Der geschichtete Pilot mit rund
2'000 Artikeln aus 2010 bis 2025 und 20 manuellen Prüfungen pro Jahrgang hat
nicht stattgefunden. Das Kriterium „Pilotbericht liegt vor und ist abgenommen“
ist deshalb noch nicht erfüllt. Es besteht keine Vollcrawl-Freigabe.

## Umsetzung und Entscheidungen

- `handle_data.py` delegiert an den neuen CLI. `fetch_articles.py` verwendet
  eine injizierte Quelle ohne eigene HTTP-Aufrufe. `sources.py` trennt
  `FixtureSource` und den rund zwanzigzeiligen `HttpSource.fetch`.
- Vier Abrufthreads und Batches von 25 Artikeln sind die Vorgaben. Ein gemeinsames
  spaCy-Modell verarbeitet die Texte im Hauptthread; das verhindert eine
  Vervielfachung des Modellspeichers. Es liegt höchstens ein Batch HTML bereit.
- `SIGINT` und `SIGTERM` setzen ein Stoppsignal. Der begonnene Batch wird
  fertig verarbeitet und atomar committet. Danach endet der CLI mit Code 130.
  Unvorhergesehene Programmfehler rollen den ganzen Batch zurück.
- `pending` wird begrenzt aus SQLite gelesen. `--retry-failed` beziehungsweise
  `--retry-url` setzen Fehler gezielt zurück, ohne Versuchsstände zu löschen.
  `attempts` zählt Verarbeitungsläufe, nicht interne HTTP-Wiederholungen.
- HTTP 404/410 sind terminale `skipped`-Einträge. Sonstige HTTP-Fehler,
  leere Antworten und unbekannte Layouts werden `failed`. Der HTTP-Adapter
  wiederholt 429/503 und Verbindungsfehler maximal dreimal, mit 20 Sekunden
  Timeout je Anfrage und Wartezeiten von einer und zwei Sekunden. Er setzt
  einen User-Agent und verfolgt keine Weiterleitungen.
- SQLite verwendet das vorgegebene Zweitabellenschema, WAL, Fremdschlüssel und
  zusätzliche CHECK-Bedingungen. Ausschliesslich die vorgesehenen Metadaten
  werden in `mark_done` gebunden. Keine generische Serialisierung eines
  `Page`-Objekts. Pro Datenbank ist ein schreibender Prozess vorgesehen.
- Titel, Lead und Körper werden getrennt an spaCy übergeben, damit keine Phrase
  über eine Feldgrenze reicht. Alle vier NER-Labels bleiben erhalten.
  Bei jeder räumlichen Überlappung gewinnt die Entität; der überlappende
  Noun-Chunk wird vollständig verworfen. Häufigkeiten werden je
  `(phrase, label)` aggregiert, Feldflags aus den jeweiligen Fundstellen.
- Modell, NER, Parser und Lemmatizer sind aktiv; gespeichert wird `span.text`,
  niemals ein Lemma. Keine F02-Normalisierung, Aliasauflösung, Stoppliste oder
  Auswahl der besten Kandidaten wurde implementiert. Die Top-50-Tabelle unten
  ist nur die in der Spezifikation verlangte Berichtsauswertung.
- Der Default bleibt `de_core_news_lg`. Endgültige Modellwahl, Vollcrawl-Freigabe
  und Mitnahme der Interaktionsmetriken bleiben beim Team. Fehlende Metriken
  werden als NULL gespeichert, nicht als Null interpretiert.
- Keine zusätzlichen Artikelseiten oder Fixtures wurden beschafft.
  Installation, Bedienung und Wiederholung der Nachweise:
  [Pipeline-Anleitung](../../data_extraction/README.md).

## Boilerplate und Fixture-Korrekturen

Alle zwölf geparsten Artikelkörper wurden lokal vollständig textuell
gegengelesen. Die häufigste Klasse stimmt in allen zwölf Dateien mit den
Metadaten überein. Sie genügt allein nicht: Der doppelte Leseraufruf von 2019
trägt dieselbe Klasse. Nach Rückfrage hat der Auftraggeber die ergänzende,
eng gefasste Absatzregel ausdrücklich bestätigt. Sie entfernt vollständige
Aufforderungen der Form „Sagen Sie uns, …“ sowie „Hast du …? Erzähl uns davon.“
Zitate und beschreibende Sätze bleiben erhalten; das ist gesondert getestet.

Infoboxen, Bildbereiche, Kommentarbereiche und verwandte semantische Container
werden zusätzlich ausgeschlossen. Der erste klassenlose Absatz ist der Lead,
spätere klassenlose Absätze werden nicht als Körper übernommen. Eindeutige
Agenturmarker am Absatzende werden entfernt, auch wenn sie am letzten Satz
stehen. Ein Klassengleichstand oder ein fehlender Körper erzeugt einen
sichtbaren Parserfehler statt einer geratenen Auswahl.

| Fixture | Häufigste Klasse: Absätze | Nach Filter |
|---|---:|---:|
| artikel_2010_1.html | 4 | 4 |
| artikel_2010_2.html | 4 | 3 |
| artikel_2013_1.html | 13 | 13 |
| artikel_2013_2.html | 6 | 6 |
| artikel_2016_1.html | 12 | 12 |
| artikel_2016_2.html | 9 | 9 |
| artikel_2019_1.html | 3 | 2 |
| artikel_2019_2.html | 10 | 8 |
| artikel_2022_1.html | 6 | 6 |
| artikel_2022_2.html | 12 | 12 |
| artikel_2025_1.html | 11 | 11 |
| artikel_2025_2.html | 14 | 14 |

Die HTML-Dateien wurden nicht verändert. Korrigiert wurden `agentur: true`
für die tatsächlich vorhandenen Marker `(si)` und `(dia/sda)` in 2010_2
beziehungsweise 2016_1 sowie sämtliche zwölf `bytes`-Werte: Diese enthielten
Zeichenzahlen statt UTF-8-Dateigrössen. Die Tests prüfen die korrigierten Werte,
Absatzanzahlen, Klassen und die drei relevanten Hooks auf der gesamten Seite.

**Qualitätsbefund für den Pilot:** Die gemäss Abschnitt 7.1 übernommene
`clean_text`-Regel verändert auch korrekte Eigennamen, etwa `McLaren` zu
`Mc Laren`, `iPod` zu `i Pod` und `AfD` zu `Af D`.
„Unveränderte Oberflächenform“ bezieht sich in der jetzigen Implementierung
auf den an spaCy übergebenen bereinigten Text. Die ursprüngliche HTML-Schreibweise
ist bei solchen Fällen nicht mehr rekonstruierbar. Dieser Konflikt zwischen der
vorgegebenen Bereinigung und der gewünschten Erhaltung von Eigennamen muss vor
einem Vollcrawl bewertet werden. Es wurde kein Alias- oder Ausnahmelexikon
hinzugefügt.

**Nachtrag 27.09.2026, behoben.** `clean_text` trennt Binnenmajuskeln nur noch,
wenn der linke Wortteil mindestens drei Kleinbuchstaben hat, und loest
Bindestriche nur zwischen Kleinbuchstaben auf. `AfD`, `BaZ`, `iPhone`, `eBay`,
`McLaren`, `Baden-Württemberg` und `Covid-19` bleiben damit erhalten, waehrend
`NachrufRobert` und `EUBehörde` weiterhin getrennt werden. Dreizehn Faelle sind
in `tests/test_page_parser.py::test_clean_text_preserves_proper_names`
abgesichert. Ein erneuter Fixture-Lauf ueber 650 Eintraege bestaetigt die
Wirkung auf die Daten: `Af D.` wird zu `AfD.`, `Ba Z Druckerei` zu `BaZ`,
`Mc Laren Elva` zu `McLaren Elva`, und `i Pod`, `i Pads` sowie `i Phones`
verschwinden vollstaendig. Artikelzahlen unveraendert bei 600 done und
50 skipped, Kandidaten von 71'150 auf 70'450 gesunken, da Fragmente wegfallen.

Die Punkte Interaktionsmetriken und Durchsatz wurden vom Team geprueft und als
unproblematisch eingestuft; fuer das aktuelle Ziel werden sie nicht benoetigt.

## Technische Akzeptanz

`pytest tests/` ist grün. Letzter Lauf mit zusätzlicher Coverage-Messung:
**36 passed in 13.29s**. `pytest-socket` sperrt Netzverbindungen.
Auch die echten CLI-Kindprozesse sperren sämtliche Socket-Auditereignisse.

Die fünf neuen Pipeline-Module erreichen gemeinsam 371 von 382 abgedeckten
Anweisungen (97,1 %). Für das gesamte Verzeichnis sind es 76 %, weil der
bestehende Sitemap-Crawler nicht ausgeführt wird und die Importprüfung in einem
separaten Prozess läuft. Die gemockten HTTP-Tests erreichen sämtliche
Adapterzweige; das ist kein Nachweis für reale Serverantworten.

`pip check`: `No broken requirements found.`
`ruff format --check data_extraction tests scripts`: alle erfassten Dateien
formatiert. `git diff --check`: erfolgreich.

`ruff check data_extraction tests scripts` meldet acht bestehende Befunde
ausschliesslich in `get_data.py`: I001, BLE001, DTZ011, zweimal DTZ007,
PLR1730, E722 und S112. Dieselben acht Befunde wurden mit identischer
Dateizuordnung an der Sicherung der Originaldatei nachgewiesen.
Das Lintergebnis für das gesamte Verzeichnis ist daher **nicht grün**.
Die Linterkonfiguration wurde nicht geändert. Die Logik des Sitemap-Crawlers
wurde entsprechend Abschnitt 9 nur hinter den Import-Guard verlegt; der
Ausgabepfad ist korrigiert und der bisher globale Zustand wird explizit
übergeben.

Die Importprüfung umfasst jedes Modul in `data_extraction/` und verbietet
Modellladen, Datenbankverbindungen, Workerstarts, Signalinstallation,
Netzwerkzugriffe und Zugriff auf Nicht-Python-Dateien. Sie prüft zusätzlich,
dass weder Konsolenausgabe noch Dateien im Arbeitsverzeichnis entstehen.
Imports laden lediglich Definitionen und Abhängigkeiten.

### 650 Pseudo-Artikel und echtes SIGINT

Artefakte dieser Sitzung:
`/private/tmp/f01-evidence-20260927/`.
Die beiden SQLite-Dateien und `evidence.json` enthalten keine Artikelkörper.

Vor der Ausführung wurde der Dry-run geprüft. Reproduzierbarer Aufruf,
mit einem neuen Ausgabeverzeichnis:

```sh
python -m scripts.verify_f01 --output-dir /private/tmp/f01-neuer-nachweis --count 650 --batch-size 25 --dry-run
python -m scripts.verify_f01 --output-dir /private/tmp/f01-neuer-nachweis --count 650 --batch-size 25
```

| Messpunkt | articles gesamt | done | skipped | pending | candidates |
|---|---:|---:|---:|---:|---:|
| Ununterbrochener Lauf | 650 | 600 | 50 | 0 | 71'150 |
| Direkt vor SIGINT im zweiten Lauf | 650 | 300 | 25 | 325 | 35'575 |
| Nach sauberem Abbruch | 650 | 324 | 26 | 300 | 38'421 |
| Nach Neustart | 650 | 600 | 50 | 0 | 71'150 |

`SELECT count(*) FROM articles WHERE status='done'` ergibt am Ende
**600 und 600**, die Gesamtzeilenzahl **650 und 650**.
Je 100 erfolgreiche Pseudo-Artikel stammen aus 2010, 2013, 2016, 2019, 2022
und 2025. Alle `attempts` bleiben eins. Beidseitige SQL-EXCEPT-Abfragen
vergleichen sämtliche Artikel- und Kandidatenspalten ausser `fetched_at`:
keine Unterschiede. `PRAGMA integrity_check` ergibt `ok`,
`PRAGMA foreign_key_check` keine Zeilen.

### Mehrwortentitäten

Der synthetische Unit-Test enthält Roger Federer in Titel, Lead und Körper.
Er ergibt `Roger Federer | PER | count=3 | in_titel=1 | in_lead=1`,
keine getrennten Kandidaten `Roger` oder `Federer` und keinen
konkurrierenden Noun-Chunk desselben Bereichs.

Direkt aus der Fixture-Datenbank:

```sql
SELECT phrase, label, count, in_titel, in_lead
FROM candidates
WHERE url='fixture://artikel_2025_2.html/11' AND phrase='Elon Musk';
-- Elon Musk | PER | 3 | 0 | 1
```

### Schema und Inhalte ohne Volltext

Ausgeführte Schemaabfrage:

```sql
SELECT m.name, p.name
FROM sqlite_master AS m
JOIN pragma_table_info(m.name) AS p
WHERE m.type='table'
  AND lower(p.name) IN ('body', 'html', 'fulltext', 'content');
-- Keine Zeilen
```

Es gibt genau die Tabellen `articles` und `candidates`. Das vollständige
CREATE-Schema ist in `evidence.json` enthalten. Titel und Lead sind wie
vorgegeben vorhanden.

`scripts/verify_f01.py:check_no_fulltext` parst die Fixtures im Speicher und
prüft für alle zwölf Körper sowie die Körperabsätze ab 80 Zeichen jede
TEXT-Spalte beider Tabellen mit gebundenen Parametern. Beispiel für die
Kandidatentabelle:

```sql
SELECT count(*) FROM candidates
WHERE instr(COALESCE(url, ''), ?) > 0
   OR instr(COALESCE(phrase, ''), ?) > 0
   OR instr(COALESCE(label, ''), ?) > 0;
```

Ergebnis über **108 Prüftexte: 0 Treffer**. Kurze Nominalphrasen sind
ausdrücklich erlaubte Kandidaten; einzelne Wörter aus einem Artikelkörper
dürfen deshalb selbstverständlich in der Kandidatentabelle vorkommen.
Es wird weder HTML noch ein vollständiger Artikelkörper archiviert.

Auch `grep -ri "body" data_extraction/` wurde ausgeführt: Fundstellen gibt
es ausschliesslich im Parser, in der Übergabe an die Extraktion und in der
Kandidatenfunktion sowie deren Python-Bytecode. Kein Treffer in `db.py`.

## Lokaler Modellvergleich

Gemessen auf macOS 27.0 (Build 26A428), arm64, Python 3.11.9,
spaCy 3.8.16; alle drei Modelle in Version 3.8.0. Jeder Vergleich lief in einem
eigenen Prozess, auf denselben zwölf geparsten Fixtures. Die Extraktionszeit
enthält nur NLP und Kandidatenaggregation, nicht HTML-Parsing oder Modellladen.
RSS ist das Prozessmaximum inklusive Python, Modell und Parserdaten.

| Modell | Entitätsvorkommen pro Artikel | NLP für 12 Artikel | Modellladen | Max. RSS |
|---|---:|---:|---:|---:|
| sm | 38,75 | 0,782 s | 0,260 s | 304,1 MiB |
| md | 36,67 | 0,838 s | 0,517 s | 541,8 MiB |
| lg | 35,75 | 0,840 s | 0,707 s | 1'086,9 MiB |

Ein Messlauf je Modell, keine statistisch abgesicherte Laufzeitaussage.
Mehr gefundene Entitäten sind kein Qualitätsbeweis. Ohne annotierte
Referenzdaten lässt sich daraus keine Precision oder Recall ableiten.
**Empfehlung:** Den dokumentierten Default für die technische Reproduzierbarkeit
beibehalten und die endgültige Wahl im Teampilot anhand annotierter Beispiele
treffen. Es wurde keine endgültige Modellentscheidung vorweggenommen.

Maschinenlesbare Einzelwerte: `model-sm.json`, `model-md.json` und
`model-lg.json` im Nachweisverzeichnis. Wiederholung über
`python -m scripts.benchmark_f01 --model de_core_news_lg --output NEUE_DATEI`,
zuerst mit `--dry-run`.

Die verwendeten spaCy-Schnittstellen sind in der offiziellen Dokumentation
beschrieben: [Entitäten und Noun-Chunks](https://spacy.io/usage/linguistic-features),
[deutsche Modelle](https://spacy.io/models/de).

## Speicher und Laufzeit: Messung getrennt von Hochrechnung

**Gemessen:** Die vollständige SQLite-Datei belegt nach Schliessen
12'128'256 Bytes. 600 erfolgreiche Artikel liefern 71'150 Kandidatenzeilen,
also 118,58 unterschiedliche Phrase-Label-Kombinationen pro Artikel.
Tabellen und Indizes der Kandidaten beanspruchen davon 11'837'440 Bytes.
Inhalte sind unnormalisiert; SQLite wiederholt die URL in Kandidaten und
Primärschlüsselindex. Diese Kosten sind Bestandteil des vorgegebenen Schemas.

Der ununterbrochene Offline-Lauf brauchte 47,44 Sekunden inklusive Modellladen,
Parsing, Extraktion und SQLite. Unterbrochener Teil: 26,56 Sekunden,
anschliessende Wiederaufnahme: 23,55 Sekunden.

**Nur lineares Rechenbeispiel:** Bei exakt derselben Artikelverteilung wären
`12'128'256 / 600 × 447'748` etwa **9,05 GB** inklusive Indizes und
`47,44 / 600 × 447'748` etwa **9,83 Stunden** lokale Verarbeitung.
Produktions-URLs sind länger als die Pseudo-URLs. Weitere Jahrgänge,
Textlängen, eindeutige Phrasen, Netzlatenz und Backoff fehlen in dieser
Stichprobe. Dies ist daher keine belastbare Prognose des Vollcrawls.
Die ältere Annahme von 200 bis 300 MB ist durch diesen Nachweis nicht gedeckt.

## Häufigste 50 Kandidaten der zwölf Fixtures, Modell lg

Summierte Vorkommen über Titel, Lead und Körper, ohne Stoppliste und ohne
Zusammenführung unterschiedlicher Schreibweisen. Die vielen Pronomen kommen
aus den unverändert übernommenen spaCy-Noun-Chunks; ihre spätere Auswahl gehört
zu F02. Keine Kandidaten mit Push-, WhatsApp- oder Newsdesk-Bestandteilen:
zusätzlich per SQL über sämtliche 71'150 Kandidatenzeilen geprüft.

| Nr. | Phrase | Vorkommen |
|---:|---|---:|
| 1 | sich | 36 |
| 2 | er | 32 |
| 3 | es | 16 |
| 4 | die | 15 |
| 5 | man | 13 |
| 6 | sie | 11 |
| 7 | Er | 10 |
| 8 | das | 9 |
| 9 | Sie | 9 |
| 10 | Schweiz | 9 |
| 11 | Musk | 9 |
| 12 | BZM | 8 |
| 13 | was | 7 |
| 14 | der | 7 |
| 15 | Apple | 7 |
| 16 | italienischen | 6 |
| 17 | Es | 6 |
| 18 | BAG | 6 |
| 19 | Schweizer | 6 |
| 20 | allem | 6 |
| 21 | der Schweiz | 6 |
| 22 | letzten Jahr | 6 |
| 23 | Basler Zeitung | 5 |
| 24 | Ba Z | 5 |
| 25 | Jahr | 5 |
| 26 | Das | 5 |
| 27 | Tianjin | 5 |
| 28 | China | 5 |
| 29 | die Geste | 5 |
| 30 | Zürich | 4 |
| 31 | Dezember | 4 |
| 32 | Franken | 4 |
| 33 | dem | 4 |
| 34 | der Vergangenheit | 4 |
| 35 | Tamilen | 4 |
| 36 | Bundesgericht | 4 |
| 37 | der Spezialitätenliste | 4 |
| 38 | ihm | 4 |
| 39 | Omikron | 4 |
| 40 | Schweizer Franken | 4 |
| 41 | Bugatti Chiron | 4 |
| 42 | die Strasse | 4 |
| 43 | römischen | 4 |
| 44 | Mc Laren | 3 |
| 45 | Blocher | 3 |
| 46 | SVP | 3 |
| 47 | deren | 3 |
| 48 | ich | 3 |
| 49 | Dies | 3 |
| 50 | der Wirtschaftlichkeit | 3 |

## Offene Abnahme und Sicherungen

- [x] Offline-Tests über sechs Jahrgänge grün.
- [x] Alle zwölf Artikelkörper textuell gegengelesen; Boilerplate ergänzt.
- [x] Roger Federer als PER-Einheit; Mehrwortentität aus echter Fixture belegt.
- [x] Mehr als 500 erfolgreiche Pseudo-Artikel durchgelaufen.
- [x] Echtes SIGINT, Batch-Commit und Wiederaufnahme ohne Dubletten oder Verlust.
- [x] Schema und Inhalte auf Artikelvolltext geprüft.
- [x] Import ohne operative Nebenwirkungen geprüft.
- [ ] Geschichteter 2'000-Artikel-Pilot und 20 manuelle Sichtungen je Jahrgang.
- [ ] Pilotbericht vom Team abgenommen, Modell und Interaktionsmetriken entschieden.
- [ ] Vollcrawl freigegeben. Es wurde keiner gestartet.

Vor den Änderungen wurden `handle_data.py`, `get_data.py`,
`requirements.txt`, `STATUS.md`, `fixtures.json` und die Fixture-README
unter `/private/tmp/f01-backup.oSzodh/` gesichert. Keine Commits, kein Push.
Vorhandene unversionierte Dokumente und HTML-Fixtures bleiben erhalten.

## Nachweis: keine Artikelseite abgerufen

### 1. Ausgabe von grep und Einordnung

Ausgeführt: `grep -rn "20min.ch" data_extraction/ tests/`.
42 Trefferzeilen, 2'953'706 Ausgabebytes, Exitcode 0.
Nachfolgend sämtliche Fundstellen. Nur die 26 sehr langen HTML-Zeilen sind
mit ihrer Länge statt ihrem Inhalt wiedergegeben, um keine zweite
Volltextkopie in diesem Bericht anzulegen.

```text
data_extraction/get_data.py:10:BASE_URL = "https://www.20min.ch/sitemap/"
data_extraction/get_data.py:11:ARTIKEL_BASIS = "https://www.20min.ch"
tests/fixtures/artikel_2019_1.html:1:[HTML-Zeile ausgelassen; 10668 Zeichen]
tests/fixtures/artikel_2019_1.html:524:[HTML-Zeile ausgelassen; 227673 Zeichen]
tests/fixtures/artikel_2010_2.html:1:[HTML-Zeile ausgelassen; 9224 Zeichen]
tests/fixtures/artikel_2010_2.html:488:[HTML-Zeile ausgelassen; 207564 Zeichen]
tests/fixtures/artikel_2025_1.html:1:[HTML-Zeile ausgelassen; 14259 Zeichen]
tests/fixtures/artikel_2025_1.html:596:[HTML-Zeile ausgelassen; 271695 Zeichen]
tests/fixtures/artikel_2013_1.html:1:[HTML-Zeile ausgelassen; 11933 Zeichen]
tests/fixtures/artikel_2013_1.html:493:[HTML-Zeile ausgelassen; 210191 Zeichen]
tests/fixtures/artikel_2016_2.html:1:[HTML-Zeile ausgelassen; 10697 Zeichen]
tests/fixtures/artikel_2016_2.html:529:[HTML-Zeile ausgelassen; 210072 Zeichen]
tests/fixtures/artikel_2022_2.html:1:[HTML-Zeile ausgelassen; 18134 Zeichen]
tests/fixtures/artikel_2022_2.html:523:[HTML-Zeile ausgelassen; 280989 Zeichen]
tests/fixtures/README.md:3:Gespeicherte Artikelseiten von 20min.ch, abgerufen am 2026-09-27. Sie existieren,
tests/fixtures/artikel_2022_1.html:1:[HTML-Zeile ausgelassen; 12508 Zeichen]
tests/fixtures/artikel_2022_1.html:561:[HTML-Zeile ausgelassen; 232346 Zeichen]
tests/fixtures/artikel_2025_2.html:1:[HTML-Zeile ausgelassen; 16918 Zeichen]
tests/fixtures/artikel_2025_2.html:603:[HTML-Zeile ausgelassen; 280706 Zeichen]
tests/fixtures/artikel_2013_2.html:1:[HTML-Zeile ausgelassen; 9841 Zeichen]
tests/fixtures/artikel_2013_2.html:533:[HTML-Zeile ausgelassen; 212587 Zeichen]
tests/fixtures/artikel_2016_1.html:1:[HTML-Zeile ausgelassen; 11630 Zeichen]
tests/fixtures/artikel_2016_1.html:524:[HTML-Zeile ausgelassen; 216587 Zeichen]
tests/fixtures/fixtures.json:15:    "url": "https://www.20min.ch/story/maximal-30-prozent-auslaender-in-den-schulen-138758570895",
tests/fixtures/fixtures.json:32:    "url": "https://www.20min.ch/story/de-la-rosa-zweiter-sauber-pilot-862123937859",
tests/fixtures/fixtures.json:50:    "url": "https://www.20min.ch/story/blocher-schliesst-die-baz-druckerei-349647421800",
tests/fixtures/fixtures.json:68:    "url": "https://www.20min.ch/story/es-war-auslaenderhass-pur-615242484584",
tests/fixtures/fixtures.json:86:    "url": "https://www.20min.ch/story/bund-verglich-preise-fuer-medikamente-ungenuegend-603373225264",
tests/fixtures/fixtures.json:104:    "url": "https://www.20min.ch/story/apple-sperrt-ipod-eines-lesers-fuer-46-jahre-650937494719",
tests/fixtures/fixtures.json:121:    "url": "https://www.20min.ch/story/sie-wollte-kein-zweites-date-weil-er-nicht-bezahlte-912275813870",
tests/fixtures/fixtures.json:139:    "url": "https://www.20min.ch/story/wie-ueberstehen-sie-langweilige-meetings-623460157537",
tests/fixtures/fixtures.json:157:    "url": "https://www.20min.ch/story/nachbarstadt-von-peking-ruft-wegen-zwei-corona-faellen-zum-massentest-auf-517806946535",
tests/fixtures/fixtures.json:175:    "url": "https://www.20min.ch/story/der-bugatti-la-voiture-noire-faehrt-jetzt-mit-zuercher-nummernschild-759199970621",
tests/fixtures/fixtures.json:193:    "url": "https://www.20min.ch/story/ukraine-warum-gefluechtete-kaum-jobs-mehr-in-der-schweiz-finden-103253091",
tests/fixtures/fixtures.json:211:    "url": "https://www.20min.ch/story/amtseinfuehrung-war-musks-ausgestreckter-arm-ein-bellamy-salute-103263365",
tests/fixtures/fixtures.json:216:    "url": "https://www.20min.ch/story/darts-lukas-littler-16-erreicht-wm-halbfinale-887675741944",
tests/fixtures/artikel_2010_1.html:1:[HTML-Zeile ausgelassen; 9373 Zeichen]
tests/fixtures/artikel_2010_1.html:484:[HTML-Zeile ausgelassen; 202473 Zeichen]
tests/fixtures/artikel_2019_2.html:1:[HTML-Zeile ausgelassen; 12174 Zeichen]
tests/fixtures/artikel_2019_2.html:533:[HTML-Zeile ausgelassen; 234281 Zeichen]
tests/fixtures/artikel_gone_410.html:1:[HTML-Zeile ausgelassen; 3395 Zeichen]
tests/fixtures/artikel_gone_410.html:293:[HTML-Zeile ausgelassen; 9240 Zeichen]
```

Die beiden `get_data.py`-Zeilen sind bestehende URL-Konstanten des separaten,
nicht ausgeführten Sitemap-Crawlers. Die README-Zeile beschreibt die Herkunft
der vorhandenen Fixtures. Jede der 13 JSON-Zeilen ist die Herkunfts-URL genau
einer gespeicherten Seite. Beide Treffer pro HTML-Datei stammen aus dem
bereits vorhandenen Seiteninhalt beziehungsweise eingebetteten Seitendaten;
keine dieser URLs wurde aufgerufen. Die Trefferprüfung allein beweist keine
Netzwerkabwesenheit; zusätzlich waren Tests und CLI-Nachweise technisch gegen
Netzverbindungen gesperrt.

### 2. Ausgeführte Quellen

**`--source http` wurde in dieser Sitzung nicht aufgerufen.**
Es gab keinen HTTP-Abruf einer Artikelseite, auch keinen Einzelabruf nach der
später erteilten Erlaubnis. Alle CLI-Läufe verwendeten `--source fixtures`;
die HTTP-Unit-Tests verwendeten ausschliesslich gemockte Antworten.

### 3. Wofür Netzwerk benötigt wurde

Netzwerkzugriff wurde nur für Python-Pakete, die drei spaCy-Modelle von GitHub
und offizielle spaCy-Dokumentation verwendet. Kein Zugriff auf 20min.ch.
Parserprüfung, Fehlerfälle, Modellvergleich, Schemaaudit und Wiederaufnahme
wurden vollständig mit lokalen Fixtures oder synthetischen Unit-Test-Eingaben
gelöst. Ein produktiver Pilot wurde weder durchgeführt noch simuliert
als abgenommen ausgegeben.
