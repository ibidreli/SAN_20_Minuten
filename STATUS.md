# STATUS: SAN-Projekt 20 Minuten (Neustart)

**Stand:** 2026-09-17
**Branch:** `mannaluca02/san-reset-keep-data`
**Team:** Elias, Luca
**Modul:** Soziale Netzwerke Analysieren (SAN), FHNW

> Dieses Dokument begleitet das ganze Modul. Es wird bei jeder Aenderung
> nachgefuehrt: Meilensteinfortschritt, neuer Blocker, erzeugtes Artefakt,
> Korrektur. **Fortschritt, der hier nicht steht, gilt als nicht passiert.**

---

## 1. Termine

| Was | Wann | Quelle |
|---|---|---|
| Schriftliche Pruefung (40% der Modulnote) | **Mi 04.11.2026, 14:15 bis 15:00**, Stoff ab LE3 | `docs/SAN-portrait.md` |
| Projektabgabe (60% der Modulnote) | **So 03.01.2027, 23:59:59** | `docs/SAN-portrait.md` |
| Meilenstein-Dokument | so frueh wie moeglich, „vor der Umsetzung des Projekts“ | `docs/SAN-Projektbeschreibung.pdf` |
| Projektbesprechung | auf Nachfrage, in den letzten zwei Semesterwochen | `docs/SAN-portrait.md` |

Verbleibend ab heute: **7 Wochen bis zur Pruefung, 15 Wochen bis zur Abgabe.**

---

## 2. Getroffene Entscheidungen

| Nr | Entscheidung | Begruendung |
|---|---|---|
| E1 | **Netzwerkmodell B**: One-Mode-Keyphrase-Netzwerk, projiziert aus dem bipartiten Artikel-Keyphrase-Graphen. Knoten sind ausschliesslich Keyphrasen. | Team-Entscheid. Artikel verschwinden in der Projektion, bleiben aber als Kantengewicht und im Two-Mode-Zwischenschritt sichtbar (LE3). |
| E2 | **Zeitraum ab 2010**, 447'748 Artikel | Team-Entscheid. 2003 bis 2009 sind mit 1'429 Artikeln zu duenn besetzt und wuerden die Jahresvergleiche verzerren. |
| E3 | **Volltext neu crawlen** statt Titel und Lead wiederzuverwenden | Der Volltext ist in den Altdaten nicht persistiert. Stichprobe 2026-09-17: 8 von 8 Artikeln aus 2010, 2015, 2020 und 2024 abrufbar, rund 0.4s pro Artikel. Hochrechnung bei 25 Workern: 2 bis 4 Stunden. |
| E4 | **Scraper wird neu geschrieben**, mit SQLite als Fortschrittsspeicher | Der alte Scraper las zur Wiederaufnahme die komplette Ausgabedatei ein. Das traegt bei 448k Artikeln nicht mehr. |
| E8 | **Der Volltext wird nicht persistiert.** Er lebt nur im Arbeitsspeicher, bis die Kandidatenextraktion darauf gelaufen ist, danach wird er verworfen | Team-Entscheid. Gespeichert wird stattdessen die **Kandidatenschicht** (siehe Abschnitt 4a), die alle spaeteren Iterationen ohne Neu-Crawl traegt |
| E5 | **Extraktion per spaCy NER + Noun-Chunks + Lemmatisierung + Alias-Mapping** | Deterministisch, reproduzierbar, im Notebook erklaerbar, keine GPU noetig. „Roger Federer“ bleibt eine Einheit, „kantone“ und „kanton“ werden zusammengefuehrt. |
| E6 | **Drei Hypothesen** (siehe Abschnitt 5) | Das Bewertungsraster fragt ausdruecklich: „Wurden, wo sinnvoll, Hypothesentests angewendet?“ |
| E7 | **Pruefung am regulaeren Termin**, 04.11.2026 | Theorie laeuft parallel zum Pipelineaufbau. |

