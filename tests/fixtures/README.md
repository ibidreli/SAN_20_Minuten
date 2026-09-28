# HTML-Fixtures

Gespeicherte Artikelseiten von 20min.ch, abgerufen am 2026-09-27. Sie existieren,
damit `page_parser` und `candidates` **ohne Netzwerkzugriff** getestet werden
koennen. Siehe `docs/features/F01-crawler-und-kandidatenextraktion.md`.

Die Auswahl deckt die Layout-Entwicklung von 2010 bis 2025 ab. Pro Jahrgang zwei
Artikel, dazu ein Fehlerfall.

| Datei | Jahr | Fliesstext-Absaetze | Andere Absaetze | Besonderheit |
|---|---|---|---|---|
| `artikel_2010_1.html` | 2010 | 4 | 1 | InfoBox, Agenturkuerzel |
| `artikel_2010_2.html` | 2010 | 4 | 1 | InfoBox, Agenturkürzel `(si)` |
| `artikel_2013_1.html` | 2013 | 13 | 1 | Crosshead, InfoBox, Agenturkuerzel |
| `artikel_2013_2.html` | 2013 | 6 | 1 | Crosshead, InfoBox |
| `artikel_2016_1.html` | 2016 | 12 | 1 | Crosshead, InfoBox, Agenturkürzel `(dia/sda)` |
| `artikel_2016_2.html` | 2016 | 9 | 1 | Crosshead, InfoBox |
| `artikel_2019_1.html` | 2019 | 3 | 1 | InfoBox |
| `artikel_2019_2.html` | 2019 | 10 | 1 | Crosshead, InfoBox |
| `artikel_2022_1.html` | 2022 | 6 | 3 | Crosshead, InfoBox |
| `artikel_2022_2.html` | 2022 | 12 | 2 | Crosshead, InfoBox |
| `artikel_2025_1.html` | 2025 | 11 | 6 | Crosshead, InfoBox |
| `artikel_2025_2.html` | 2025 | 14 | 7 | Crosshead, InfoBox |
| `artikel_gone_410.html` | – | HTTP 410 | – | Fehlerfall: Artikel entfernt |

**Spalte „Andere Absaetze“:** Absaetze innerhalb des `<article>`, die nicht die
haeufigste Klasse tragen, also Lead, Widgets, Infobox-Titel und Autorenkaesten.
Ihre Zahl steigt von 1 (2010) auf 6 bis 7 (2025). Neuere Artikel enthalten
deutlich mehr Beiwerk, der Boilerplate-Filter muss also gerade dort greifen.

**Maschinenlesbare Metadaten:** `fixtures.json`, mit URL, Jahr, Absatzzaehlung,
gefundenen `data-testid`-Werten und Markern je Datei.

Die Fixtures werden nicht neu erzeugt. Wer weitere braucht, ergaenzt sie einzeln
und traegt sie hier nach.

## Lokal geprüfte Korrekturen für F01

`bytes` misst die UTF-8-Dateigrösse. Zuvor enthielt das Feld die Zeichenzahl.
Die Agenturmarker in `artikel_2010_2.html` und `artikel_2016_1.html` sind vorhanden;
die beiden zuvor falschen `agentur`-Werte wurden berichtigt. Das HTML ist unverändert.

`p_body` zählt Absätze mit der häufigsten Klasse **vor** der Boilerplate-Filterung.
Ein eigener Agenturabsatz und Leseraufrufe können diese Klasse ebenfalls tragen.
Insbesondere enthält `artikel_2019_2.html` zweimal denselben Leseraufruf.
Der Parser entfernt ihn mit der im Auftrag bestätigten ergänzenden Absatzregel.
`testids` erfasst die drei relevanten Hooks auf der ganzen Seite, nicht nur im Artikel.
