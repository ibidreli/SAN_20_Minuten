# ROADMAP: SAN-Projekt 20 Minuten

**Stand:** 2026-11-12 · **Team:** Elias, Luca · **Modul:** Soziale Netzwerkanalyse (SAN), FHNW

Grundlagen dieser Roadmap:

- `docs/SNA-Projektbeschreibung-1769855081.pdf` (Aufgabenstellung, Abgaben, Präsentationsablauf)
- `docs/main.pdf` (Skript „Soziale Netzwerkanalyse“, M. Henninger, v3.8.1)
- der bisherige Plan aus `STATUS.md` (gelöscht, abrufbar mit `git show HEAD:STATUS.md`)
- der aktuelle Code in `data_extraction/`

---

## 1. Was die Aufgabenstellung verlangt

| Teil | Anforderung | Quelle |
|---|---|---|
| Thema & Daten | frei gewählt, öffentlich verfügbar; **eigener Crawler gibt Bonuspunkte** | Projektbeschreibung S. 2 |
| Rohdaten | „Rohdaten persistieren“, damit Transformationen ohne Neu-Abruf wiederholbar sind | S. 2 |
| EDA | Häufigkeiten, Statistiken, Visualisierungen, Missing Values, **Plausibilitätsprüfung gegen die Quelle per Stichprobe**; Empfehlung: Pandas Profiling / Sweetviz. Schwach gewichtet | S. 2 |
| Netzwerkanalyse | **verschiedene** Analysen aus dem Unterricht; zusätzliche erlaubt | S. 2 |
| Meilenstein | kurz und klar: Datenquelle, Team, Hindernisse, geplante Analysen; **vor der Umsetzung** einreichen, Feedback schriftlich | S. 3 |
| Präsentation | aufgezeichnet, **max. 30 Min.** (danach wird nichts bewertet). Ablauf: 1 Datenbeschaffung · 2 EDA · 3 Modellierung · 4 SNA · 5 Ausblick · 6 Lessons Learned. Immer sagen, **in welcher Datei / welchem Notebook** etwas umgesetzt ist | S. 3–4 |
| Interpretation | Zahlen und Grafiken **ohne Bezug zum Anwendungsfall** werden ignoriert oder wirken negativ | S. 4 |
| Abgabeordner | `Meilenstein/`, `Präsentation/`, `Source/`, `Rohdaten/`, `Graphen/` in MS Teams → „Allgemein“ → „Gruppenarbeiten“ → `<Gruppennr>_<Titel>` | S. 3 |
| Code | keine separate Doku nötig, aber Code und Notebooks **dokumentiert und aufgeräumt** | S. 3 |
| KI | KI ohne Deklaration **und Angabe der Prompts** → **Note 1 für die ganze Gruppe** | S. 4 |
| Schlussgespräch | ca. 15 Min., auf Verlangen des Dozenten | S. 3 |

### Abdeckung aus dem Skript (Analyse-Werkzeugkasten)

