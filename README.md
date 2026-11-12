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
python scripts/run_notebook.py           # baut, fuehrt aus und setzt die Kennzahlen in den Text ein
python scripts/validate_notebook.py      # Qualitaetsgate, siehe unten
python scripts/build_manifest.py         # aktualisiert die Hashes in data/manifest.json
python scripts/build_manifest.py --check # prueft Rohdaten und Parquet gegen das Manifest
python scripts/package_submission.py --dry-run  # zeigt das Abgabe-Paket
python scripts/package_submission.py            # baut submission/*.zip
python scripts/build_ground_truth_validation.py --offline  # Audit-Report neu rendern
python scripts/build_ground_truth_validation.py            # Live-Audit gegen 20min.ch
```

`scripts/build_analysis_notebook.py` kann auch einzeln laufen, erzeugt dann
aber ein Notebook mit unaufgeloesten Platzhaltern. Der Weg ueber
`run_notebook.py` ist der vorgesehene.

Die Unit-Tests der Netzwerkmodelle laufen mit:

```bash
python src/network_models.py
```

### Kennzahlen im Fliesstext

Die Interpretationstexte enthalten keine handgeschriebenen Zahlen. Jede
Kennzahl laeuft im Notebook durch `fact(schluessel, wert, format)`, landet in
`data/notebook_facts.json` und wird von `scripts/run_notebook.py` nach der
Ausfuehrung in die Platzhalter `{{schluessel}}` eingesetzt. Ein erneuter Lauf
schreibt den Text also neu, statt eine alte Zahl stehen zu lassen.

`scripts/validate_notebook.py` prueft danach sieben Bedingungen und bricht mit
Rueckgabewert 1 ab, wenn eine verletzt ist:

1. keine Zelle mit Ausfuehrungsfehler,
2. kein unaufgeloester Platzhalter,
3. keine Steuerzeichen im Markdown (verunglueckte LaTeX-Escapes),
4. **jede Zahl im Fliesstext ist durch eine Zellenausgabe oder die Registry
   gedeckt**; Ausnahmen brauchen einen begruendeten Eintrag in
   `ALLOWED_NUMBERS`,
5. Abbildungen luecklos nummeriert, alle inline sichtbar und im Text
   referenziert,
6. auf jede Abbildungszelle folgt eine Interpretation,
7. die Registry existiert.

Die Quarto-Dokumente in `src/` verwenden dagegen dokumentrelative Pfade
(`../data/...`) und werden mit `quarto render src/01_cleaning.qmd` gerendert.

## Stand der Code-Review-Befunde

Das Projekt wurde in sechs Runden systematisch reviewt. Alle Befunde sind
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
  Graphen. Token-basierte Filterung entfernte in dieser Runde 133
  institutionelle Knoten (947 auf 814 Autor:innen). Runde 4 zeigte, dass der
  Filter weiter durchliess, und erweiterte ihn auf 166 Knoten (947 auf 781).
- Der **QAP-Test** korrelierte zunaechst zwei Matrizen, die beide fuer nicht
  benachbarte Paare null sind, und mass damit teilweise blosse
  Kanten-Kopraesenz. Mit einer ueber alle Dyaden definierten JSD-Matrix kehrt
  sich das Vorzeichen von +0.148 auf -0.1393 um, was der Homophilie-Hypothese
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
| 1 | **Diffusion war am Maximalgewicht normiert.** Bei $w_{max} = 103$ und Median $1.0$ lag die effektive Uebertragungswahrscheinlichkeit rund 50-fach unter dem angegebenen $p$; 94.7% der Kanten unter 0.01. Der Befund „Hubs schlagen Broker“ war ein Artefakt. | Normierung am Median, magische Konstante entfernt, Sweep ueber $p \in \{0.02, ..., 0.5\}$. Nach dieser Korrektur lagen die Broker vorn. Auch das war noch ein Artefakt, siehe Runde 4, Befund 4: mit vergleichbarer Baseline verschwindet der Vorsprung ganz |
| 2 | $C_B$ trug die Aussage zu Hypothese 2, war aber nur bei $k=10$ geprueft | $C_B$ in die Sensitivitaetsanalyse aufgenommen. Ergebnis: **nicht robust** (Maximum 2020/2020/2023), die Aussage wurde entsprechend zurueckgenommen |
| 3 | Das robuste $Q$-Minimum 2020 bei allen $k$ war nicht erwaehnt | Als k-robuste Bestaetigung der Modularitaets-Haelfte von Hypothese 2 ausgewiesen |
| 4 | Abstract, Forschungsfrage und Kapitelnummerierung waren veraltet | Abstract auf vier Pfeiler aktualisiert, Burt-Formulierung korrigiert, Nummerierung durchgezogen |
| 5 | $Q$ differierte zwischen 3.1 (Mittel ueber 10 Seeds) und 3.2 (Einzellauf) | Fussnote in 3.2 |

### Runde 4: fuenf Befunde, davon drei blockierend

| # | Befund | Behebung |
|---|---|---|
| 1 | **Betweenness wurde mit falscher Gewichtssemantik berechnet.** networkx liest `weight` als Distanz, das Newman-Gewicht ist aber eine Staerke. Die staerksten Kollaborationen galten damit als die laengsten Wege; 8 von 10 Namen der Broker-Tabelle waren falsch | Kollaborationskanten tragen jetzt `distance = 1/weight`, alle Pfadmasse nutzen es. Das Keyword-Netzwerk machte es bereits richtig |
| 2 | **Der Agenturfilter liess weiter durch**: `Spot` (187 Artikel), `Agvs` (120), `Sp-X`, `Storyful`, `Picstars` u.a. `Spot` waere nach Behebung von Befund 1 in die Broker-Top-10 gerutscht | Exakt-Set plus erweiterte Tokens und Substrings; 166 institutionelle Knoten entfernt (781 statt 947 Autor:innen) |
| 3 | **`python-louvain` fehlte in `requirements.txt`** | Ergaenzt und pruefbar (`pip install --dry-run`) |
| 4 | Diffusions-Baseline war konfundiert: Zufallsauswahl aus allen Knoten, Broker und Hubs aus einer gefilterten Grundgesamtheit | Baseline aus derselben Grundgesamtheit; die naive Ziehung wird zusaetzlich ausgewiesen. Der scheinbare Broker-Vorsprung verschwindet |
| 5 | `package_submission.py` haette die Aufzeichnung geloescht (`rmtree` ohne Eintrag in `LAYOUT`) | Aufzeichnung liegt in `praesentation/` ausserhalb des Pakets und wird hineinkopiert |

Zusaetzlich behoben: `freeman_centralization` gab die rohe Summe statt eines
normierten Werts zurueck; `#WIRSINDZUKUNFT` war in `clean_dataset` ein eigenes
Ressort, im JSD-Vektor aber Teil von `Andere`; `kommentare_erlaubt` machte aus
fehlenden Werten `False`; mehrere Zahlenangaben in der Prosa stimmten nicht mit
der Ausgabe ueberein.

