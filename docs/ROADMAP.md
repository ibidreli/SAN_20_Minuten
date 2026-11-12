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
| URL-Liste | ✅ `data/20min_artikel_sortiert.csv`, 449'190 Artikel, 01.10.2003 bis 25.09.2025 (`get_data.py`) |
| Scraper / Kandidatenschicht (F01) | ✅ implementiert in `data_extraction/` (SQLite, Wiederaufnahme, spaCy NER + Noun-Chunks). **Noch nie gegen 20min.ch gelaufen.** |
| Umgebung | 🟡 `.venv` vorhanden, aber **`de_core_news_lg` nicht installiert**; `networkx`, `pandas`, `matplotlib` fehlen in `requirements.txt` |
| Meilenstein-Dokument | 🔴 **nicht eingereicht** (war für Ende September geplant) |
| Pilotlauf, Vollcrawl | ⬜ offen |
| Keyphrase-Normalisierung (Lemma, Alias, Stoppliste, Ranking) | ⬜ offen, kein Code |
| EDA, Netzwerk, Analysen, Präsentation | ⬜ offen, `src/` ist leer |
| KI-Deklaration | ⬜ kein Prompt-Log im Repo |

**Was F01 heute liefert:** pro Artikel rohe Kandidaten (`phrase`, `label` ∈ PER/ORG/LOC/MISC/NOUN_CHUNK,
`count`, `in_titel`, `in_lead`). Das sind **noch keine Keywords**: keine Lemmatisierung, keine Stoppwörter,
kein Ranking. „die Mieter“ und „Mieter“ sind zwei Kandidaten. Die Keyword-Bildung ist Phase 3.

---

## 3. Offene Entscheide (zuerst klären)

| Nr | Frage | Empfehlung | Warum jetzt |
|---|---|---|---|
| E-A | **Abgabetermin bestätigen.** Die PDF nennt *Fr 31.5.2026* (offensichtlich Vorlage aus dem Frühlingssemester), der alte Plan *So 03.01.2027*. | Beim Dozenten im Gruppenchat bestätigen lassen | Davon hängt der ganze Zeitplan unten ab |
| E-B | **Vollcrawl oder Stichprobe?** Vollcrawl ≈ 10 h Laufzeit, ≈ 9 GB Kandidatenschicht. | **Geschichtete Stichprobe**, z. B. 4'000–5'000 Artikel pro Jahr 2010–2025 (≈ 70k). Reicht für 16 stabile Jahresnetze, Laufzeit < 2 h, < 1.5 GB. Vollcrawl nur, wenn Zeit bleibt | Restzeit ~7 Wochen; ein misslungener Vollcrawl kostet zu viel |
| E-C | **Rohdaten persistieren?** Die Aufgabe empfiehlt es, der Plan (E8) verwirft den Volltext. | Kandidatenschicht + Titel/Lead/Ressort als „Rohdaten“ abgeben und in der Präsentation begründen (Urheberrecht 20min) | Muss vor dem Crawl feststehen |
| E-D | Diffusion (Kap. 13) und Graphlets (Kap. 14) mitnehmen? | **Graphlets ja** (GDV/RGF-Distanz zum Vergleich der Jahresnetze, gut begründbar). Diffusion nur als klar deklarierte Simulation oder im Ausblick | „Vielfalt der Analysen“ ist stark gewichtet |
| E-E | Projektionsgewicht | Newman's Weighted Projection (aus dem Skript) **und** Salton-Kosinus vergleichen, eine als Hauptvariante wählen | Kap. 3 explizit; Vergleich ist selbst eine LE3-Leistung |
| E-F | Aufgabenteilung Elias / Luca | z. B. Elias: Daten, Pipeline, EDA · Luca: Netzwerk, Analysen; Präsentation gemeinsam | Zusammenarbeit muss erkennbar sein |

---

## 4. Roadmap

Annahme: Abgabe **So 03.01.2027** (E-A). Ab heute bleiben **7 Wochen**.

### Phase 0 · Sofort (bis So 15.11.)

