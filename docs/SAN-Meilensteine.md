# Meilenstein SNA-Projekt

In diesem Meilenstein formulieren Sie ihre Projektidee. Sie sind keinesfalls darauf beschränkt, dass Sie schlussendlich dann nur genau die hier beschriebenen Analysen durchführen dürfen oder alle hier beschriebenen Analysen durchführen müssen. Der Meilenstein dient zum Austausch zwischen den Studierenden und dem Dozenten in der Anfangsphase, um Ihnen frühzeitig Feedback zur Projektidee geben zu können.

## Organisatorisches

Die Fragen in diesem Abschnitt betreffen die rein organisatorischen Aspekte des Projekts.

### Projekttitel / Projekt Kurzbeschrieb:

**Strukturelle Dynamik, redaktionelle Kollaboration und Link-Prediction im Schweizer Online-Journalismus: Eine Soziale Netzwerkanalyse von 20 Minuten (2020–2024)**

Dieses Projekt untersucht die redaktionellen Interaktionsmuster und Themenstrukturen des reichweitenstärksten Schweizer Pendler- und Online-Mediums *20 Minuten*. Anhand eines eigens gecrawlten Volltext- und Metadaten-Korpus von über 449'000 Artikeln (fokussiert auf die fünf vollständigen Kalenderjahre 2020 bis 2024) analysieren wir zwei komplementäre Netzwerkmodelle: ein gewichtetes Autoren-Kollaborationsnetzwerk (One-Mode-Projektion eines bipartiten Artikel-Autor-Graphen) sowie ein longitudinales semantisches Keyword-Kookkurrenz-Netzwerk. Wir untersuchen, inwiefern Ressorts isolierte Silos bilden (Assortativität und strukturelle Löcher nach Burt), wie externe Schockereignisse wie die Covid-19-Pandemie die globale Netzwerk-Zentralisierung und modulare Clusterung verändern, und evaluieren im Längsschnitt prädiktive Link-Prediction-Algorithmen zur Vorhersage zukünftiger journalistischer Kooperationen.

### Teammitglieder (min. 2, max. 3)

- Elias
- Luca

## Datenquelle

Woher kriegen Sie Ihre Daten?