### Runde 5: Reproduzierbarkeit

Zwei aufeinanderfolgende Notebook-Laeufe auf identischen Daten lieferten
unterschiedliche Zahlen, obwohl ueberall `seed=42` gesetzt war. Ursache: die
Iteration ueber Python-**Mengen** folgt der Hash-Reihenfolge, die pro Prozess
variiert. Betroffen waren die Kandidatenreihenfolge der Link-Prediction, die
Diffusions-Startmengen, die Knotenreihenfolge mengenbasierter Teilgraphen und
die Summationsreihenfolge des Adamic-Adar-Scores; zusaetzlich war das
Maslov-Sneppen-Rewiring ungeseedet. Nach Sortierung aller Mengen-Iterationen,
expliziter Seed-Uebergabe und Rundung der Scores sind zwei Laeufe
**byte-identisch**. Geprueft mit:

```bash
python scripts/run_notebook.py && cp -f src/02_analyse.ipynb /tmp/a.ipynb
python scripts/run_notebook.py   # Ausgaben mit /tmp/a.ipynb vergleichen
```

### Runde 6: veraltete Zahlen im Fliesstext, und die strukturelle Ursache

| # | Befund | Behebung |
|---|---|---|
| 1 | **Zwei Interpretationszellen widersprachen der Ausgabe direkt darueber.** Die Modellierungszelle nannte 814 / 83'707 / 574 / 2'754, gedruckt waren 781 / 83'273 / 554 / 2'717. Die OLS-Zelle nannte $N = 6'887$, adj. $R^2 = 0.353$ und einen Koeffizienten von 0.61, gedruckt waren 6'586, 0.3610 und 0.6754 | Beide Zellen ziehen ihre Zahlen jetzt aus der Registry |
| 2 | Die Brokerage-Interpretation beschrieb noch die fehlerhafte Betweenness-Rangliste („teilweise andere Namen, oft mit deutlich geringerem Grad“). Tatsaechlich liegen neun der zehn auf oder ueber dem Median-Grad | Absatz neu gefasst und vollstaendig aus berechneten Werten erzeugt; die eine Ausnahme wird benannt |
| 3 | `README.md` widersprach sich selbst zur Diffusion: Runde 3 behauptete einen Broker-Vorsprung, den Runde 4 widerlegt hatte | Runde-3-Eintrag als Zwischenstand gekennzeichnet und auf Runde 4 verwiesen |
| 4 | Der Block „Siegerstrategie je p“ druckte fuer jedes $p$ einen Sieger ohne Streuungsmass, waehrend der Text sagte, die Wahl sei egal | Standardabweichungs-Tabelle, 95%-KI des Mittelwerts und $z$-Statistik je $p$; verglichen werden nur die drei Strategien aus derselben Grundgesamtheit. Ergebnis: bei 2 von 5 $p$-Werten ist der Abstand trennscharf, aber die Zufallsauswahl fuehrt bei 4 von 5 |
| 5 | Assortativitaets- und Nullmodell-Zelle nannten $r = 0.3630$ und $0.3371$ / $0.6258$; gedruckt waren $0.3621$ und $0.3355$ / $0.6199$ | Ueber die Registry |
| 6 | `$\text{...}$` stand in einem nicht-rohen Python-String und wurde zu einem Tabulator; zwei Formeln wurden nicht gesetzt | Escape korrigiert, Pruefung 3 des Gates faengt den Fall kuenftig ab |
| 7 | Evidence Map und Lessons Learned nannten weiter 133 entfernte Knoten | Auf 166 korrigiert |