- [ ] **Gruppennummer und Teams-Chat** „SAN-Projekt – Gruppe xx“ mit Dozent prüfen; E-A klären
- [ ] **KI-Deklaration ab heute führen:** `docs/KI-Deklaration.md` mit Datum, Tool, Prompt, wofür verwendet. Rückwirkend alles erfassen, was noch auffindbar ist (u. a. die Commits mit Claude-Code-Mitarbeit)
- [ ] **Meilenstein-Dokument schreiben und einreichen** (`docs/Meilenstein.md`, 1–2 Seiten): Titel, Team, Datenquelle und Rechtslage, Modell (Two-Mode Artikel–Keyphrase → One-Mode Keyphrase-Netz), geschätzte Grösse, die drei Hypothesen, bekannte Hindernisse (Layoutwechsel über 15 Jahre, fehlende Like/Share-Daten, Clique-Artefakt der Projektion)
- [ ] Umgebung vervollständigen: `de_core_news_lg` installieren; `networkx`, `pandas`, `matplotlib`, `pyarrow` in `requirements.txt` aufnehmen

### Phase 1 · Pilot und Crawl (16.–22.11.)

- [ ] Geschichtete Pilotstichprobe ziehen (z. B. 100 Artikel pro Jahr 2010–2025) → `data/pilot_input.csv` (Script `scripts/sample_urls.py`)
- [ ] Pilot laufen lassen: `python -m data_extraction.fetch_articles --db data/pilot.sqlite --input data/pilot_input.csv`
- [ ] Pilot prüfen: Fehlerquote pro Jahr, `failed`/`skipped` nach Layout, 20 Artikel von Hand gegen 20min.ch vergleichen (Titel, Lead, Ressort, plausible Kandidaten)
- [ ] Parser nachbessern, falls ältere Jahrgänge scheitern; **Modell und Kandidatenregeln danach einfrieren**
- [ ] Hauptlauf mit der in E-B gewählten Stichprobe starten (über Nacht). Laufprotokoll: Modellversion, Durchsatz, Fehlerquote

**Fertig, wenn:** Abdeckung ≥ 95 % pro Jahr und die Fehlschläge kategorisiert sind.

### Phase 2 · Keyphrase-Pipeline (23.–29.11.) — inhaltliches Herzstück

`src/keyphrases.py`, läuft beliebig oft auf der Kandidatenschicht, ohne Neu-Crawl:

- [ ] **Normalisierung:** Artikel/Präpositionen am Rand entfernen, Kopfnomen lemmatisieren, Kleinschreibung bei Nicht-Entitäten
- [ ] **Alias-Auflösung:** „Federer“ / „Roger Federer“ → eine Form (längste Form pro Entitätsklasse, nur bei eindeutigen Nachnamen)
- [ ] **Stoppliste:** Redaktions-Boilerplate (`news`, `push`, `whatsapp`, …), Wochentage, Monate, Zahlwörter, generische Nominalphrasen
- [ ] **Ranking:** pro Artikel die Top-k Phrasen (TF-IDF / c-TF-IDF, Bonus für `in_titel`/`in_lead`)
- [ ] **Vokabular:** globales Vokabular über alle Jahre (z. B. Dokumentfrequenz ≥ 20), identisch für alle Jahresnetze
- [ ] Qualitätscheck: 50–100 Artikel von Hand annotieren, Precision@k angeben; zeigen, dass die drei Altprobleme weg sind (getrennte Namensteile, Singular/Plural-Dubletten, Boilerplate in den Top-Begriffen)

### Phase 3 · EDA (parallel, bis 29.11.)

`src/01_eda.ipynb`:

- [ ] Artikel pro Jahr / Ressort, Missing Values (Lead, Ressort, Datum), Kandidaten pro Artikel
- [ ] Häufigste Keyphrases gesamt und pro Jahr, Verteilung (Long Tail)
- [ ] Plausibilitätscheck gegen die Quelle (Stichprobe n ≥ 30–60)
- [ ] Vergleich alte (`data/20min_metadaten_keywords_clean.csv`) vs. neue Extraktion → Begründung, warum neu gebaut wurde
- [ ] Optional Sweetviz/ydata-profiling-Report (wie in der Aufgabe empfohlen)
- [ ] Festhalten: **welche Massnahmen** aus der EDA folgen (gehört explizit in die Präsentation)

### Phase 4 · Netzwerkkonstruktion (30.11.–06.12.)

`src/network.py` + `src/02_netzwerk.ipynb`:

