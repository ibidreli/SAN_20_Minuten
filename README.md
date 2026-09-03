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
| `src/clean_dataset.py` | Cleaning-Logik als Modul, erzeugt das Parquet |
| `src/network_models.py` | Graphkonstruktion, Metriken, Link-Prediction |
| `src/02_analyse.ipynb` | Hauptanalyse-Notebook (generiert, siehe unten) |
| `scripts/` | Notebook-Generierung und headless Ausfuehrung |
| `out_plots/` | Erzeugte Abbildungen fuer den Bericht |
| `graphen/` | Exportierte `.gexf`-Graphen fuer Gephi |
| `docs/` | Meilensteindokument, Bewertungsraster, Modulbeschreibung |
| `explorations/` | Nebenanalysen, nicht Teil der Hauptargumentation |

## Daten

Die Rohdaten (324 MB CSV) und das bereinigte Parquet (33 MB) sind per
`.gitignore` ausgeschlossen. `data/manifest.json` enthaelt die Hashes der
Rohdateien zur Integritaetspruefung.

Ausfuehrungsreihenfolge, jeweils **vom Repository-Wurzelverzeichnis** aus:

```bash
python src/clean_dataset.py              # Rohdaten -> data/20min_cleaned_post2020.parquet
python scripts/build_analysis_notebook.py  # erzeugt src/02_analyse.ipynb
python scripts/run_notebook.py           # fuehrt das Notebook headless aus
```

Die Quarto-Dokumente in `src/` verwenden dagegen dokumentrelative Pfade
(`../data/...`) und werden mit `quarto render src/01_cleaning.qmd` gerendert.

## Bekannte offene Punkte

Ein Code-Review hat folgende Punkte identifiziert, die noch **nicht** behoben
sind. Die Zahlen in `src/02_analyse.ipynb` und in den Abbildungen sind davon
betroffen und noch nicht final:

1. `src/network_models.py`: Beim Aufbau der Negativmenge fuer die
   Link-Prediction werden Trainingskanten nicht zuverlaessig ausgeschlossen,
   da Kantentupel nicht sortiert verglichen werden. Dadurch landen echte
   Kanten in der Negativmenge und PR-AUC sowie Precision@k sind zu tief.
2. `scripts/build_analysis_notebook.py`: Die als "Leave-One-Out JSD"
   bezeichnete Regression ist keine, da die Autorenprofile ueber den gesamten
   Korpus gebildet werden. Der Artikel k ist in seinem eigenen Profil enthalten.
3. `src/network_models.py`: Der Tie-Break fuer `dominant_ressort` erfolgt ueber
   die Position in der kanonischen Ressortliste statt, wie dokumentiert, ueber
   das juengste Publikationsdatum.
4. Die `.gexf`-Dateien in `graphen/` lassen sich mit dem aktuellen Code nicht
   reproduzieren: `nx.write_gexf` scheitert am numpy-Knotenattribut
   `ressort_distribution`.
5. p-Werte und Signifikanzaussagen sind im Notebook teilweise als Stringliteral
   hinterlegt statt aus den berechneten Werten abgeleitet.
6. Fehlende Interaktionswerte (Likes, Kommentare) werden in
   `src/clean_dataset.py` zu 0 statt zu `NaN`.

## Hinweis zur Nutzung von KI-Werkzeugen

Teile des Analysecodes wurden mit KI-Assistenz erstellt. Die oben genannten
offenen Punkte stammen aus einem anschliessenden Code-Review.