| Kapitel | Thema | Geplante Nutzung |
|---|---|---|
| 3 | One-/Two-Mode, Projektionen (gewichtet, **Newman's Weighted Projection**, Overlap) | Artikel–Keyphrase → Keyphrase–Keyphrase |
| 4 | Reduktion: Local/Global/Contextual View, Ego-Netz, Filter auf Kantenattributen | Vokabular- und Kantengewichtsfilter, Ego-Netze z. B. „Corona“ |
| 5 | Components, Cliquen, k-Core, Edge-Betweenness, Label Propagation, Louvain | Themencluster je Jahr |
| 6–7 | Zentralitäten, Gruppenzentralität, Zentralisierung | zentrale Begriffe, Agenda-Konzentration |
| 8–9 | Dichte, Durchmesser, Clustering, Connectivity | Jahresvergleich |
| 10 | Korrelation, Assortativität (numerisch/kategorisch) | Ressort-Assortativität |
| 11 | Referenznetzwerke, Hypothesentests (monadisch, dyadisch/QAP, Metriken) | H1, H2 |
| 12 | Link Prediction (CN, Jaccard, RA, Adamic-Adar, PA) und Evaluation | H3 |
| 13 | Diffusion (ICM, Voter, Threshold) | optional, siehe Entscheid E-D |
| 14 | Graphlets (RGF-Distanz, GDV) | optional, Jahresnetze vergleichen |

---

## 2. Wo wir stehen

| Bereich | Stand |
|---|---|
*Aktualisiert am 12.11.2026 abends.*

| Bereich | Stand |
|---|---|
| URL-Liste | ✅ `data/20min_artikel_sortiert.csv`, 477'487 Artikel, 01.10.2003 bis 12.11.2026 (`get_data.py`) |
| Parser | ✅ aktuelles Layout: Reaktionen aus `__NEXT_DATA__`, Autoren mit Kürzel/ID, Quellenkürzel, Textlänge, Format (Artikel/Ticker), Aktualisierung. Test 2020–2026: 698/700 erfolgreich |
| Pilot | ✅ 1'000 Artikel 2003–2026 und 700 Artikel 2020–2026, Fehler analysiert und behoben |
| Vollcrawl | 🟡 **läuft**: 166'212 Artikel 01.01.2020 bis 05.11.2026 (`data/input_ab_2020.csv`), ca. 11 h, ca. 4 GB |
| Keywords (Lemma, Alias, Stoppliste, TF-IDF) | ✅ `data_extraction/keywords.py`, Top 8 pro Artikel + Ressort-Stufen |
| Personen (Namen/Kürzel/ID zusammenführen) | ✅ `data_extraction/autoren.py` |
| Analyse-Code | ✅ `src/daten.py`, `src/netzwerk.py`; Notebooks `src/01_eda`, `02_keyword_netz`, `03_autoren_netz`, an einer Test-DB mit 4'400 Artikeln geprüft |
| Umgebung | ✅ `requirements.txt` vollständig |
| Meilenstein-Dokument | 🟡 Entwurf `docs/Meilenstein.md`, **noch nicht eingereicht** |
| KI-Deklaration | 🟡 `docs/KI-Deklaration.md` + Prompt-Log `docs/KI-Prompts.md` (`scripts/ki_prompts.py`); Lucas Teil und „Eigenleistung“ fehlen |
| Interpretation, Präsentation | ⬜ offen, nach dem Vollcrawl |

**Wichtige Befunde aus den Tests** (Details in `data_extraction/README.md` und `src/01_eda.ipynb`):

- **Reaktionen erst ab Juni 2020** gemessen. Vorher liefert die Quelle 0 Likes/Shares und keine Kommentare, deshalb gelten sie als fehlend (`daten.REAKTIONEN_AB`).
- `views` ist unplausibel und wird nicht verwendet. Liveticker verzerren die Reaktionen.
- 2020 stehen in der Byline fast nur Kürzel. Auf der Test-DB ist gut die Hälfte aufgelöst, auf dem Vollbestand werden es mehr.

---

## 3. Offene Entscheide (zuerst klären)

| Nr | Frage | Empfehlung | Warum jetzt |
|---|---|---|---|
| E-A | **Abgabetermin bestätigen.** Die PDF nennt *Fr 31.5.2026* (offensichtlich Vorlage aus dem Frühlingssemester), der alte Plan *So 03.01.2027*. | Beim Dozenten im Gruppenchat bestätigen lassen | Davon hängt der ganze Zeitplan unten ab |
| E-B | ~~Vollcrawl oder Stichprobe?~~ | ✅ **Entschieden:** Vollbestand ab 2020 (166k Artikel, 7 Jahresnetze). Grund: Reaktionen und Autoren-IDs gibt es erst im neuen CMS | — |
| E-C | **Rohdaten persistieren?** Die Aufgabe empfiehlt es, der Plan (E8) verwirft den Volltext. | Kandidatenschicht + Titel/Lead/Ressort als „Rohdaten“ abgeben und in der Präsentation begründen (Urheberrecht 20min) | Muss vor dem Crawl feststehen |
| E-D | Diffusion (Kap. 13) und Graphlets (Kap. 14) mitnehmen? | **Graphlets ja** (GDV/RGF-Distanz zum Vergleich der Jahresnetze, gut begründbar). Diffusion nur als klar deklarierte Simulation oder im Ausblick | „Vielfalt der Analysen“ ist stark gewichtet |
| E-E | Projektionsgewicht | Newman's Weighted Projection (aus dem Skript) **und** Salton-Kosinus vergleichen, eine als Hauptvariante wählen | Kap. 3 explizit; Vergleich ist selbst eine LE3-Leistung |
| E-F | Aufgabenteilung Elias / Luca | z. B. Elias: Daten, Pipeline, EDA · Luca: Netzwerk, Analysen; Präsentation gemeinsam | Zusammenarbeit muss erkennbar sein |

---

## 4. Roadmap

Annahme: Abgabe **So 03.01.2027** (E-A). Ab heute bleiben **7 Wochen**.

### Phase 0 · Sofort (bis So 15.11.)

- [ ] **Gruppennummer und Teams-Chat** „SAN-Projekt – Gruppe xx“ mit Dozent prüfen; E-A klären
- [x] KI-Deklaration angelegt: `docs/KI-Deklaration.md`, Prompt-Log `docs/KI-Prompts.md` (`python scripts/ki_prompts.py`)
- [ ] KI-Deklaration: Lucas Prompts ergänzen, Abschnitt „Eigenleistung“ ausfüllen, nach jeder Sitzung Skript erneut ausführen
- [ ] **Meilenstein einreichen:** Entwurf `docs/Meilenstein.md` prüfen, Gruppennummer ergänzen, abgeben
- [x] Umgebung: `de_core_news_lg` installiert, `requirements.txt` vollständig

### Phase 1 · Pilot und Crawl (bis 15.11.)

- [x] Pilot 1'000 Artikel 2003–2026 und 700 Artikel 2020–2026; Fehler kategorisiert und behoben
- [x] Parser und Kandidatenregeln eingefroren (Branch `feat/extraction-quality`)
- [ ] Vollcrawl 2020–2026 abschliessen, dann `--retry-failed`; Laufprotokoll (Start, Ende, done/failed, Python- und spaCy-Version) in der README
- [ ] Nach dem Crawl: `python -m data_extraction.keywords --db data/articles.sqlite` und `python -m data_extraction.autoren --db data/articles.sqlite`

**Fertig, wenn:** Abdeckung ≥ 95 % pro Jahr und die Fehlschläge kategorisiert sind.

### Phase 2 · Keywords und Personen (16.–22.11.)

- [x] Keyword-Schicht `data_extraction/keywords.py`: Grundform, Alias-Auflösung, Stoppliste, TF-IDF mit Titel-/Lead-/Namensbonus, Top 8 pro Artikel
- [x] Personen-Schicht `data_extraction/autoren.py`: Namen, Kürzel und IDs zu Personen zusammenführen
- [ ] Auf dem Vollbestand nachjustieren: Stoppliste (Top 200 Keywords durchsehen), `--top-k`, `--min-df`
- [ ] Qualitätscheck: 50 Artikel von Hand bewerten, Precision@8 angeben; Anteil aufgelöster Kürzel pro Jahr

### Phase 3 · EDA (16.–29.11.)

`src/01_eda.ipynb` (Code fertig, auf Test-DB geprüft):

- [x] Abdeckung, fehlende Werte, Ressorts, Textlänge, Reaktionen, Aktualisierungen, Autoren, Agenturen, Keywords, Long Tail
- [x] Vergleich mit der alten CSV, Massnahmentabelle
- [ ] Auf dem Vollbestand ausführen und die Massnahmentabelle mit den echten Zahlen abgleichen
- [ ] Plausibilitätsstichprobe `data/plausibilitaet_stichprobe.csv` (40 Artikel) von Hand gegen 20min.ch prüfen
- [ ] Optional Sweetviz/ydata-profiling-Report

### Phase 4 · Netzwerkkonstruktion (23.11.–06.12.)

`src/netzwerk.py` + `src/02_keyword_netz.ipynb` + `src/03_autoren_netz.ipynb` (Code fertig, auf Test-DB geprüft):

- [x] Two-Mode Artikel–Keyword und Artikel–Person, Projektionen mit Kookkurrenz, Newman und Salton
- [x] k-NN-Backbone, Knotenattribute (Ressort, df, Typ, erstes Jahr, Likes-/Kommentar-Median), Export `Graphen/*.gexf` + CSV
- [x] Nullmodell gegen das Clique-Artefakt, Kennzahlentabelle
- [ ] Schwellen (`MIN_DF`, `MIN_ANZAHL`, `BACKBONE_K`) auf dem Vollbestand festlegen und begründen
- [ ] Visualisierung in **Gephi** (Layout, Louvain-Färbung, Filter) → Screenshots für die Präsentation

### Phase 5 · Analysen und Hypothesentests (07.–20.12.)

In `src/02_keyword_netz.ipynb` und `src/03_autoren_netz.ipynb` (Code vorhanden). Jede Analyse mit **Frage → Methode → Resultat → Interpretation für 20 Minuten**.

| | These | Methode (Skript-Kapitel) | Test |
|---|---|---|---|
| **H1** | Krisenjahre (2020 Covid, 2022 Ukraine) zentralisieren die Agenda | Degree-/Betweenness-Zentralisierung, Louvain-Modularität über Seeds (Kap. 5, 7) | Krisenjahre vs. Verteilung der übrigen Jahre, Referenznetze (Kap. 11.3.4) |
| **H2** | Ressorts sind semantische Silos, wenige Brückenbegriffe | kategorische Assortativität nach Ressort, Betweenness, Structural Holes / Burt (Kap. 1.5.2, 6, 10.4) | Label-Permutation, QAP (Kap. 11.3.2–11.3.3) |
| **H3** | Neue Themenverbindungen sind vorhersagbar, Adamic-Adar > Preferential Attachment | CN, Jaccard, RA, AA, PA auf Zeitfenstern (Kap. 12) | Precision@k / AUC, Bootstrap |
| **H4** | Die Redaktion arbeitet in ressortgebundenen Teams; Themencluster unterscheiden sich in den Reaktionen | Co-Autorennetz, Autoren-Themennetz (Kosinus), Louvain, Assortativität; Reaktions-Mediane pro Community (ab Juni 2020) | Permutationstest |

Ergänzend für die Vielfalt:

- [ ] Zentrale Begriffe pro Jahr (Degree, Betweenness, Eigenvector) und deren Wandel
- [ ] Communities: Louvain vs. Label Propagation, k-Core des Themenkerns
- [ ] Ego-Netze ausgewählter Begriffe (z. B. „Corona“, „SVP“, „Klima“) im Zeitverlauf
- [ ] Graphlets: RGF-Distanz zwischen Jahresnetzen (E-D)
- [ ] Optional: Diffusion als deklarierte Simulation (E-D)

### Phase 6 · Abgabe (21.12.–03.01.)

- [ ] Code aufräumen und kommentieren; Notebooks von oben nach unten fehlerfrei ausführbar
- [ ] README: Ablauf von URL-Liste bis Grafiken in wenigen Befehlen
- [ ] **Präsentation** aufnehmen (≤ 30 Min., Ziel 25): Datenbeschaffung (inkl. Validierung) · EDA + Massnahmen · Modellierung (Knoten, Kanten, Two→One-Mode, Gewichte, Attribute) · SNA mit Interpretation · Ausblick · Lessons Learned. Bei jeder Analyse die Datei nennen
- [ ] Abgabeordner in MS Teams: `Meilenstein/`, `Präsentation/`, `Source/`, `Rohdaten/`, `Graphen/`, dazu die **KI-Deklaration mit Prompts**
- [ ] Vorbereitung Schlussgespräch: jede Methode erklären und jede Zahl begründen können

---

## 5. Zeitplan auf einen Blick

| KW | Datum | Phase | Ergebnis |
|---|---|---|---|
| 46 | 12.–15.11. | 0 Sofort, 1 Crawl | Meilenstein eingereicht, Termin bestätigt, Vollcrawl fertig |
| 47 | 16.–22.11. | 2 Keywords/Personen | Keywords und Personen auf dem Vollbestand justiert |
| 48 | 23.–29.11. | 3 EDA | `01_eda.ipynb` mit echten Zahlen, Stichprobe geprüft |
| 49 | 30.11.–06.12. | 4 Netzwerk | `.gexf`-Dateien, Kennzahlentabelle, Gephi-Bilder |
| 50–51 | 07.–20.12. | 5 Analysen | H1–H3 mit Tests und Interpretation |
| 52–1 | 21.12.–03.01. | 6 Abgabe | Präsentation aufgenommen, Paket in Teams |

Puffer: Phase 5 kann auf H1 + H2 + Zentralitäten/Communities reduziert werden, falls Phase 1 oder 2 länger dauert. H3 und Graphlets sind die ersten Kandidaten zum Streichen.

---

## 6. Risiken

| Risiko | Gegenmassnahme |
|---|---|
| Parser scheitert an Layouts | ✅ Pilot 2003–2026 gelaufen; Zeitraum ab 2020 hat ein einheitliches CMS |
| 20min.ch blockiert / drosselt | User-Agent gesetzt, Backoff vorhanden; Workers niedrig halten, über Nacht laufen lassen |
| Keyphrases zu verrauscht → Netz unbrauchbar | Stoppliste und Ranking iterativ auf der Kandidatenschicht, kein Neu-Crawl nötig |
| Projektionsnetz zu dicht (Altdaten: Dichte 0.34) | Normalisierung + Sparsifizierung, Filter in der Präsentation erklären |
| Analysen ohne Interpretation | Pro Grafik ein Satz „Was heisst das für die 20-Minuten-Berichterstattung?“ |
| Fehlende KI-Deklaration | Ab sofort mitschreiben, nicht am Schluss rekonstruieren |
