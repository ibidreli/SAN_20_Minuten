# Meilenstein · 20-Minuten-Mining: Themen- und Redaktionsnetzwerke 2020–2026

**Gruppe:** *(Nr. ergänzen)* · **Team:** Elias, Luca · **Modul:** Soziale Netzwerkanalyse, FHNW

## Idee

Angelehnt an David Kriesels *[SpiegelMining](https://www.dkriesel.com/spiegelmining)* (33C3) untersuchen wir, worüber 20 Minuten berichtet, wie die Themen zusammenhängen  
und wie die Redaktion organisiert ist. Grundlage sind alle Online-Artikel von [20min.ch](https://www.20min.ch/) von Januar 2020 bis November 2026.

## Datenquelle und Beschaffung

- **Quelle:** öffentliche Artikelseiten von [20min.ch](https://www.20min.ch/). Die URL-Liste stammt aus den [Tages-Sitemaps](https://www.20min.ch/sitemap) (477'487 Artikel seit 2003).  
Für die Analyse verwenden wir 166'212 Artikel ab 01.01.2020.
- **Eigener Crawler**: lädt jede Seite und liest Titel, Lead, Ressort, Datum, Autoren mit Kürzel/ID, Quellenkürzel  
(Agenturen), Textlänge, Format (Artikel/Liveticker) sowie Likes, Shares und Kommentare. Danach folgen Named Entity Recognition und Nominalphrasen mit spaCy. Die Daten werden in einer SQLite Datenbank abgespeichert.
- **Urheberrecht:** Den Volltext speichern wir nicht, nur Metadaten und daraus gewonnene Begriffe.

## Modellierung

| Netz               | Knoten                                                                             | Kante                          | Gewicht                                                            |
| ------------------ | ---------------------------------------------------------------------------------- | ------------------------------ | ------------------------------------------------------------------ |
| Themennetz         | Keywords (Personen, Organisationen, Orte, Themen -> Top 8 pro Artikel nach TF-IDF) | gemeinsam in einem Artikel     | Newman's Weighted Projection, Vergleich mit Kookkurrenz und Salton |
| Co-Autorennetz     | Journalistinnen und Journalisten                                                   | gemeinsam gezeichneter Artikel | Anzahl Artikel                                                     |
| Autoren-Themennetz | Journalistinnen und Journalisten                                                   | ähnliche Themen                | Kosinus über Keyword-Profile                                       |

Zwei-Modus-Netze Artikel – Keyword und Artikel – Person, projiziert auf One-Mode. Knotenattribute sind Ressort, Entitätstyp, Häufigkeit,
erstes Auftreten sowie Likes und Kommentare (Median). Dazu kommen Jahresnetze 2020–2026.

## Fragestellungen und Hypothesen

- **H1** Krisenjahre (2020 Covid, 2022 Ukraine) zentralisieren die Agenda: höhere Degree-Zentralisierung, tiefere Modularität.
  Getestet auf gleich grossen Jahresstichproben.
- **H2** Ressorts sind thematische Silos, die nur wenige Begriffe verbinden: kategorische Assortativität nach Ressort mit
  Permutationstest, Brückenbegriffe über Betweenness.
- **H3** Neue Themenverbindungen sind vorhersagbar, lokale Verfahren (Adamic-Adar, Resource Allocation) schlagen Preferential Attachment.
  Link Prediction von Vorjahren auf das Folgejahr (AUC, Precision@k).
- **H4** Die Redaktion arbeitet in ressortgebundenen Teams. Themencluster unterscheiden sich in den Reaktionen
  (Kommentare vs. Likes vs. Shares).

## Geplante Analysen (Skript-Kapitel)

Projektionen, Reduktion: Backbone, Ego-Netze, Komponenten, k-Core, Louvain vs. Label Propagation, Zentralitäten und  
Zentralisierung, Dichte, Clustering, Pfadlängen im Jahresvergleich, Assortativität, Nullmodell gegen das  
Clique-Artefakt der Projektion und Permutationstests, Link Prediction, Visualisierung in Gephi.

## Bekannte Hindernisse

- **Reaktionen erst ab Juni 2020:** Vorher liefert die Quelle 0 Likes und keine Kommentare. Diese Werte behandeln wir als fehlend.  
Liveticker sammeln Reaktionen über Tage und werden für Reaktionsauswertungen ausgeschlossen.
- **Autoren 2020 oft nur als Kürzel:** Kürzel lösen wir über Artikel auf, in denen Name und Kürzel gemeinsam stehen. Kürzel, die sich  
nicht auflösen lassen, bleiben eigene Knoten.
- **Clique-Artefakt:** Jeder Artikel verbindet alle seine Keywords. Das Clustering vergleichen wir deshalb mit einem Konfigurationsmodell.
- **Laufzeit:** Der Crawl dauert etwa 11 Stunden und erzeugt rund 4 GB Daten.
- **Qualität der Entitätserkennung:** spaCy ordnet etwa 10–15 % der Namen dem falschen Typ zu (z. B. „US-Präsident“ als Ort). Festgestellt haben wir das mit einer manuellen Prüfung der Stichprobe. Für Kanten ist das unkritisch, für Auswertungen nach Typ weisen wir es aus.