Die Datenbasis stammt direkt von der Online-Plattform von *20 Minuten* (https://www.20min.ch). Über einen eigens implementierten mehrstufigen Web-Crawler wurden sämtliche öffentlich über die Sitemap gelisteten Artikel-URLs ab Oktober 2003 bis September 2025 vollständig erfasst. Anschliessend wurden über einen parallelen Extraktions-Pipeline-Prozess mit trafilatura und BeautifulSoup strukturierte Volltexte und Metadaten (Titel, Lead, Autor:innen, Ressort, Publikationszeitstempel, Leserinteraktionen wie Likes, Shares, Kommentare sowie bereinigte Substantiv-Schlagwörter via spaCy POS-Tagging) extrahiert und persistent gespeichert.

Dürfen Sie die Daten einsammeln und verwenden. Welche Dokumente (AGBs, Terms of use, robots.txt usw.) wurden berücksichtigt, um diese Frage zu beantworten?

Die Datenerhebung erfolgte ausschliesslich für nicht-kommerzielle, akademische Forschungszwecke im Rahmen dieses FHNW-Moduls. Die robots.txt von 20min.ch wurde geprüft: Die allgemeinen Inhaltsseiten und Sitemaps sind für Web-Scraper zugänglich. Zur Wahrung der technischen Verhältnismässigkeit und des Datenschutzes wurden folgende Massnahmen implementiert:
1. Technische Schonung: Einsatz von Concurrency-Begrenzung und exponentiellem Backoff bei Server-Verzögerungen, um die Serverlast minimal zu halten.
2. Anonymisierung und Aggregation: Analyse von Redaktionsstrukturen erfolgt auf aggregierter Netzwerkebene. Es werden keine privaten Profildaten natürlicher Personen ausserhalb der ohnehin öffentlich sichtbaren Autorenzeilen (Bylines) ausgewertet.
3. Nicht-Kommerzialität: Sämtliche Daten verbleiben lokal im Forschungsprojekt und werden nicht kommerziell weiterverbreitet.

Ist der Zugang zu den Daten limitiert? (beispielsweise haben APIs häufig Zugriffs-Limitierungen wie beispielsweise maximal 100 Anfragen pro Tag). Falls ja, inwiefern schränkt Sie dies ein? Wie gehen Sie damit um, damit dies nicht zu einem Problem wird?

Da keine offizielle öffentliche REST-API von *20 Minuten* existiert, erfolgte der Zugriff direkt über HTTP-Requests auf die Web-Sitemap und die HTML-Artikelseiten. Mögliche Einschränkungen (Rate Limits, IP-Throttling oder temporäre 429/503-Statuscodes) wurden durch folgende Architektur gelöst:
- Lokale Persistenz der Rohdaten: Alle extrahierten Daten wurden sofort in lokalen CSV- und Parquet-Dateien (20min_metadaten_keywords.csv) zwischengespeichert.
- Idempotente Wiederaufnahme: Der Scraper prüft bereits vorhandene URLs ab und setzt bei Unterbrüchen exakt am letzten gespeicherten Datum an, wodurch wiederholte Anfragen an dieselben Seiten vermieden wurden.
- Vollständigkeit: Die Datenerhebungsphase ist für den Zeitraum 2020 bis 2024 bereits zu 100% abgeschlossen, sodass für die nachfolgenden Netzwerkanalysen keine weiteren Live-Zugriffe mehr erforderlich sind.

## Datenmodellierung

Was bildet in Ihrem Netzwerk die Knoten? Welche Bedeutung(en) haben die Kanten? Handelt es sich um ein One-Mode oder Two-Mode Netzwerk? Planen Sie verschiedene Modellierungen?

Wir modellieren zwei komplementäre Graphstrukturen:

1. **Modell A: Bipartites Autoren-Artikel-Netzwerk (Two-Mode) und Koautorenschaft (One-Mode-Projektion)**
   - **Two-Mode:** Knotenmenge 1 sind menschliche Journalist:innen, Knotenmenge 2 sind Artikel. Kanten repräsentieren Urheberschaft.
   - **One-Mode-Projektion:** Ungerichteter, gewichteter Graph G_collab = (V, E), in welchem Knoten ausschliesslich individuelle Journalist:innen repräsentieren (institutionelle Nachrichtenagenturen wie SDA, dpa, Reuters werden explizit herausgefiltert). Eine Kante existiert, wenn zwei Personen mindestens einen gemeinsamen Artikel verfasst haben. Die Kanten werden mit der etablierten Newman-Kollaborationsgewichtung gewichtet:
     w_{ij} = \sum_{k \in V_{ij}} rac{1}{|U_k| - 1}
     wobei |U_k| die Anzahl beteiligter Autor:innen an Artikel k ist.

2. **Modell B: Semantisches Keyword-Kookkurrenz-Netzwerk (One-Mode)**
   - Knoten sind die Top 1'200 bereinigten Substantive und Eigennamen (clean_terms) eines einheitlichen globalen Vokabulars für 2020 bis 2024.
   - Kanten verbinden Begriffe, die im selben Artikel gemeinsam auftreten, gewichtet nach Salton-Kosinus-Assoziation:
     w_{uv} = rac{|A_u \cap A_v|}{\sqrt{|A_u| \cdot |A_v|}}
   - Das Netzwerk wird über gegenseitige k-Nächste-Nachbarn (Mutual k-NN mit k=10) sparsifiziert, um eine robuste, über Jahre hinweg topologisch vergleichbare Dichte sicherzustellen.

Mit welcher Netzwerk-Grösse rechnen Sie? (Brechen Sie die Abschätzung auf den Typ herunter, falls sie ein Two-Mode Netzwerk verwenden):

| Netzwerktyp | Anzahl Knoten (geschätzt) | Anzahl Kanten (geschätzt) |
|---|---:|---:|
| Modell A: Autoren-Kollaboration (One-Mode) | ca. 800 – 1'200 Journalist:innen | ca. 3'000 – 6'000 Kollaborationskanten |
| Modell B: Keyword-Kookkurrenz (One-Mode, Top 1200) | 1'200 Begriffe | ca. 6'000 – 12'000 Assoziationskanten |

Welche Attribute haben Sie auf den Knoten und Kanten? Geben Sie für jedes Attribut, welches Sie in ihren Analysen verwenden, eine Prognose an, was für eine Datenqualität / Probleme Sie nach Ihren ersten Untersuchungen erwarten. (Wie vollständig sind die Daten, wie korrekt sind die Daten, gibt es unterschiedliche Schreibweisen für dasselbe Konzept usw.)

- **Knotenattribute Autoren:**
  - name: Vollständiger Name der Journalist:in. Datenqualität: Gut, erfordert jedoch Filterung von Autorenkürzeln (<= 3 Zeichen), Platzhaltern (Undefined Undefined) und institutionellen Agenturen.
  - dominant_ressort: Das Fachressort, in welchem die Person die relative Mehrheit ihrer Artikel publiziert hat. Datenqualität: Hoch (über 98% eindeutig zuordenbar).
  - article_count: Gesamtanzahl verfasster Artikel. Datenqualität: Vollständig.
  - ressort_distribution: Diskreter Wahrscheinlichkeitsvektor p_i über alle Ressorts. Datenqualität: Vollständig.

- **Kantenattribute Kollaboration:**
  - weight: Newman-Kollaborationsgewicht. Datenqualität: Exakt deterministisch berechnet.
  - jsd_divergence: Jensen-Shannon-Divergenz JSD(p_i || p_j) in [0, 1] zwischen den Ressort-Profilen der Koautor:innen. Datenqualität: Exakt.

- **Kantenattribute Keywords:**
  - weight: Normalisierte Kosinus-Assoziationsstärke. Datenqualität: Hoch, da Stoppwörter und redaktionelle Floskeln zuvor gefiltert wurden.

Leiten Sie aus gesammelten Daten neue Attribute ab (z.B. Kategorisierung verschiedener Werte, Extraktion von Alter anhand der Jahreszahl, usw.)? Falls ja, welches sind diese neuen Attribute und wie sieht Ihre Strategie aus, diese abzuleiten? Welche Datenqualität erwarten Sie?

1. **dominant_ressort pro Autor:in:** Abgeleitet via Pluralitätszählung über alle publizierten Artikel pro Person. Bei Gleichstand entscheidet deterministisch das jüngste Publikationsdatum.
2. **ressort_distribution (p_i):** Normalisierter Häufigkeitsvektor der Ressorts pro Journalist:in zur quantitativen Erfassung interdisziplinärer thematischer Mobilität.
3. **jsd_divergence:** Informationstheoretische Jensen-Shannon-Divergenz zwischen den Ressortvektoren zweier kooperierender Personen zur mathematisch schwellenwertfreien Quantifizierung von Fachgrenzen-Überschreitung.
4. **is_agency:** Boolesches Attribut zur Trennung von Nachrichtenagenturen (SDA, dpa, Reuters, AFP) und realen Journalist:innen.

## Analysen

Beschreiben Sie in diesem Abschnitt, was sie wie analysieren möchten. Verwenden Sie für jede Analyse die dafür vorgegebene Tabelle. Jede Analyse soll in einer eigenen Tabelle beschrieben werden.

### Analyse 1: Redaktionelle Silobildung, Homophilie und strukturelle Brokerage (LE3, LE5, LE7)

|  |  |
|---|---|
| These / Frage: | Bilden Fachressorts bei 20 Minuten geschlossene Kooperations-Silos (Homophilie), welche Akteure fungieren als strukturelle Broker (Betweenness Centrality), und unterscheidet sich das interdisziplinäre Kooperationsniveau signifikant vom Zufall? |
| Filterung: | Zeitraum 2020–2024. Ausschluss von Nachrichtenagenturen und Autorenkürzeln (<= 3 Zeichen). Mindestaktivität: >= 2 publizierte Artikel. |
| Analyse: | 1. Berechnung des nominalen Assortativitätskoeffizienten nach Newman (r_ressort) auf dominant_ressort. Signifikanztest via Node-Label-Permutation (B=5'000 Permutationen bei fixer Topologie).<br>2. Berechnung von Degree Centrality und Betweenness Centrality zur Identifikation von Schlüssel-Brokern (Schliessen struktureller Löcher nach Burt).<br>3. Test der mittleren Kanten-JSD gegen ein gradtreues Nullmodell (Maslov-Sneppen Double-Edge-Swap Rewiring).<br>4. Sekundäre Leave-One-Out-Regression (OLS mit robusten Standardfehlern) von Kanten-JSD auf Artikel-Shares unter Kontrolle von Ressort, Jahr und Teamgrösse. |
| Erwartung: | Wir erwarten eine statistisch hochsignifikante positive Assortativität (r > 0, p < 0.001), was auf starke Silos hinweist. Gleichzeitig erwarten wir vereinzelte redaktionelle Brückenpersonen mit überproportional hoher Betweenness Centrality, deren Kooperationen eine messbar höhere thematische Reichweite erzielen. |

### Analyse 2: Makro-Topologie und Krisen-Evolution der Berichterstattung 2020–2024 (LE4, LE6)

|  |  |
|---|---|
| These / Frage: | Wie veränderte der externe Schock der Covid-19-Pandemie im Jahr 2020 die makro-topologische Struktur und Zentralisierung des Themennetzwerks, und wie entwickelte sich das Netzwerk in den Folgejahren 2021 bis 2024? |
| Filterung: | Jeweils vollständige Kalenderjahre 2020 bis 2024. Identisches globales Vokabular der Top 1'200 bereinigten Substantive. Sparsifizierung über Mutual k-NN (k=10, Sensitivitätsanalyse für k in {5, 10, 20}). |
| Analyse: | 1. Berechnung globaler Kennzahlen auf der Riesenzusammenhangskomponente (Giant Component): Dichte, Durchmesser, durchschnittliche Pfadlänge (Distanztransformation d = 1/w), Clustering-Koeffizient.<br>2. Berechnung der normalisierten Freeman-Grad-Zentralisierung (C_D) und Betweenness-Zentralisierung (C_B) pro Jahr.<br>3. Community Detection mittels Louvain-Algorithmus (10 Random Seeds zur Prüfung der Partitionsstabilität, Angabe von Modularity Q +/- std). |
| Erwartung: | Im Krisenjahr 2020 erwarten wir eine maximale Zentralisierung und minimale Modularität (Q), da verschiedenste Themenfelder im Pandemie-Komplex zusammenliefen. Für 2021 bis 2024 erwarten wir eine sukzessive Dezentralisierung und stärkere modulare Ausdifferenzierung eigenständiger Themen-Cluster. |

### Analyse 3: Rolling Temporal Link-Prediction im Koautorenschafts-Netzwerk (LE8)

|  |  |
|---|---|
| These / Frage: | Welche netzwerkanalytischen Mechanismen können das Entstehen neuer redaktioneller Kooperationen im Folgejahr am besten vorhersagen: lokale Schliessung von Triaden (Adamic-Adar) oder reine Popularität (Preferential Attachment)? |
| Filterung: | Rolling Temporal Windows: (2020–21 -> 2022), (2020–22 -> 2023), (2020–23 -> 2024). Berücksichtigung aller aktiven Autor:innen (>= 2 Artikel im Trainingsfenster, >= 1 im Testjahr). Unbalancierte Evaluation über alle im Trainingsfenster unverbundenen Kandidatenpaare. |
| Analyse: | 1. Implementierung und Vergleich von Link-Prediction-Heuristiken: Common Neighbors (CN), Jaccard Coefficient (JC), Adamic-Adar (AA) und Preferential Attachment (PA) sowie Random-Baseline.<br>2. Quantitative Leistungsbewertung primär über Average Precision (PR-AUC) und Precision@k (k in {20, 50, 100}) sowie sekundär über ROC-AUC.<br>3. Statistische Absicherung der Leistungsunterschiede via 1'000 Bootstrap-Resamples. |
| Erwartung: | Wir erwarten, dass der Adamic-Adar-Index eine signifikant höhere Average Precision erzielt als Preferential Attachment. Dies würde empirisch belegen, dass neue Kooperationen in der Redaktion primär über gemeinsame Dritte und dichte Triadenstrukturen entstehen statt über das Verfassen mit ohnehin bereits hochgradigen Einzelautor:innen. |

## Fragen und Unklarheiten?

1. **Bestätigung des Einreichungstermins:** Im Modulbeschrieb wird der Abgabetermin für Portfoliokompetenzen jeweils semesterweise geführt (Projektbeschreibung: Ende Semester; Portrait: Januar). Wir streben die finale Fertigstellung auf den regulären Semesterabschluss an.
2. **Anerkennung des Web-Crawlers als Bonusleistung:** Wir bitten um Bestätigung im Rahmen des Meilenstein-Feedbacks, dass die technische Eigenleistung der Sitemap- und Volltext-Pipeline über 449'000 Artikel für die maximale Bonus-Einstufung (+0.5 Punkte) berücksichtigt wird.