**Aus dem Altprojekt behalten:** die Rohdaten (`data/20min_artikel_sortiert.csv`,
449'180 URL-Datum-Paare) und der Sitemap-Crawler als Vorlage.
**Verworfen:** Autoren-Kollaborationsnetzwerk, die alte `handle_data.py`-Extraktion,
alle Analysen des Vorprojekts.

---

## 3. Meilensteine

Status: ✅ erledigt · 🟡 in Arbeit · ⬜ offen · 🔴 blockiert

### M0 · Reset und Projektgeruest ⬜
**Woche 1 (bis 21.09.)**

- `.venv` im Worktree, `requirements.txt` aufgeraeumt (die aktuelle Datei listet `pandas` dreimal und `newspaper3k`, das nirgends verwendet wird)
- Ordnerstruktur: `data_extraction/`, `src/`, `scripts/`, `data/`, `out_plots/`, `graphen/`, `docs/`, `submission/`
- Projekt-`CLAUDE.md` mit der Pflegeregel fuer dieses Dokument
- `docs/` aus dem Altprojekt uebernehmen (Portrait, Projektbeschreibung, Bewertungsraster, Skript)

**Fertig, wenn:** `python -c "import spacy, networkx, pandas"` im Worktree-venv laeuft und die Ordnerstruktur steht.

### M1 · Meilenstein-Dokument einreichen ⬜
**Woche 2 (bis 28.09.) · hat Vorrang vor allem Technischen**

Das Dokument ist eine Modulabgabe und soll laut Projektbeschreibung **vor** der
Umsetzung eingereicht werden, damit das Feedback des Dozenten noch etwas nuetzt.
Inhalt: Projekttitel, Team, Datenquelle mit Rechtslage, Modellierung, geschaetzte
Netzwerkgroesse, die drei Analysen mit These, Filterung, Methode und Erwartung.

**Fertig, wenn:** `docs/Meilenstein.md` eingereicht und der Eingang bestaetigt ist.

### M2 · Scraper v2 ⬜
**Woche 2 bis 3 (bis 05.10.)**

`data_extraction/fetch_articles.py`, neu geschrieben:

| Anforderung | Umsetzung |
|---|---|
| Nur die noetigen Teile | Titel, Lead und Artikelkoerper. Verworfen werden Push- und WhatsApp-Hinweise, Bildlegenden, Related-Boxen, Autorenkaesten, Kommentare und Disclaimer |
| Volltext transient | Der Artikelkoerper wird geparst und sofort zu Kandidaten verdichtet. Er verlaesst den Arbeitsspeicher nie und wird nicht auf Platte geschrieben |
| Wiederaufnahme nach Abbruch | SQLite, `articles(url PK, status, attempts, http_code, fetched_at, titel, lead, ressort)` plus `candidates(url, phrase, label, count)`. **Keine `body`-Spalte.** Neustart ist `SELECT url WHERE status='pending'` |
| Fehlerbehandlung | Status `failed` mit Versuchszaehler, exponentielles Backoff, gezieltes Nachfahren der Fehlschlaege |
| Schonender Umgang | begrenzte Parallelitaet, Backoff bei 429 und 503, robots.txt dokumentiert |
| Lesbarer Code | handgeschriebener Stil, benannte Konstanten, keine generischen Kommentare |

**Fertig, wenn:** ein Lauf ueber 500 Artikel aus fuenf verschiedenen Jahrgaengen
durchlaeuft, ein erzwungener Abbruch mit Ctrl+C ohne Datenverlust wieder aufsetzt,
und eine Sichtpruefung von 20 Artikeln kein Boilerplate im `body` zeigt.

### M2b · Pilotlauf und Festzurren der Kandidatenregeln ⬜
**Woche 3 · Voraussetzung fuer M3, nicht optional**

Weil der Volltext nicht aufbewahrt wird, ist der Vollcrawl praktisch nicht
wiederholbar. Vorher auf einer geschichteten Stichprobe von rund 2'000 Artikeln
(gleichmaessig ueber 2010 bis 2025) klaeren:

- Greift der Boilerplate-Filter in allen Jahrgaengen? Das Seitenlayout von 20min
  hat sich ueber 15 Jahre mehrfach geaendert
- Welches spaCy-Modell: `de_core_news_sm`, `md` oder `lg`? Die Wahl ist danach
  festgelegt
- Welche Kandidatenregeln: welche Entitaetslabels, wie werden Noun-Chunks
  beschnitten, wird die Position im Artikel mitgespeichert
- Wie gross wird die Kandidatenschicht pro Artikel tatsaechlich

**Fertig, wenn:** die Regeln schriftlich fixiert sind, die Stichprobe von Hand
gesichtet ist und der hochgerechnete Speicherbedarf bekannt ist.

### M3 · Volltext-Crawl ⬜
**Woche 3 bis 4 (bis 12.10.)**

447'748 Artikel ab 2010. Abruf, Boilerplate-Filter und Kandidatenextraktion
laufen im selben Prozess, der Volltext wird nach jedem Artikel verworfen (E8).
Laufzeitprotokoll mitschreiben: Durchsatz, Fehlerquote, HTTP-Codes je Jahrgang.
Export nach `data/kandidaten.parquet` und `data/manifest.json` mit Hashes.

**Fertig, wenn:** Abdeckung je Jahrgang >= 95%, die Fehlschlaege kategorisiert sind,
das Manifest prueft und stichprobenartig belegt ist, dass kein Volltext auf Platte
zurueckgeblieben ist.

### M4 · Keyphrase-Pipeline ⬜
**Woche 4 bis 6 (bis 26.10.) · das inhaltliche Herzstueck**

Das ist der Punkt, an dem das Altprojekt scheiterte: die Extraktion war weder
bestaendig noch einheitlich. Belege aus den Altdaten: `kanton` und `kantone`
stehen als zwei Knoten nebeneinander, und unter den 15 haeufigsten Begriffen
finden sich `news`, `push` und `whatsapp`, also Redaktions-Boilerplate.

Stufen der neuen Pipeline. Stufe 1 laeuft bereits im Crawl (M3), die Stufen 2
bis 5 arbeiten auf der gespeicherten Kandidatenschicht und sind daher beliebig
oft wiederholbar, `src/keyphrases.py`:

1. **Kandidaten** (im Crawl, M3): spaCy mit NER (PER, ORG, LOC, MISC) liefert
   Mehrwortentitaeten als Einheit, der Dependency-Parser liefert Nominalphrasen
   fuer Themen ohne Entitaetsstruktur
2. **Normalisierung**: Lemmatisierung des Kopfnomens, Kleinschreibung nur bei
   Nicht-Entitaeten, Entfernen von Artikeln und Praepositionen am Phrasenrand
3. **Alias-Aufloesung**: „Federer“, „Roger Federer“ und „R. Federer“ werden auf
   eine kanonische Form abgebildet. Regel: laengste beobachtete Form innerhalb
   derselben Entitaetsklasse gewinnt, Nachnamen werden nur zusammengefuehrt, wenn
   sie im Korpus eindeutig sind
4. **Stoppliste**: redaktionelles Boilerplate, Wochentage, Monate, Zaehlwoerter
5. **Ranking**: pro Artikel die *k* staerksten Phrasen nach c-TF-IDF

**Fertig, wenn:** auf einer vom Team annotierten Stichprobe von 100 Artikeln
Precision und Recall gemessen sind, die Zahlen im Notebook stehen und die drei
Altprobleme nachweislich weg sind: getrennte Namensteile, Singular-Plural-Dubletten,
Boilerplate unter den Top-Begriffen.

### M5 · EDA und Datenvalidierung ⬜
**Woche 6 bis 7 (bis 02.11.)**

Rubrikkriterium 1: Missing Values, Verteilungen, Plausibilitaetspruefungen und
der Abgleich mit der Quelle. Enthaelt den Vergleich alte gegen neue Extraktion
als Beleg, dass der Neubau noetig war.

**Fertig, wenn:** `src/01_eda.ipynb` fehlerfrei durchlaeuft und die
Ground-Truth-Validierung gegen 20min.ch mit n >= 60 dokumentiert ist.

### M6 · Netzwerkkonstruktion ⬜
**Woche 7 bis 9 (bis 16.11.)**

`src/network.py`:

- bipartiter Artikel-Keyphrase-Graph als Zwischenschritt (LE3, wird mitanalysiert)
- One-Mode-Projektion, Kantengewicht zunaechst Kookkurrenzzahl
- Normalisierung per Salton-Kosinus. **Ohne diesen Schritt ist das Netz unbrauchbar**:
  auf den Altdaten ergab die rohe Kookkurrenz der Top-1200-Begriffe eine Dichte
  von 0.343, nach Normalisierung und Mutual-10-NN 0.0046
- Sparsifizierung, Verfahren siehe Fragekatalog F3
- 16 Jahresnetze 2010 bis 2025 mit identischem globalem Vokabular
- Knotenattribute: dominantes Ressort, Dokumentfrequenz, Erstauftrittsjahr, Entitaetsklasse
- Export nach `graphen/*.gexf` fuer Gephi (LE2)

**Fertig, wenn:** Unit-Tests fuer Projektion, Gewichtung und Sparsifizierung gruen
sind und die Kennzahlen der 16 Jahresnetze tabelliert vorliegen.

### M7 · Analysen und Hypothesentests ⬜
**Woche 9 bis 13 (bis 14.12.)**

Siehe Abschnitte 5 und 6.

### M8 · Abgabepaket ⬜
**Woche 13 bis 15 (bis 03.01.2027)**

| Teil | Hinweis |
|---|---|
| Meilenstein | aus M1, ausgefuellt |
| Praesentation | aufgezeichnet, **maximal 30 Minuten**, alles danach wird nicht mehr bewertet. Ablauf: Datenbeschaffung, EDA, Modellierung, Netzwerkanalyse, Ausblick, Lessons Learned |
| Source | Scraper, Pipeline, Notebooks, aufgeraeumt und dokumentiert |
| Rohdaten | Ausgaben des Crawls |
| Graphen | `.gexf` und CSV-Export |
| **KI-Deklaration mit Prompts** | **Fehlt sie, ist die Note fuer die ganze Gruppe eine 1.** Ab sofort mitschreiben, nicht rekonstruieren |

**Fertig, wenn:** das Paket ueber MS Teams abgegeben ist. Ein anderer Abgabeweg
kostet bis zu 0.2 Notenpunkte.

### Q · Pruefungsvorbereitung 🟡
**laufend bis 04.11.2026**

Stoff ab LE3, Orientierung an den Uebungen, erlaubt sind ein beidseitig
beschriebenes A4-Blatt und die gestellte Formelsammlung. Von Hand rechnen koennen:
Girvan-Newman, Label Propagation, Zentralitaetsmasse, Netzwerk-Zentralisierung,
Pearson und Spearman, Link-Prediction-Indizes, Graphlet Degree Vectors.

---

## 4. Zielbild des Netzwerks

```
Two-Mode (Zwischenschritt, LE3)          One-Mode (Analysegegenstand)

  Artikel        Keyphrase                    Keyphrase
   [A1] ──────── (roger federer)              (roger federer)
   [A1] ──────── (wimbledon)          ==>      │ w = Salton(A_u, A_v)
   [A2] ──────── (roger federer)              (wimbledon)
   [A2] ──────── (basel)                       │
                                              (basel)
```

- **Knoten:** Keyphrase. Groesse in der Darstellung = Zentralitaetsmass,
  Dokumentfrequenz als separates Attribut
- **Kante:** zwei Keyphrasen kommen im selben Artikel vor
- **Kantengewicht:** Salton-Kosinus ueber die Artikelmengen, nicht die rohe Anzahl
- **Achtung, strukturelles Artefakt:** jeder Artikel erzeugt eine Clique ueber
  seine Keyphrasen. Der Clustering-Koeffizient ist dadurch systematisch erhoeht,
  Dreiecke sind nicht unabhaengig. Das gehoert offengelegt und gegen ein
  Nullmodell gestellt, sonst ist es ein Angriffspunkt in der Bewertung

---

## 4a. Kandidatenschicht statt Volltextarchiv

Der Volltext wird nicht gespeichert (E8). Damit trotzdem nicht bei jeder
Aenderung an der Extraktion neu gecrawlt werden muss, wird die Pipeline an einer
Stelle aufgetrennt, die selten wechselt:

```
teuer, einmalig                      billig, beliebig oft wiederholbar
┌──────────────────────────┐         ┌────────────────────────────────┐
│ HTTP-Abruf               │         │ Lemmatisierung                 │
│ Boilerplate-Filter       │  ────►  │ Alias-Aufloesung               │
│ spaCy NER + Noun-Chunks  │  KAND.  │ Stoppliste                     │
│ Volltext danach verworfen│         │ Ranking, Vokabularauswahl      │
└──────────────────────────┘         └────────────────────────────────┘
```

**Gespeichert wird pro Artikel:** jede gefundene Kandidatenphrase in ihrer
Oberflaechenform, mit Entitaetslabel (PER, ORG, LOC, MISC oder NOUN_CHUNK),
Haeufigkeit im Artikel und der Angabe, ob sie im Titel oder Lead stand.

| | Volltextarchiv | Kandidatenschicht |
|---|---|---|
| Speicher | rund 1.3 GB | rund 200 bis 300 MB |
| Neu-Crawl noetig bei geaenderter Stoppliste, Alias-Regel, Ranking, Vokabulargroesse | ja | **nein** |
| Neu-Crawl noetig bei geaendertem spaCy-Modell oder geaenderten Kandidatenregeln | nein | ja |

**Daraus folgt eine harte Reihenfolge:** die Kandidatenregeln und das spaCy-Modell
muessen **vor** dem Vollcrawl festgezurrt sein. Dafuer gibt es den Pilotlauf in M2b.
Wird das uebersprungen, kostet jeder Fehler in den Kandidatenregeln einen zweiten
Crawl ueber 448'000 Artikel.

**Annahme, bitte widersprechen falls falsch:** Titel, Lead und Ressort bleiben
gespeichert. Sie stehen ohnehin schon in den Altdaten, sind klein, und ohne sie
lassen sich im Notebook keine konkreten Artikelbeispiele zeigen und keine
Ground-Truth-Validierung durchfuehren.

---

## 5. Hypothesen

### H1 · Externe Schocks zentralisieren die Themenagenda
**These:** In Krisenjahren laufen sonst getrennte Themenfelder im Krisenkomplex
zusammen. Erwartet werden Maxima der Zentralisierung und Minima der Modularitaet
2020 (Covid) und 2022 (Ukraine).
**Messung:** 16 Jahresnetze, identisches Vokabular. Freeman-Zentralisierung C_D
und C_B, Louvain-Modularitaet Q ueber 10 Seeds mit Streuung.
**Test:** Krisenjahre gegen die Verteilung der uebrigen Jahre, Bootstrap-Konfidenzintervall.
**Deckt ab:** LE4, LE6.

### H2 · Ressorts sind semantische Silos
**These:** Begriffe bleiben ueberwiegend in ihrem Ressort, nur wenige Begriffe
verbinden Themenwelten und schliessen strukturelle Loecher.
**Messung:** dominantes Ressort je Keyphrase als Knotenattribut, nominale
Assortativitaet nach Newman, Betweenness und Burt Constraint fuer die Brueckenbegriffe.
**Test:** Label-Permutation bei fester Topologie (B = 5'000), zusaetzlich QAP mit
gemeinsamer Zeilen- und Spaltenpermutation.
**Deckt ab:** LE5, LE7.

### H3 · Neue Themenverbindungen sind vorhersagbar
**These:** Neue Assoziationen entstehen eher ueber gemeinsame Dritte als ueber
Popularitaet, Adamic-Adar schlaegt also Preferential Attachment.
**Messung:** rollierende Zeitfenster, zum Beispiel 2010 bis 2019 auf 2020, dann
fortlaufend. Common Neighbors, Jaccard, Adamic-Adar, Preferential Attachment,
Zufallsbaseline.
**Test:** PR-AUC und Precision@k, Unterschiede ueber 1'000 Bootstrap-Resamples.
**Deckt ab:** LE8.

---

## 6. Abdeckung der Lernergebnisse

| LE | Gewicht | Abdeckung | Meilenstein |
|---|---|---|---|
| LE1 Soziologie und Anwendungsfaelle | 11% | theoretische Verankerung ueber Network Agenda Setting und semantische Netzwerkanalyse in der Kommunikationsforschung | M1, M8 |
| LE2 Tools | 10% | Gephi-Layouts und -Filter auf den `.gexf`-Exporten, NetworkX durchgehend | M6 |
| LE3 Modellierung und Filterung | 10% | Two-Mode zu One-Mode, Gewichtungsvarianten, Sparsifizierung, Vokabularfilter | M6 |
| LE4 Communities | 10% | Louvain mit Seed-Stabilitaet, Cliquen, k-Core, Giant Component | M7, H1 |
| LE5 Zentrale Aktoren | 10% | Degree, Betweenness, Closeness, Burt Constraint und Effective Size | M7, H2 |
| LE6 Netzwerk-Kennzahlen | 10% | Dichte, Durchmesser, Pfadlaenge, Clustering, C_D und C_B ueber 16 Jahre, Connectivity, Artikulationspunkte | M7, H1 |
| LE7 Statistik | 10% | Assortativitaet mit Permutationstest, QAP, Nullmodelle | M7, H2 |
| LE8 Link Prediction | 10% | fuenf Verfahren, rollierende Fenster, PR-AUC mit Bootstrap | M7, H3 |
| LE9 Diffusion | 10% | offen, siehe Fragekatalog F8 | M7 |
| LE10 Graphlets | 10% | offen, siehe Fragekatalog F9 | M7 |

Die Vielfalt der Analysen ist im Raster mit Gewicht 2 das schwerste Kriterium.
Mit nur einem Netzwerkmodell entsteht die Vielfalt ueber: den bipartiten Graphen
zusaetzlich zur Projektion, 16 Jahresschnitte, und Teilnetze je Ressort.

---

## 7. Fragekatalog fuer das Team

Diese Punkte sind noch offen. Antworten bitte direkt hier eintragen.

| Nr | Frage | Warum es zaehlt | Antwort |
|---|---|---|---|
| F1 | Wie gross soll das Vokabular sein: feste Top-N Knoten oder alle Phrasen ab einer Mindest-Dokumentfrequenz? | Bestimmt Knotenzahl und ob Gephi noch handhabbar bleibt. Im Altbestand: 14'084 Begriffe ab 10 Artikeln, 1'784 ab 100 | |
| F2 | Jahresnetze oder feinere Zeitschnitte, etwa Quartale? | 16 Jahre reichen fuer H1, Quartale wuerden Schockwirkungen schaerfer zeigen, vervierfachen aber die Rechenzeit | |
| F3 | Sparsifizierung per Mutual k-NN oder per Disparity-Filter (Backbone)? | k-NN haelt die Dichte ueber Jahre vergleichbar, der Backbone ist statistisch besser begruendbar | |
| F4 | Alias-Aufloesung rein heuristisch oder zusaetzlich gegen Wikidata? | Wikidata bringt echte Entitaetsidentitaet, kostet aber einen weiteren Abgleichsschritt und eine Offline-Kopie | |
| F5 | Dominantes Ressort je Keyphrase: wie wird ein Gleichstand aufgeloest? | Muss deterministisch sein, sonst ist H2 nicht reproduzierbar | |
| F6 | Wer annotiert die 100 Artikel der Ground-Truth-Stichprobe, nach welcher schriftlichen Regel? | Ohne vorab festgelegte Regel sind Precision und Recall wertlos | |
| F7 | Gruppennummer und Abgabeweg geklaert? | Abgabe nicht ueber MS Teams kostet bis zu 0.2 Notenpunkte | |
| F8 | LE9 Diffusion mitnehmen? | Auf einem semantischen Netz ist Ansteckung eine Metapher, keine echte Ausbreitung. Entweder sauber als Simulation deklarieren oder bewusst weglassen und im Ausblick begruenden | |
| F9 | LE10 Graphlets mitnehmen? | Im Altprojekt bewusst ausgelassen. Waere ein Zugewinn beim Kriterium Vielfalt | |
| F10 | Aufgabenteilung Elias und Luca? | Der Dozent erwartet eine erkennbare Zusammenarbeit | |
| F11 | Wie werden die KI-Prompts ab sofort mitgeschrieben? | Fehlende Deklaration bedeutet Note 1 fuer die ganze Gruppe. Rekonstruktion am Schluss funktioniert erfahrungsgemaess nicht | |
| F12 | Duerfen Titel, Lead und Ressort gespeichert bleiben? | Ohne sie sind keine Artikelbeispiele im Notebook und keine Ground-Truth-Validierung moeglich. Annahme im Plan: ja | |
| F13 | Welches spaCy-Modell, `sm`, `md` oder `lg`? | Wird in M2b entschieden und ist danach fixiert, weil eine Aenderung einen zweiten Vollcrawl bedeutet | |

---

## 8. Blocker

🔴 **Termin-Widerspruch.** `docs/SAN-Projektbeschreibung.pdf` nennt als
Abgabetermin Freitag, 31.05.2026. Dieses Datum liegt in der Vergangenheit und
stammt aus dem vorherigen Semester. `docs/SAN-portrait.md` nennt Sonntag,
03.01.2027. Dieser Plan folgt dem Portrait. **Beim Dozenten bestaetigen lassen.**

🟡 **Abgabeordner „Rohdaten“ gegen E8.** Die Projektbeschreibung verlangt einen
Ordner `Rohdaten` und empfiehlt ausdruecklich, die Rohdaten zu persistieren, damit
bei Anpassungen der Transformation nicht neu eingesammelt werden muss. Da der
Volltext bewusst nicht aufbewahrt wird, tritt an seine Stelle: die URL-Datum-Liste,
die Kandidatenschicht und das Manifest. **Das ist in der Praesentation und im
Meilenstein-Dokument aktiv zu begruenden**, sonst liest es sich wie eine Luecke.

🟡 **Spaces nicht abgezogen.** `spaces.informatik.fhnw.ch` verlangt eduID-SSO.
Der Browser-Tab ist offen, aber nicht angemeldet (`auth.user: null`). Dieser Plan
stuetzt sich daher auf die lokalen Unterlagen in `docs/`, die inhaltlich
vollstaendig sind und die aktuellen Semestertermine enthalten. **Nach dem Login
nachziehen**, um zu pruefen, ob der Space Zusaetzliches enthaelt.

---

## 9. Artefakte

| Pfad | Inhalt | Stand |
|---|---|---|
| `data/20min_artikel_sortiert.csv` | 449'180 URL-Datum-Paare, 2003 bis 2025 | ✅ vorhanden, im Hauptcheckout |
| `data_extraction/get_data.py` | Sitemap-Crawler, Vorlage fuer v2 | ✅ vorhanden |
| `data_extraction/handle_data.py` | alte Extraktion | ⬜ wird ersetzt (M2, M4) |
| `data/kandidaten.parquet` | Kandidatenschicht, Ergebnis von M3 | ⬜ noch nicht erzeugt |
| `src/00_beispiel_netzwerk.py` | Illustration Two-Mode zu One-Mode aus fuenf echten Artikeln | ✅ erzeugt 2026-09-17 |
| `out_plots/beispiel_5artikel_10keywords.png` | dazugehoerige Abbildung | 🟡 Panel A und C brauchen noch ein Layout-Fix |
| `docs/` | Portrait, Projektbeschreibung, Bewertungsraster, Skript | ⬜ noch in den Worktree zu uebernehmen |

---

## 10. Gemessene Ausgangslage

Alle Zahlen am 2026-09-17 auf den Altdaten gemessen, nicht geschaetzt:

| Groesse | Wert |
|---|---|
| Artikel gesamt | 449'177 mit gueltigem Datum |
| Artikel ab 2010 | 447'748, pro Jahr zwischen 20'034 und 36'110 |
| Abdeckung Titel, Lead, Ressort | 100% in jedem Jahrgang |
| Volltext in den Altdaten | **nicht vorhanden**, daher E3. Wird auch kuenftig nicht archiviert (E8) |
| Volltext heute abrufbar | 8 von 8 Stichproben, rund 0.4s pro Artikel |
| Eindeutige Begriffe (alte Extraktion, ab 2020) | 118'849, davon 1'784 in mindestens 100 Artikeln |
| Rohe Kookkurrenz, Top-1200, ab 2020 | 246'541 Kanten, Dichte 0.343 |
| Nach Salton und Mutual-10-NN | 3'282 Kanten, Dichte 0.0046, Giant Component 94.7%, Louvain Q = 0.858 |

Die letzte Zeile ist der Beleg, dass das Modell traegt: 24 Communities, thematisch
lesbar (Corona, Ukraine-Krieg, Sport, Polizei und Justiz, Verkehrsunfaelle).

---

## 11. Naechster Schritt

**Einer:** Fragekatalog in Abschnitt 7 beantworten, mindestens F1, F3, F6 und F13,
weil M2 und M4 sonst auf ungeklaerten Annahmen aufsetzen. F13 ist seit E8 nicht
mehr nachtraeglich korrigierbar.
