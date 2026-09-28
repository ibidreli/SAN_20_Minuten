# Delegations-Prompt fuer F01

Alles unterhalb der Linie ist der Prompt. Er ist eigenstaendig lesbar und setzt
kein Wissen aus vorherigen Gespraechen voraus.

---

## Auftrag

Implementiere Feature F01 in diesem Repository. Die vollstaendige Spezifikation
steht in `docs/features/F01-crawler-und-kandidatenextraktion.md`. Lies sie
zuerst ganz, danach `STATUS.md` Abschnitt 4a und `tests/fixtures/README.md`.

Kurzfassung: Ersetze die Extraktionspipeline `data_extraction/handle_data.py`
durch einen neu geschriebenen Crawler, der pro Artikel Mehrwort-Keyphrasen
liefert (`Roger Federer` als eine Einheit, nicht `Roger` plus `Federer`) und der
nach einem Abbruch an seinem Stand weiterlaeuft. Der Artikelvolltext wird nicht
gespeichert, persistiert wird nur die Kandidatenschicht.

## Absolute Regel: kein einziger Abruf von 20min.ch

**Du fuehrst den Crawler nicht aus und sendest keinen HTTP-Request an
20min.ch. Auch keinen einzelnen, auch nicht zum Ausprobieren, auch nicht mit
`curl`, auch nicht "nur um zu sehen, ob es geht".**

Der Grund: Der Volltext wird bewusst nicht archiviert. Der spaetere Vollcrawl
ueber 447'748 Artikel ist deshalb praktisch nicht wiederholbar und wird erst nach
einer Abnahme durch das Team gestartet, nicht von dir. Ein Probelauf verfaelscht
ausserdem den Stand der Fortschrittsdatenbank, an dem das Team seinen Pilotlauf
misst.

Diese Regel ist nicht verhandelbar und nicht durch gute Absicht aufhebbar. Wenn
du glaubst, eine Aufgabe sei ohne Netzwerkzugriff nicht loesbar, dann halte an,
beschreibe das Problem und frage nach. Rate nicht, und weiche nicht aus.

Das Verbot betrifft ausschliesslich Netzwerkzugriffe auf 20min.ch. Lokale Tests,
das Lesen der Fixtures, das Installieren von Paketen und das Herunterladen des
spaCy-Modells sind erlaubt und noetig.

## Womit du stattdessen arbeitest

In `tests/fixtures/` liegen 13 gespeicherte Artikelseiten: je zwei aus 2010,
2013, 2016, 2019, 2022 und 2025, dazu eine geloeschte Seite mit HTTP 410 als
Fehlerfall. `tests/fixtures/fixtures.json` enthaelt zu jeder Datei die
erwarteten Kennzahlen (Anzahl Fliesstext-Absaetze, Anzahl uebriger Absaetze,
gefundene `data-testid`-Werte, Marker wie Agenturkuerzel).

Diese Dateien sind deine einzige Datenquelle. Sie reichen aus, wenn du das
Design unten einhaeltst.

## Das Design, das den Netzwerkzugriff entbehrlich macht

Trenne den HTTP-Zugriff von allem anderen. Der gesamte Code ausser einer einzigen
duennen Funktion muss ohne Netz lauffaehig und testbar sein.

```
                  ┌──────────────────────────────────────┐
                  │ Quelle (austauschbar)                │
                  │                                      │
   HttpSource ────┤  fetch(url) -> (status, html|None)   ├──── FixtureSource
   (Produktion,   │                                      │     (Tests + Probelauf,
    ungetestet,   └──────────────────────────────────────┘      liest aus
    ~20 Zeilen)                    │                            tests/fixtures/)
                                   ▼
              page_parser  ->  candidates  ->  db
              (rein, testbar)   (rein, testbar)  (SQLite, testbar)
```

Anforderungen an diese Trennung:

- `fetch_articles.py` nimmt die Quelle als Parameter entgegen und kennt keine
  `requests`-Aufrufe im eigenen Code
