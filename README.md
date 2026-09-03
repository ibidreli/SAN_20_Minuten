# Strukturelle Dynamik, redaktionelle Kollaboration und Link-Prediction im Schweizer Online-Journalismus

Soziale Netzwerkanalyse von *20 Minuten* (2020 bis 2024). FHNW, Modul SAN.

Team: Elias, Luca

## Projektidee

Analyse der redaktionellen Interaktionsmuster und Themenstrukturen von 20min.ch
auf Basis eines eigens gecrawlten Volltext- und Metadaten-Korpus. Zwei
komplementaere Netzwerkmodelle:

- **Modell A**: gewichtetes Autoren-Kollaborationsnetzwerk (One-Mode-Projektion
  eines bipartiten Artikel-Autor-Graphen, Newman-Kollaborationsgewichtung)
- **Modell B**: longitudinales semantisches Keyword-Kookkurrenz-Netzwerk
  (Salton-Kosinus, Mutual k-NN Sparsifizierung)

Die vollstaendige Projektbeschreibung liegt in `docs/SAN-Meilensteine.md`.

## Durchgefuehrte Analysen

| Lernergebnis | Analyse | Notebook-Abschnitt |
|---|---|---|
| LE3 | Two-Mode-Modellierung, Newman-Projektion auf One-Mode | 1 |
| LE5 | Zentralitaetsmasse, strukturelle Loecher nach Burt (Constraint, Effective Size) | 2.1 |
| LE7 | Ressort-Homophilie via Label-Permutation | 2.2 |
| LE7 | Kanten-JSD vs. gradtreues Maslov-Sneppen-Nullmodell | 2.3 |
| LE7 | QAP mit gemeinsamer Zeilen-/Spalten-Permutation | 2.4 |
| LE7 | OLS auf Leave-One-Out-JSD und Leser-Shares (mit N, R2) | 2.5 |
| LE4, LE6 | Cliquen, k-Core, Artikulationspunkte, Bruecken, Connectivity | 2.6 |
| LE6 | Makro-Metriken, Zentralisierung C_D und C_B 2020-2024 | 3.1 |
| LE6 | Sensitivitaetsanalyse der Sparsifizierung, k in {5, 10, 20} | 3.2 |
| LE4 | Louvain-Community-Detection auf Keyword-Netzwerken | 3.3 |
| LE6 | Pruefung von Hypothese 2 inkl. Grenzen des Messdesigns | 3.4 |
| LE8 | Rollierende temporale Link-Prediction, fuenf Algorithmen | 4 |
| LE9 | Independent-Cascade-Diffusion, Broker vs. Hubs vs. Zufall | 5 |