- [ ] Two-Mode-Graph Artikel–Keyphrase (selbst analysieren: Grad-Verteilung beider Modi)
- [ ] One-Mode-Projektion Keyphrase–Keyphrase; Gewichte: Kookkurrenz, Newman's Weighted Projection, Salton (E-E)
- [ ] Sparsifizierung (Mindestgewicht oder Backbone / k-NN), Filterkriterien dokumentieren
- [ ] Knotenattribute: dominantes Ressort, Dokumentfrequenz, Entitätsklasse, Erstauftrittsjahr
- [ ] 16 Jahresnetze 2010–2025 + Gesamtnetz; Teilnetze je Ressort
- [ ] Export `graphen/*.gexf` + Kantenlisten-CSV; Visualisierung in **Gephi** (Layout, Louvain-Färbung, Filter) → Screenshots für die Präsentation
- [ ] Kennzahlentabelle: Knoten, Kanten, Dichte, Komponenten, Giant Component, Durchmesser, Clustering

**Achtung:** Jeder Artikel erzeugt eine Clique über seine Keyphrases → Clustering ist künstlich hoch. Offenlegen und gegen ein Nullmodell stellen (Konfigurationsmodell auf dem bipartiten Graphen).

### Phase 5 · Analysen und Hypothesentests (07.–20.12.)

`src/03_analyse_*.ipynb`. Jede Analyse mit **Frage → Methode → Resultat → Interpretation für 20 Minuten**.

| | These | Methode (Skript-Kapitel) | Test |
|---|---|---|---|
| **H1** | Krisenjahre (2020 Covid, 2022 Ukraine) zentralisieren die Agenda | Degree-/Betweenness-Zentralisierung, Louvain-Modularität über Seeds (Kap. 5, 7) | Krisenjahre vs. Verteilung der übrigen Jahre, Referenznetze (Kap. 11.3.4) |
| **H2** | Ressorts sind semantische Silos, wenige Brückenbegriffe | kategorische Assortativität nach Ressort, Betweenness, Structural Holes / Burt (Kap. 1.5.2, 6, 10.4) | Label-Permutation, QAP (Kap. 11.3.2–11.3.3) |
| **H3** | Neue Themenverbindungen sind vorhersagbar, Adamic-Adar > Preferential Attachment | CN, Jaccard, RA, AA, PA auf Zeitfenstern (Kap. 12) | Precision@k / AUC, Bootstrap |

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
| 46 | 12.–15.11. | 0 Sofort | Meilenstein eingereicht, Termin bestätigt, KI-Log läuft |
| 47 | 16.–22.11. | 1 Pilot & Crawl | Kandidatenschicht in SQLite |
| 48 | 23.–29.11. | 2 Keyphrases + 3 EDA | `keyphrases.parquet`, `01_eda.ipynb` |
| 49 | 30.11.–06.12. | 4 Netzwerk | `.gexf`-Dateien, Kennzahlentabelle, Gephi-Bilder |
| 50–51 | 07.–20.12. | 5 Analysen | H1–H3 mit Tests und Interpretation |
| 52–1 | 21.12.–03.01. | 6 Abgabe | Präsentation aufgenommen, Paket in Teams |

Puffer: Phase 5 kann auf H1 + H2 + Zentralitäten/Communities reduziert werden, falls Phase 1 oder 2 länger dauert. H3 und Graphlets sind die ersten Kandidaten zum Streichen.

---

## 6. Risiken

| Risiko | Gegenmassnahme |
|---|---|
| Parser scheitert an alten Layouts (2010–2015) | Pilot über alle Jahrgänge **vor** dem Hauptlauf |
| 20min.ch blockiert / drosselt | User-Agent gesetzt, Backoff vorhanden; Workers niedrig halten, über Nacht laufen lassen |
| Keyphrases zu verrauscht → Netz unbrauchbar | Stoppliste und Ranking iterativ auf der Kandidatenschicht, kein Neu-Crawl nötig |
| Projektionsnetz zu dicht (Altdaten: Dichte 0.34) | Normalisierung + Sparsifizierung, Filter in der Präsentation erklären |
| Analysen ohne Interpretation | Pro Grafik ein Satz „Was heisst das für die 20-Minuten-Berichterstattung?“ |
| Fehlende KI-Deklaration | Ab sofort mitschreiben, nicht am Schluss rekonstruieren |
