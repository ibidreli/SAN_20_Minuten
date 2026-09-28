# F01 · Crawler v2 und Kandidatenextraktion

**Projekt:** SAN 20 Minuten, Modul Soziale Netzwerke Analysieren, FHNW
**Repository:** `SAN_20_Minuten`, Branch `mannaluca02/san-reset-keep-data`
**Verwandte Dokumente:** `STATUS.md` (Meilensteine M2, M2b, M3), Abschnitt 4a
**Erstellt:** 2026-09-27
**Status:** bereit zur Umsetzung

---

## 1. Ziel in zwei Saetzen

Ersetze die bestehende Extraktionspipeline `data_extraction/handle_data.py` durch
einen neu geschriebenen Crawler, der pro Artikel Mehrwort-Keyphrasen statt
Einzelwoerter liefert und nach einem Abbruch an seinem Stand weiterlaeuft.

Der Artikelvolltext wird dabei **nicht gespeichert**. Persistiert wird die
Kandidatenschicht: alle im Artikel gefundenen Phrasen mit Entitaetslabel und
Haeufigkeit.

---

## 2. Warum, mit Belegen

Das Vorgaengerprojekt scheiterte an der Keyword-Qualitaet. Die drei Befunde,
gemessen am bestehenden Datensatz (118'302 Artikel ab 2020):

| Befund | Beleg |
|---|---|
| Mehrwortbegriffe zerfallen in Einzelteile | `extract_clean_terms` in `handle_data.py:144` zaehlt einzelne NOUN- und PROPN-Tokens. „Roger Federer“ kann diese Funktion prinzipiell nicht als Einheit liefern |
| Singular und Plural stehen als zwei Knoten | `kanton` und `kantone` erscheinen beide im Vokabular, weil spaCy in `handle_data.py:24` mit `exclude=[..., "lemmatizer"]` geladen wird |
| Redaktionelles Boilerplate landet unter den Top-Begriffen | Unter den 15 haeufigsten Begriffen des Korpus stehen `news`, `push` und `whatsapp`. Ursache: `trafilatura.extract()` in `handle_data.py:180` nimmt den gesamten Seitentext inklusive Hinweisboxen |

Das Netzwerk, das auf diesen Begriffen aufbaut, ist der gesamte Analysegegenstand
des Projekts. Die Extraktion ist damit nicht ein Vorverarbeitungsschritt, sondern
die Grundlage jeder spaeteren Aussage.

---

## 3. Die harte Randbedingung

**Der Volltext wird nie auf Platte geschrieben.** Er lebt im Arbeitsspeicher, bis
die Kandidatenextraktion darauf gelaufen ist, danach wird er verworfen.

Daraus folgt eine Konsequenz, die den Ablauf bestimmt: der Crawl ueber 447'748
Artikel ist praktisch **nicht wiederholbar**. Fehler in den Kandidatenregeln oder
im Boilerplate-Filter sind danach nicht mehr am Schreibtisch korrigierbar, sondern
nur durch einen zweiten Vollcrawl.

**Deshalb gilt: Teil B (Pilot) ist vor Teil C (Vollcrawl) abzuschliessen.**
Kein Vollcrawl ohne abgenommenen Pilotbericht.

---

## 4. Umfang

### Im Umfang

- Neuschrieb von `data_extraction/handle_data.py` in vier Module (siehe 5)
- SQLite als Fortschritts- und Ergebnisspeicher
- Boilerplate-Filter auf dem Artikel-HTML
- Kandidatenextraktion mit spaCy NER und Noun-Chunks
- Pilotlauf ueber eine geschichtete Stichprobe mit schriftlichem Bericht
- Unit-Tests gegen gespeicherte HTML-Fixtures

### Nicht im Umfang

- Normalisierung, Lemmatisierung, Alias-Aufloesung, Stopplisten, Ranking.
  Das ist F02 und arbeitet auf der von F01 erzeugten Kandidatenschicht
- Netzwerkkonstruktion, Analysen, Visualisierung
- Aenderungen an `get_data.py`, mit einer Ausnahme (siehe 9)

---

## 5. Zielstruktur

```
data_extraction/
  get_data.py         unveraendert bis auf den Bugfix in Abschnitt 9
  db.py               SQLite-Schema, Verbindung, Resume-Abfragen
  page_parser.py      HTML  ->  titel, lead, body, ressort, datum, metriken
  candidates.py       Text  ->  Kandidatenphrasen
  fetch_articles.py   Orchestrierung: Pool, Batching, Signal-Handling
tests/
  fixtures/           gespeicherte HTML-Seiten, ein Jahrgang je Datei
  test_page_parser.py
  test_candidates.py
```

Die Trennung ist funktional begruendet: `page_parser` und `candidates` muessen
sich **ohne Netzwerkzugriff** gegen Fixtures testen lassen. Genau darauf beruht
der Pilot, und ohne Volltextarchiv gibt es keinen zweiten Versuch.

---

## 6. Datenschema

```sql
CREATE TABLE articles (
    url          TEXT PRIMARY KEY,
    status       TEXT NOT NULL DEFAULT 'pending',   -- pending | done | failed | skipped
    attempts     INTEGER NOT NULL DEFAULT 0,
    http_code    INTEGER,
    fetched_at   TEXT,
    datum        TEXT,        -- aus dem HTML, Fallback: Sitemap-Datum
    titel        TEXT,
    lead         TEXT,
    ressort      TEXT,
    likes        INTEGER,
    shares       INTEGER,
    kommentare   INTEGER
);
-- bewusst KEINE Spalte body

CREATE TABLE candidates (
    url        TEXT NOT NULL REFERENCES articles(url),
    phrase     TEXT NOT NULL,     -- Oberflaechenform, unveraendert
    label      TEXT NOT NULL,     -- PER | ORG | LOC | MISC | NOUN_CHUNK
    count      INTEGER NOT NULL,  -- Vorkommen im Artikel
    in_titel   INTEGER NOT NULL,  -- 0 oder 1
    in_lead    INTEGER NOT NULL,  -- 0 oder 1
    PRIMARY KEY (url, phrase, label)
);

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_candidates_phrase ON candidates(phrase);
```

**Wichtig zur Oberflaechenform:** `phrase` wird unveraendert gespeichert, also
„Roger Federer“ mit Grossschreibung und „die Kantone“ mit Artikel, falls spaCy
das so abgrenzt. Jede Normalisierung passiert in F02. Der Grund: nur so lassen
sich die Normalisierungsregeln spaeter aendern, ohne neu zu crawlen.

**Warum Leserinteraktionen mitgenommen werden:** `likes`, `shares` und
`kommentare` fallen im selben HTML-Parse ohne Zusatzaufwand an und eroeffnen eine
vierte Analyse (Themenpaare nach Leserresonanz). Im Bewertungsraster ist
„Vielfalt der Netzwerk-Analysen“ das am staerksten gewichtete Kriterium.

---

## 7. Anforderungen je Modul

### 7.1 `page_parser.py`

**Gepruefte HTML-Struktur.** Am 2026-09-27 an je einem Artikel aus 2010, 2015,
2020 und 2024 verifiziert:

| Beobachtung | Konsequenz |
|---|---|
| Genau ein `<article>`-Element pro Seite, in allen vier Jahrgaengen | `<article>` ist der Anker fuer den Artikelkoerper |
| Stabile `data-testid`-Werte: `Crosshead`, `InfoBox`, `Rating` | brauchbare Hooks fuer Zwischentitel, Infoboxen und die Bewertung |
| CSS-Klassen sind Styled-Components-Hashes, etwa `sc-2f3736c6-2 gjJEEZ` (2010 bis 2020) gegen `sc-2f3736c6-2 bDdfNG` (2024) | **Niemals auf eine konkrete Klasse selektieren.** Sie wechselt mit dem Build |

**Empfohlene Regel fuer den Fliesstext**, weil sie den Klassenwechsel ueberlebt:
Innerhalb des `<article>` die **haeufigste** `<p>`-Klasse bestimmen und nur diese
Absaetze als Fliesstext nehmen. Die Regel ist relativ, nicht absolut, und war in
allen vier geprueften Jahrgaengen korrekt.

- Der **erste** `<p>` ohne Klasse ist der Lead
- Spaetere `<p>` ohne Klasse sind Widgets, etwa die Umfrage „Wie regelmaessig isst
  du Fleisch?“ im Artikel von 2024, und gehoeren verworfen
- Abweichende Klassen sind Beiwerk. Belegte Faelle: `sc-f19a47c0-1` mit dem Text
  „Das 20-Minuten-Newsdesk-Team liefert dir 24/7 aktuelle Nachrichten ...“
  (Autorenkasten, 2010) und `sc-47558006-4` mit „Ueber die Expertinnen“
  (Infobox-Titel, 2024)

**Ebenfalls zu verwerfen:** Agenturkuerzel als eigener Absatz, etwa `(sda)`,
Bildlegenden, Related-Boxen, Kommentarbereich, Disclaimer sowie Push-, Newsletter-
und WhatsApp-Hinweise.

**Aus `handle_data.py` zu uebernehmen**, erprobt ueber 449'000 Artikel:

| Funktion | Zeilen | Zweck |
|---|---|---|
| `clean_text` | 61-69 | trennt zusammengeklebte Woerter, etwa `NachrufRobert` zu `Nachruf Robert`. Muss **vor** spaCy laufen, weil NER an solchen Klebewoertern scheitert |
| `extract_ressort_from_html` | 71-86 | JSON-LD `articleSection` mit Breadcrumb-Fallback. Liefert das Knotenattribut fuer Hypothese H2, im Altbestand zu 100 Prozent gefuellt |
| `extract_datum_from_html` | 88-105 | Artikeldatum statt Sitemap-Datum, Grundlage fuer H1 und H3 |
| `parse_count_from_sibling` | 107-121 | liest die Zahl neben einem Button |
| `comments_enabled` | 123-142 | prueft, ob ein Kommentarbereich existiert |

### 7.2 `candidates.py`

Eingabe ist der bereinigte Text, Ausgabe eine Liste von Kandidaten.

- spaCy-Modell **konfigurierbar** ueber eine Konstante, Vorgabe `de_core_news_lg`.
  Die endgueltige Wahl faellt im Pilot (siehe 8)
- Das Modell wird **mit** NER, Parser und Lemmatizer geladen. Das ist der
  Gegensatz zum Altbestand und der Kern dieses Tickets
- Entitaeten aus `doc.ents` mit den Labels PER, ORG, LOC und MISC, jeweils als
  eine Phrase, also „Roger Federer“ und nicht „Roger“ plus „Federer“
- Nominalphrasen aus `doc.noun_chunks` fuer Themen ohne Entitaetsstruktur, Label
  `NOUN_CHUNK`
- Ueberlappungen: wenn eine Entitaet und ein Noun-Chunk denselben Textbereich
  abdecken, gewinnt die Entitaet
- Fuer jede Phrase zaehlen: Vorkommen im Artikel, ob sie im Titel stand, ob sie
  im Lead stand
- **Keine** Normalisierung, keine Stoppliste, kein Ranking. Das ist F02

### 7.3 `db.py`

- Schema aus Abschnitt 6 anlegen, idempotent
- `pending_urls(limit)`, `mark_done`, `mark_failed`, `reset_failed`
- Schreibvorgaenge in Transaktionen, ein Batch pro Commit
- WAL-Modus, damit ein Leseprozess den laufenden Crawl nicht blockiert

### 7.4 `fetch_articles.py`

| Anforderung | Kriterium |
|---|---|
| Wiederaufnahme | Neustart ist `SELECT url FROM articles WHERE status='pending'`. Kein Einlesen der gesamten Ausgabe wie in `handle_data.py:42-56` |
| Fehlerbehandlung | `failed` mit Versuchszaehler, exponentielles Backoff, Fehlschlaege gezielt nachfahrbar |
| Schonender Umgang | begrenzte Parallelitaet, Backoff bei 429 und 503, gesetztes User-Agent-Feld |
| Abbruch | Ctrl+C beendet sauber, der laufende Batch wird noch committet |
| Fortschritt | Ausgabe von Durchsatz, Fehlerquote und Restdauer |
| Lesbarkeit | handgeschriebener Stil, benannte Konstanten, `if __name__ == "__main__"`-Guard. Kein Code auf Modulebene, der beim Import laeuft |

---

## 8. Teil B: Pilotlauf, Abnahmebedingung fuer den Vollcrawl

Geschichtete Stichprobe von rund 2'000 Artikeln, gleichmaessig ueber 2010 bis 2025.
Ergebnis ist ein kurzer Bericht unter `docs/features/F01-pilotbericht.md` mit:

1. **Boilerplate-Pruefung:** 20 Artikel je Jahrgang von Hand gesichtet. Enthaelt
   der `body` noch Hinweisboxen, Bildlegenden oder Autorenkaesten?
2. **Modellwahl:** `de_core_news_sm`, `md` und `lg` auf derselben Stichprobe
   gegeneinander. Verglichen werden gefundene Entitaeten je Artikel, Laufzeit und
   Speicherbedarf. Die Wahl ist danach fixiert
3. **Groesse:** hochgerechneter Speicherbedarf der Kandidatenschicht fuer 447'748
   Artikel
4. **Laufzeit:** hochgerechnete Dauer des Vollcrawls
5. **Trefferbild:** die 50 haeufigsten Kandidatenphrasen der Stichprobe.
   Erwartung: keine Push-, WhatsApp- oder Newsdesk-Begriffe mehr

---

## 9. Bugfix in `get_data.py`

Zwei kleine Korrekturen, unabhaengig vom Rest:

- Zeile 96: `AUSGABE_DATEI = "20min_artikel_sortiert.csv"` schreibt ohne
  `data/`-Praefix in das aktuelle Arbeitsverzeichnis statt nach `data/`
- Die Datei hat keinen `__main__`-Guard, der Crawl startet beim blossen Import

---

## 10. Akzeptanzkriterien

Alle Punkte sind pruefbar, kein Punkt ist eine Einschaetzung.

- [ ] `pytest tests/` ist gruen, mit Fixtures aus mindestens vier Jahrgaengen
- [ ] `page_parser` liefert auf allen Fixtures einen `body` ohne Boilerplate,
      von Hand gegengelesen
- [ ] `candidates` liefert fuer einen Testartikel ueber Roger Federer die Phrase
      `Roger Federer` mit Label `PER`, **nicht** `Roger` und `Federer` getrennt
- [ ] Ein Lauf ueber 500 Artikel aus fuenf Jahrgaengen laeuft durch
- [ ] Ctrl+C mitten im Lauf, danach Neustart: keine Dublette, kein Verlust,
      nachgewiesen ueber `SELECT count(*) FROM articles WHERE status='done'`
      vor und nach dem Abbruch
- [ ] `grep -ri "body" data_extraction/` zeigt keine Persistierung des Volltexts
- [ ] Die Datenbank enthaelt nach einem Testlauf keine Spalte und keinen Wert
      mit Artikelfliesstext
- [ ] Pilotbericht liegt vor und ist abgenommen
- [ ] Kein Code laeuft beim Import eines der Module

---

## 11. Offene Punkte, die der Umsetzende **nicht** allein entscheidet

| Punkt | Wer entscheidet | Wann |
|---|---|---|
| spaCy-Modell `sm`, `md` oder `lg` | Team, auf Basis des Pilotberichts | nach Teil B |
| Freigabe des Vollcrawls | Team | nach Teil B |
| Ob `likes`, `shares`, `kommentare` wirklich mitlaufen | Team | vor Teil C |

Bei allem anderen gilt: entscheiden, im Pilotbericht festhalten, weiterarbeiten.

---

## 12. Referenzen

| Was | Wo |
|---|---|
| Gesamtplan, Meilensteine, Hypothesen | `STATUS.md` |
| Begruendung der Kandidatenschicht | `STATUS.md`, Abschnitt 4a |
| Alte Extraktion, Quelle der uebernommenen Funktionen | `data_extraction/handle_data.py` |
| URL-Liste, 449'180 Eintraege 2003 bis 2025 | `data/20min_artikel_sortiert.csv` |
| Illustration des Zielmodells | `src/00_beispiel_netzwerk.py` |
| Bewertungsraster des Moduls | `docs/SAN-Bewertungsraster.xlsx` |