**Die strukturelle Ursache.** Alle drei bisherigen Runden hatten dasselbe
Muster: die Korrektur am Code war richtig, aber die Prosa mit den
festgeschriebenen Zahlen lief still aus dem Takt. Deshalb wurde in dieser Runde
nicht nur der Text korrigiert, sondern die Fehlerklasse entfernt. Zahlen
stehen nicht mehr im Text, sondern werden zur Laufzeit eingesetzt, und
`scripts/validate_notebook.py` bricht ab, sobald eine Zahl im Fliesstext
nirgends gedeckt ist.

### Auswirkungen auf die Resultate

- 41.4% der Kommentarwerte (48'970 Artikel) waren faelschlich 0.
- 1'573 Autorennamen wurden durch `capitalize()` beschaedigt. Autorennamen sind
  Knoten-IDs.
- 166 institutionelle Knoten (Agenturen, Desks, Content-Zulieferer) sind
  entfernt: 781 statt 947 Autor:innen, 554 statt 639 Knoten im
  Kollaborationsnetzwerk.
- PR-AUC der Link-Prediction im finalen Fenster: 0.1939 statt 0.1230.
- QAP-Korrelation Kollaborationsgewicht zu Ressort-Divergenz: -0.1393 statt
  +0.148 (Vorzeichenumkehr nach Korrektur der Matrixdefinition).
- Diffusion: nach Korrektur von Normierung UND Baseline unterscheiden sich die
  Startmengen-Strategien um weniger als 2%. Die zuvor berichteten Vorspruenge
  (erst "Hubs schlagen Broker", dann "Broker erreichen das 2.5-fache") waren
  beide methodische Artefakte.
- Assortativitaet r = 0.3621.
- 78 Kennzahlen im Fliesstext werden zur Laufzeit eingesetzt statt von Hand
  geschrieben.

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