Nicht abgedeckt: LE10 (Graphlets), im Ausblick des Notebooks als naechster
Schritt benannt. 14 durchnummerierte Abbildungen, alle inline sichtbar und in
der Interpretation referenziert.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download de_core_news_sm   # nur fuer die Extraktionspipeline
```

## Repository-Struktur

| Pfad | Inhalt |
|---|---|
| `data_extraction/` | Web-Crawler und Extraktionspipeline (sitemap, trafilatura, spaCy) |
| `data/` | Datensaetze. Rohdaten und Parquet sind bewusst **nicht** versioniert |
| `src/00_eda.qmd` | Explorative Datenanalyse des Rohkorpus |
| `src/01_cleaning.qmd` | Datenaufbereitung, Qualitaetspruefung, Ground-Truth-Validierung |
| `src/clean_dataset.py` | Cleaning-Skript, erzeugt das Parquet. Nur ausfuehren, nie importieren (siehe offene Punkte) |
| `src/network_models.py` | Graphkonstruktion, Metriken, Link-Prediction |
| `src/02_analyse.ipynb` | Hauptanalyse-Notebook (generiert, siehe unten) |
| `scripts/` | Notebook-Generierung, Ausfuehrung, Manifest, Ground-Truth-Audit, Abgabe-Paket |
| `out_plots/` | Erzeugte Abbildungen fuer den Bericht |
| `graphen/` | Exportierte `.gexf`-Graphen fuer Gephi |
| `docs/` | Meilensteindokument, Bewertungsraster, Modulbeschreibung |
| `explorations/` | Nebenanalysen, nicht Teil der Hauptargumentation |
| `TODO.md` | Offene Punkte, u.a. die noch fehlende KI-Deklaration |

## Daten

Die Rohdaten (324 MB CSV) und das bereinigte Parquet (33 MB) sind per
`.gitignore` ausgeschlossen. `data/manifest.json` enthaelt die Hashes der
Rohdateien zur Integritaetspruefung.

Ausfuehrungsreihenfolge, jeweils **vom Repository-Wurzelverzeichnis** aus:

```bash
python src/clean_dataset.py              # Rohdaten -> data/20min_cleaned_post2020.parquet
python scripts/build_analysis_notebook.py  # erzeugt src/02_analyse.ipynb
python scripts/run_notebook.py           # fuehrt das Notebook headless aus
python scripts/build_manifest.py         # aktualisiert die Hashes in data/manifest.json
python scripts/build_manifest.py --check # prueft Rohdaten und Parquet gegen das Manifest
python scripts/package_submission.py --dry-run  # zeigt das Abgabe-Paket
python scripts/package_submission.py            # baut submission/*.zip
python scripts/build_ground_truth_validation.py --offline  # Audit-Report neu rendern
python scripts/build_ground_truth_validation.py            # Live-Audit gegen 20min.ch
```

Die Unit-Tests der Netzwerkmodelle laufen mit:

```bash
python src/network_models.py
```

Die Quarto-Dokumente in `src/` verwenden dagegen dokumentrelative Pfade
(`../data/...`) und werden mit `quarto render src/01_cleaning.qmd` gerendert.

## Stand der Code-Review-Befunde

Das Projekt wurde in drei Runden systematisch reviewt. Alle Befunde sind
behoben und durch Unit-Tests in `src/network_models.py` abgesichert
(`python src/network_models.py`).

### Runde 1: acht Befunde zur Korrektheit

| # | Befund | Behebung |
|---|---|---|
| 1 | Trainingskanten landeten in der Negativmenge der Link-Prediction, da Kantentupel unsortiert verglichen wurden | Normalisierung auf sortierte Tupel; Regressionstest |
| 2 | Die als „Leave-One-Out JSD“ bezeichnete Regression war keine (Artikel k war in seinem eigenen Prädiktor enthalten) | `compute_leave_one_out_jsd` implementiert und im Notebook verwendet |
| 3 | Tie-Break für `dominant_ressort` erfolgte über die Position in der kanonischen Ressortliste | Tie-Break über das juengste Publikationsdatum im jeweiligen Ressort |
| 4 | `graphen/*.gexf` liessen sich mit keinem Code im Repository reproduzieren | `export_graph_gexf` plus Notebook-Zelle 2.6 |
| 5 | Die Signifikanzaussage zum Bootstrap-CI wurde unabhaengig vom Intervall gedruckt | Aussage wird aus `ci_low`/`ci_high` abgeleitet; bester Algorithmus wird berechnet |
| 6 | p-Werte in Plot-Legenden waren Stringliterale („p < 0.002“ bei tatsaechlich p = 0.00200) | Legenden werden aus den berechneten p-Werten erzeugt |
| 7 | Fehlende Interaktionswerte wurden zu 0 statt zu `NaN` | Nullable `Int64`; Aggregation mit `nanmean` |
| 8 | `article_id` war nicht reproduzierbar (instabiler Sort), Manifest deckte das Parquet nicht ab | Stabiler Sort auf `(datum, url)`; `scripts/build_manifest.py` hasht auch das Parquet |

Vier weitere Punkte kamen bei der Behebung dazu:

- **Precision@k** wurde innerhalb grosser Gruppen identischer Scores durch die
  Array-Position entschieden. Jetzt fest geseedeter Tie-Break via `np.lexsort`.
- Das **Two-Mode-Netzwerk** wurde nur aus Mehrautoren-Artikeln gebaut und war
  damit ein gefilterter Teilgraph. Jetzt ueber alle Artikel mit Autorenschaft.
- Der **Agentur-Filter** verglich nur exakte Zeichenketten. Zusammengesetzte
  Bylines wie `SDA fss`, `Rat Dpa` oder `Agence France-Presse` (214 Artikel,
  Mitglied der groessten Clique) gelangten als vermeintliche Personen in den
  Graphen. Token-basierte Filterung entfernt 133 institutionelle Knoten
  (947 auf 814 Autor:innen).
- Der **QAP-Test** korrelierte zunaechst zwei Matrizen, die beide fuer nicht
  benachbarte Paare null sind, und mass damit teilweise blosse
  Kanten-Kopraesenz. Mit einer ueber alle Dyaden definierten JSD-Matrix kehrt
  sich das Vorzeichen von +0.148 auf -0.140 um, was der Homophilie-Hypothese
  entspricht.

### Runde 2: zehn Befunde zu Vollstaendigkeit und Belegbarkeit

| # | Befund | Behebung |
|---|---|---|
| 1 | Interpretation fehlte bei 7 von 10 Analysen | Alle 14 Analyse-Zellen haben jetzt eine anwendungsbezogene Interpretation |
| 2 | Methodik versprach eine Sensitivitaetspruefung ueber `k`, die nie lief | Implementiert als Abschnitt 3.2 |
| 3 | Hypothese 2 wurde nirgends gegen die Erwartung geprueft | Abschnitt 3.4, inkl. Grenzen des Messdesigns |
| 4 | „Burt structural holes“ war `betweenness/(degree+1)` | `nx.constraint` und `nx.effective_size`, getrennt von Betweenness |
| 5 | $C_B$ und Precision@100 waren im Meilenstein zugesagt, fehlten aber | Beide ergaenzt |
| 6 | OLS gab nur Koeffizienten aus | N, $R^2$, adj. $R^2$, F-Statistik und Fallausschluesse |
| 7 | `ground_truth_validation.md` hatte keinen erzeugenden Code | `scripts/build_ground_truth_validation.py`, mit `--offline` |
| 8 | Abbildungen: Nummernkollision, Luecken, Renderings nicht im Notebook | Durchnummeriert 01-14, alle inline, alle im Text referenziert |
| 9 | Stub-Notebook und internes `TODO.md` landeten im Abgabe-Paket | Aus `Source/` entfernt |
| 10 | LE9 (Diffusion) nicht abgedeckt | Independent Cascade als Pfeiler 4 |

### Runde 3: fuenf Befunde, davon einer schwerwiegend

| # | Befund | Behebung |
|---|---|---|
| 1 | **Diffusion war am Maximalgewicht normiert.** Bei $w_{max} = 103$ und Median $1.0$ lag die effektive Uebertragungswahrscheinlichkeit rund 50-fach unter dem angegebenen $p$; 94.7% der Kanten unter 0.01. Der Befund „Hubs schlagen Broker“ war ein Artefakt. | Normierung am Median, magische Konstante entfernt, Sweep ueber $p \in \{0.02, ..., 0.5\}$. Ergebnis kehrt sich um: bei kleinem $p$ gewinnen die Broker klar, ab $p \approx 0.1$ wird die Startmenge irrelevant |
| 2 | $C_B$ trug die Aussage zu Hypothese 2, war aber nur bei $k=10$ geprueft | $C_B$ in die Sensitivitaetsanalyse aufgenommen. Ergebnis: **nicht robust** (Maximum 2020/2020/2023), die Aussage wurde entsprechend zurueckgenommen |
| 3 | Das robuste $Q$-Minimum 2020 bei allen $k$ war nicht erwaehnt | Als k-robuste Bestaetigung der Modularitaets-Haelfte von Hypothese 2 ausgewiesen |
| 4 | Abstract, Forschungsfrage und Kapitelnummerierung waren veraltet | Abstract auf vier Pfeiler aktualisiert, Burt-Formulierung korrigiert, Nummerierung durchgezogen |
| 5 | $Q$ differierte zwischen 3.1 (Mittel ueber 10 Seeds) und 3.2 (Einzellauf) | Fussnote in 3.2 |

### Auswirkungen auf die Resultate

- 41.4% der Kommentarwerte (48'970 Artikel) waren faelschlich 0.
- 1'573 Autorennamen wurden durch `capitalize()` beschaedigt. Autorennamen sind
  Knoten-IDs.
- 133 institutionelle Knoten (Agenturen, Desks) sind entfernt: 814 statt 947
  Autor:innen, 574 statt 639 Knoten im Kollaborationsnetzwerk.
- PR-AUC der Link-Prediction im finalen Fenster: 0.1872 statt 0.1230.
- QAP-Korrelation Kollaborationsgewicht zu Ressort-Divergenz: -0.140 statt
  +0.148 (Vorzeichenumkehr nach Korrektur der Matrixdefinition).
- Diffusion: nach Korrektur der Normierung erreichen die Burt-Broker bei
  $p = 0.02$ das 2.3-fache einer Zufallsauswahl; zuvor schien der Unterschied
  zu den Hubs entgegengesetzt.
- Assortativitaet r = 0.3630.

### Verbleibende Einschraenkung

`src/clean_dataset.py` ist ein flaches Skript ohne
`if __name__ == "__main__":`-Guard. Ein Import fuehrt die gesamte Pipeline aus.
Das Skript ist zum Ausfuehren gedacht, nicht zum Importieren.

## Hinweis zur Nutzung von KI-Werkzeugen

Teile des Analysecodes wurden mit KI-Assistenz erstellt. Die oben genannten
Befunde stammen aus einem anschliessenden Code-Review.

**Die Projektbeschreibung verlangt neben der Deklaration ausdruecklich die
Angabe der Prompts.** Diese Dokumentation fehlt noch und ist in `TODO.md` als
blockierender Punkt erfasst.