- Ein CLI-Schalter `--source fixtures` laesst den **kompletten** Ablauf gegen die
  Fixtures laufen: SQLite anlegen, Artikel verarbeiten, Kandidaten schreiben,
  Wiederaufnahme nach Abbruch. `--source http` ist die Produktionsvariante, die
  du nie aufrufst
- `FixtureSource` kann dieselben Fixtures mehrfach unter verschiedenen
  Pseudo-URLs ausliefern, damit ein Lauf ueber mehrere hundert Eintraege moeglich
  ist, ohne das Netz zu beruehren
- `HttpSource` enthaelt nur Abruf, Timeout, Backoff und Statuscode. Keine
  Parsing-Logik, kein Datenbankzugriff. Sie ist so klein, dass ein Review sie
  vollstaendig erfasst

Damit ist alles ausser rund zwanzig Zeilen mechanisch geprueft, und diese zwanzig
Zeilen sind per Augenschein nachvollziehbar.

## Was Fertigstellung heisst

Arbeite die Akzeptanzkriterien aus Abschnitt 10 der Spezifikation ab. Zusaetzlich
gilt fuer diesen Auftrag:

- [ ] `pytest tests/` ist gruen. Die Tests laufen ohne Netzwerkzugriff
- [ ] Ein Ende-zu-Ende-Lauf mit `--source fixtures` ueber mindestens 500
      Pseudo-Artikel laeuft durch
- [ ] Derselbe Lauf, mit `SIGINT` in der Mitte abgebrochen und neu gestartet,
      ergibt dieselbe Zeilenzahl in `articles` wie ein ununterbrochener Lauf.
      Zeige die beiden Zahlen
- [ ] `candidates` liefert fuer einen Fixture-Artikel eine Mehrwort-Entitaet mit
      Label `PER`, `ORG` oder `LOC`. Zeige die konkrete Phrase
- [ ] Die erzeugte Datenbank enthaelt keinen Artikelfliesstext. Belege es mit
      einer Abfrage ueber das Schema und ueber die Inhalte
- [ ] Kein Modul fuehrt beim blossen Import Code aus

## Nachweis, dass nicht gecrawlt wurde

Schreibe ans Ende deines Berichts:

1. Die Ausgabe von `grep -rn "20min.ch" data_extraction/ tests/` mit einer
   kurzen Einordnung jeder Fundstelle
2. Die Bestaetigung, dass `--source http` in dieser Sitzung nicht aufgerufen
   wurde
3. Falls du an einer Stelle Netzwerkzugriff gebraucht haettest: welche, und wie
   du es stattdessen geloest hast

## Arbeitsweise

- Deutsch fuer Prosa und Kommentare, Englisch fuer Bezeichner, Dateinamen und
  Commit-Nachrichten
- Der Code soll aussehen, als haette ihn ein Mensch geschrieben: benannte
  Konstanten statt magischer Zahlen, Kommentare nur dort, wo das Warum nicht aus
  dem Code hervorgeht, keine erklaerenden Kommentare zu Offensichtlichem
- Halte dich an den Umfang aus Abschnitt 4 der Spezifikation. Normalisierung,
  Lemmatisierung, Alias-Aufloesung, Stopplisten und Ranking gehoeren zu F02 und
  sind hier ausdruecklich nicht zu bauen
- Entscheide alles, was Abschnitt 11 der Spezifikation nicht dem Team vorbehaelt,
  selbst und halte die Entscheidung schriftlich fest
- Committe nicht und pushe nicht. Lege die Aenderungen im Arbeitsverzeichnis ab
  und fasse am Ende zusammen, was du geaendert hast

## Wenn etwas nicht aufgeht

Melde dich, statt zu improvisieren, wenn:

- eine Fixture nicht das enthaelt, was `fixtures.json` behauptet
- die Boilerplate-Regel aus Abschnitt 7.1 der Spezifikation (haeufigste
  `<p>`-Klasse im `<article>`) auf einem Jahrgang nicht traegt
- du zusaetzliche Fixtures brauchst, weil ein Fall nicht abgedeckt ist

Insbesondere der zweite Punkt ist ein erwartbarer Befund und kein Fehler deiner
Arbeit. Er gehoert gemeldet, nicht umgangen.
