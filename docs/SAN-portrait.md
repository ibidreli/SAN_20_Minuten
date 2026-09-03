Wegleitung

Soziale Netzwerke und sowie weitere Daten, welche als Graphen modelliert werden können, sind allgegenwärtig. Auf diesen Graphstrukturen können sehr vielfältige Analysen durchgeführt werden. Einerseits können explorative / visuelle Analysen durchgeführt werden, um wichtige Personen oder Personengruppen zu finden. Jedoch ermöglicht die Soziale Netzwerkanalyse auch die Anwendung inferentieller Statistik, um zu beurteilen, welche Faktoren die Interaktion signifikant beeinflusst haben. Dank Link-Prediction Algorithmen können Vorschläge generiert werden, welche Kanten sich in Zukunft bilden werden (z.B. Freundesvorschläge auf Social Media Plattformen). Weitere interessante Anwendungsgebiete sind das Semi-Supervised Learning von unbekannten Knoten-Attributne oder die Simulation, wie sich Meinungen oder Krankheiten in einem Graphen ausbreiten.

Was erwartet Dich?

"Soziale Netzwerke Analysieren" ist eine Portfoliokompetenz. Das heisst, Du wirst die Lernergebnisse durch verschiedene, selbst zusammengestellte Aufgaben über mehrere Semester hinweg bearbeiten.

Die Kompetenz "Soziale Netzwerke Analysieren" umfasst 9 Lernergebnisse (siehe Kompetenzbeschreibung). Nachfolgend ist aufgeführt, was Dich erwartet, wenn Du auf die einzelnen Lernergebnisse hinarbeitest.

Das referenzierte Script wie auch die Jupyter Notebooks findest du in der Mediathek.

LE1 - Soziologische Aspekte &amp; Anwendungsfälle der Sozialen Netzwerk Analyse

Ziel

Du kennst grundlegende Theorien was Menschen dazu bewegt, miteinander in Kontakt zu treten und sich auszutauschen. Zudem hast Du erste Berührungspunkte mit typischen Anwendungsfälle von Sozialer Netzwerk Analyse.

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie:

Du kannst erklären, weshalb Menschen sich "verknüpfen" und kennst die "Looking Glass Self", "The Self, I &amp; Me" Theorien sowie auch die Maslowsche Bedürfnispyramide.

Du kennst die "Exchange Theorie" &amp; die sieben Social Forces

Du kennst die Begriffe Tie Strenght, Structural Hole und Social Capital

Du kennst die Grundfunktionalitäten von Sozialen Netzwerken im Internet und verstehst, was Leute dazu bewegt, darin sehr aktiv zu sein.

Du kennst verschiedene Anwendungsfälle von Sozialer Netzwerkanalyse

Was NICHT erwartet wird

Du brauchst dir keine Namen oder Jahreszahlen zu merken

Zu erarbeitende Unterlagen

Skript, Kapitel 1: Aspekte der Soziologie 2: Modellierung Sozialer Netzwerke

Skript, Kapitel 2: Anwendungsfälle von Sozialer Netzwerkanalyse

Übungen

LE2 - Tool Installation &amp; Einarbeitung in Tools zur Sozialen Netzwerk Analyse

Ziel

Du hast ein erstes Beispiel-Netzwerk mit Hilfe eines Tutorials Schritt für Schritt untersucht (auch wenn Du noch nicht alles im Detail verstehst). Zudem hast Du eine Python-Umgebung, in welcher die verwendeten Libraries installiert wurden und das erste Beispiel-Notebook ausgeführt werden kann.

Im Selbststudium zu erarbeiten

Installation der Tools &amp; Einführung in Tools (siehe Übungen) - Referenziertes Video in den Übungen findest du in der Mediathek: Einführung in Gephi

Notebooks

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und Selbststudium erarbeitet und die Übungen gemacht hast:

Praxis:

Du hast Gephi installiert

Du hast das Gephi Tutorial erarbeitet und bist in Kontakt gekommen mit: Datenset laden, Datenset im Data Laboratory ansehen, Graph layouten, Graph filtern, Berechnungen auf dem Graph durchführen sowie ein Two-Mode Netzwerk in ein One-Mode Netzwerk umzuwandeln.

Du hast Python installiert und konntest das Notebook 02_Basics (im Hauptverzeichnis unter Notebooks) ausführen.LE3 - Netzwerk-Modellierung &amp; Filterung

LE3 - Netzwerk-Modellierung &amp; Filterung

Ziel

Du bist in der Lage, für bestehende Daten eine geeigneten Netzwerk-Modellierung (One-Mode, TwoMode, Multirelational) zu definieren und umzusetzen. Du kannst Two-Mode Netzwerke anhand verschiedener Transformationen in ein One-Mode Netzwerk umwandeln. Zudem bist Du in der Lage, grosse Netzwerke auf verschiedene Arten zu reduzieren.

Zu erarbeitende Unterlagen

Skript, Kapitel 3: Modellierung Sozialer Netzwerke

Skript, Kapitel 4: Reduktion von Netzwerken

Übungen

Tools:

Die Umwandlung von einem Two-Mode in ein One-Mode Netzwerk ist in der Übungsaufgabe 2 bei der Übung "Erste Schritte mit Gephi" (LE: Tool-Installation) beschrieben.

NetworkX: Öffne die Notebooks unter 03 Modelling. Das "Modelling" Notebook beinhaltet verschiedene Modellierungen wie auch die Transformationen von TwoMode in One-Mode Netzwerke. Das "Filtering &amp; Drawing" Notebook zeigt, wie die Netzwerkgrösse reduziert werden kann. Zusätzlich hat es noch ein paar CodeSnippets für visuelle Hervorhebungen von bestimmten Eigenschaften.

Video: Kanten &amp; Kanten-Eigenschaften (ca. ab 4:45) dient als Ergänzung des Skripts und ist in der Mediathek verfügbar. Video-Erklärungen (Inhalt) sind nicht zwingend deckungsgleich mit Skript.

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du kennst die verschiedenen Formen ein Netzwerk zu modellieren (One-Mode, Two-Mode, Knoten- resp. Kantenattribute, Gerichtet / Ungerichtet, Gewichtet / Ungewichtet usw.)

Du kennst die verschiedenen Transformationen, wie ein Two-Mode in ein One-Mode Netzwerk umgewandelt werden kann.

Du kennst verschiedene Möglichkeiten, um die Grösse des Netzwerk zu reduzieren.

Praxis (entweder Gephi oder Python):

Du kannst ein Netzwerk mit Knoten- und Kantenattributen modellieren.

Du kannst ein Two-Mode Netzwerk in ein One-Mode Netzwerk umwandeln. NetworkX kann alle Transformationen durchführen. Gephi ist da weniger flexibel und stösst bei grösseren Graphen auch schnell an seine Grenzen.

Du kannst das Netzwerk anhand von Knoten- &amp; Kantenattributen verringern.

LE4 - Communities in Netzwerken entdecken

Ziel

Du kennst verschiedene Ansätze zur Entdeckung von gut verbundenen Gruppen innerhalb eines Netzwerks. Du kannst diese mit einem Tool anwenden und die identifizierten Gruppen ausgeben resp. visuell hervorheben.

Zu erarbeitende Unterlagen

Skript, Kapitel 5: Communities - Es gibt eine Übung zu Gephi und ein Notebook (unter "04 Subgroups") welches zeigt, wie Communities mit NetworkX gefunden und eingefärbt werden können.

Übungen &amp; Notebooks

Video-Erklärungen in der Mediahthek dienen als Ergänzung des Skripts. Die Inhalte sind nicht zwingend deckungsgleich mit dem Skript:

Edge Betweenness berechnen

Connected Components (ca. ab 15:30)

Cliques, k-Core, n-cliques

Edge Betweeness Clustering (ab 5:45)

Modularity &amp; Louvain Algorithmus

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du weisst, was ein (Strongly) Connected Coponent ist und kannst diesen identifizieren.

Du kennst den Begriff "Giant Component"

Du kennst die Begriffe Clique, k-core, p-clique und n-clique und kannst solche Communities in einem gegebenen Graphen erkennen.

Du kennst verschiedene Community Detection Algorithmen (Girvan-Newman Clustering, Label Propagation, Louvain Algorithmus). Die ersten beiden solltest Du von Hand ausführen können und beim letzten die Funktionsweise verstehen

Praxis

Du kannst mit einem Tool die Communities berechnen und den Graphen. Zudem kannst du die berechneten Communities visuell hervorheben oder den Graphen so filtern, dass nur noch der Subgraph einzelner Communities dargestellt wird.

LE5 - Zentrale Aktoren &amp; Aktor-Gruppen finden

Ziel

Du kennst verschiedene Algorithmen und somit Definitionen für zentrale Aktoren in einem Netzwerk. Du kannst die Algorithmen von Hand ausführen und bist in der Lage, in einem Netzwerk mit Hilfe von Tools die zentralen Aktoren zu identifizieren und hervorzuheben / auszugeben.

Zu erarbeitende Unterlagen

Kapitel 6: Wichtigkeit von Knoten &amp; Knoten-Gruppen

Übungen - Es gibt eine Übung zu Gephi wie auch ein Jupyter Notebook unter "04 Centrality".

Video-Erklärungen in der Mediathek zu gewissen Themen

Betweenness Centrality

Degree Centrality (ab 12:00)

Degree Centrality &amp; Normalisierung (ab 9:10)

Betweenness Centrality (ab 19:15)

Closeness Centrality (ab 23:40)

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du kannst die im Script behandelten Aktor- und Gruppen-Zentralitätsmasse sowie Prestige Masse von Hand berechnen und interpretieren

Praxis

Du kannst in die Aktor-Zentralität berechnen und die zentralen Aktoren hervorheben / ausgeben.

LE6 - Netzwerk-Kennzahlen (Metriken, Zentralisierung, Connectivity)

Ziel

Du kennst die verschiedenen Netzwerk-Kennzahlen und kannst diese interpretieren. Bei den Metriken und Zentralisierung ist es einfacher, wenn verschiedene Messwerte (z.B. gleiches Netzwerk zu unterschiedlichen Zeitpunkten) zur Verfügung stehen, da so ein Vergleich gegeben ist.

Zu erarbeitende Unterlagen

Kapitel 7: Netzwerk-Zentralisierung

Kapitel 8: Netzwerk-Metriken

Kapitel 9: Connecivity

Übungen &amp; Notebooks

Video Netzwerk Zentralisierung (ca. ab 11:00) in der Mediathek dient der Ergänzung des Skripts, die Inhalte sind nicht zwingend deckungsgleich

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du verstehst die allgemeine Formel zur Berechnung der Netzwerk Zentralisierung.

Du kannst die Netzwerk-Zentralisierung für die im Script (Kapitel 7) angegebenen Zentralitätsmasse berechnen und interpretieren (v.a. im Vergleich mit anderen Messwerten)

Du kennst Netzwerk-Metriken wie Diameter, Density, Balance oder Cluster Coeffizient, kannst diese interpretieren und bist in der Lage zu entscheiden, wann deren Anwendung sinnvoll ist

Du kennst die Begriffe Cut-Vertex, Bridge, k-connected (für Nodes) und Edge Connectivity (für Edges).

Praxis

Du kannst mit einem Tool (Gephi oder Python) die Netzwerk-Metriken berechnen und ausgeben.

Du kannst in Python mit der networkX Library die Node und Edge Connectivity ausgeben, resp. diejenigen Knoten / Kanten, welche dazu führen, dass der Graph nicht mehr zusammenhängend ist.

LE7 - Statistik in Netzwerken

Ziel

Du kennst die lineare Korrelation wie auch die Rangkorrelation und kannst diese mit Hilfe von ToolUnterstützung berechnen und das Resultat interpretieren. Du arbeitest bedacht, so dass Du die typischen Fehler bei Analyse von Korrelationen vermeiden kannst. Du bist in der Lage, Korrelationen mit Permutations-Tests in Netzwerken auf Signifikanz zu untersuchen und kannst bei Multirelationalen Netzwerken feststellen, welche Faktoren schlussendlich signifikant zur schlussendlichen Netzwerkstruktur beigetragen haben.

Zu erarbeitende Unterlagen

Kapitel 10: Korrelation in Netzwerken

Kapitel 11: Inferenzielle Statistik in Netzwerken

Übungen &amp; Notebooks

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du kannst beschreiben, was eine Korrelation und der Korrelationskoeffizient r aussagt.

Du kannst die Person Korrelation und Spearman Rang Korrelation (mit der vereinfachten Formel im Script) von Hand berechnen.

Du weisst, wie das Bestimmtheitsmass r2 zu interpretieren ist.

Du kennst die üblichen Fehler im Zusammenhang mit Korrelation

Du kennst die Unterschiede zwischen monadischen, dyadischen und mixed monadischen-dyadischen Hypothesentests und kannst diese ausführen.

Du weisst, wie nummerische Knoten-Attribute mit einem Permutations-Test auf Signifikanz überprüft werden können.

Du weisst, wie die Korrelation von Knotenattributen mit QAP auf Signifikanz überprüft werden können.

Du kennst ein paar Strategien, wie Knoten-Attribute als Kantenattribute in einer Adjazenzmatrix abgebildet werden können, um im Anschluss eine Analyse mit QAP auf Signifikanz zu prüfen

Praxis

Du kannst in Netzwerken Knoten-Attribute auf signifikante Korrelation überprüfen (Permutations-Test).

Du kannst in Netzwerken Kanten-Attribute auf signifikante Korrelation überprüfen. (QAP)

Due kannst, sofern sinnvoll, Knotenattribute als Kanten abbilden, um einen Mixed Monadischen-Dyadischen Hypothesentest auszuführen.

LE8 - Link Prediction

Ziel

Du kennst verschiedene Link-Prediction Algorithmen und kannst diese von Hand berechnen wie auch mit einem Tool ausführen. Zudem bist Du in der Lage, anhand von historischen Daten ein Experiment durchzuführen und zu zeigen, welche Link-Prediction Algorithmen wie gut in diesem Anwendungsfall funktionieren.

Zu erarbeitende Unterlagen

Im Kapitel 12: Link Prediction

Übungen &amp; Notebooks

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du kennst die im Script erklärten Link-Prediction Algorithmen und kannst von Hand Vorhersagen für zukünftige Kanten berechnen.

Du kennst den Experimenten-Aufbau, wie Du anhand historischer Daten evaluieren kannst, welcher Link-Prediction Algorithmus wie gut funktioniert hätte.

Praxis

Du kannst die verschiedenen Link-Prediction Algorithmen ausführen und die Vorhersage mit den tatsächlichen Werten vergleichen (falls diese vorhanden sind).

LE9 - Diffusion

Ziel

Du kennst ein paar einfache Modelle, wie sich Informationen oder Krankheiten verbreiten. Du bist zudem in der Lage, diese einfachen Diffusions-Modelle in Python auf Netzwerken anzuwenden.

Zu erarbeitende Unterlagen

Im Kapitel 13: Diffusion

Übungen

Beispiele für die erlernten Modelle mit NDLib &amp; NetworkX

Optional: Unter Visualisierung wird noch gezeigt, wie der Diffusions-Prozess visualisiert werden kann

Lernziele

Das wird von Dir erwartet, nachdem Du dir den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht hast:

Theorie

Du kannst die Eigenschaften und Beispiel-Situationen des Information Cascade DiffusionsModells beschreiben. Zusätzlich kannst Du berechnen, welche Knoten initial selektiert werden müssen, um eine maximale Ausbreitung zu erreichen.

Du kennst weitere einfache Modelle wie das Voter Modell oder das Threshold Modell. (Für Interessierte: Auf der NDLib Webseite hat es noch viele weitere Modelle; ebenfalls solche, um die Ausbreitung von Epidemien zu modellieren).

Praxis

Du kannst die Beispiele zu den betrachteten Diffusions-Modellen mit NDLib simulieren.

LE 10: Graphlets

Ziel

Sie wissen, was Graphlets sind und können damit Graphen und Knoten auf Strukturelle Ähnlichkeit prüfen resp. ähnliche Knoten / Netzwerke gruppieren. Sie können die strukturellen Eigenschaften von Knoten und Graphen als Vektoren abbilden.

Zu erarbeitende Unterlagen

- Im Kapitel 14: Graphlets

- Übungen zum LE

- Jupyter Notebooks zu Graphlets

Lernziele:

Das wird von Ihnen erwartet, nach dem Sie die den Stoff aus dem Unterricht und dem Selbststudium erarbeitet und die Übungen gemacht haben:

Theorie:

- Sie wissen, was Graphlets sind und solche in einem Netzwerk identifizieren.

- Sie können die "Relative Graphlet Frequency Distance" von Hand berechnen.

- Sie wissen, was ein Graphlet Degree Vector ist.

- Sie können den Graphlet Degree Vector für einen gegebenen Knoten von Hand berechnen.

Praxis:

- Sie können Graphlet Degree Vektoren mit Hilfe von bestehendem Code auf kleinen Netzwerken berechnen und mit Hilfe von t-SNE (oder einer anderen Dimensions-Reduktion) dann die strukturelle Ähnlichkeit von Knoten in einem 2d Scatterplot nachvollziehen.

Aufbau und Lernaufwand

LE1 - Soziologische Aspekte &amp; Anwendungsfälle der Sozialen Netzwerk Analyse: 11%

LE2 - Tool Installation &amp; Einarbeitung in Tools zur Sozialen Netzwerk Analyse: 10%

LE3 - Netzwerk-Modellierung &amp; Filterung: 10%

LE4 - Communities in Netzwerken entdecken: 10%

LE5 - Zentrale Aktoren &amp; Aktor-Gruppen finden: 10%

LE6 - Netzwerk-Kennzahlen: 10%

LE7 - Statistik in Netzwerken: 10%

LE8 - Link Prediction: 10%

LE9 - Diffusion: 10%

LE10 - Graphlets: 10%

Grundsätzlich ist empfohlen, die Lernergebnisse in der nummerisch aufsteigenden Reihenfolge abzuarbeiten, auch wenn nicht alle LEs aufeinander aufbauen.

Die Abhängigkeiten sind wie folgt definiert:

Zuerst sollte LE1, LE2 und LE3 erledigt werden (Einstieg ins Thema, Umgebung einrichten, Modellierung der Graph Struktur)

LE 6 baut auf LE 5 auf (Aktor Zentralität =&gt; Netzwerk Zentralisierung)

LE 7 baut auf LE 5 auf (Korrelation zwischen Zentralitäts-Werten u. Aktor-Attributen)

LE 8 baut auf LE 4 auf (Nutzen von Community-Info für Link-Prediction)

LE 9 baut auf LE 4 auf

Kompetenznachweis

Übersicht Kompetenznachweis

Schriftliche Prüfung

Praktische Arbeit

Detaillierte Angaben zum Kompetenznachweis

Der Kompetenznachweis erfolgt durch zwei Leistungsnachweise ausserhalb der Prüfungswochen.

Die Modulnote setzt sich wie folgt zusammen:

Schriftliche Prüfung: 40 %

Praktische Arbeit: 60 %

Spielregeln

Schriftliche Prüfung (40% gewichtet)

Der Prüfungstermin ist der folgende:

Freiwilliger vorgezogener Prüfungstermin (für diejenigen, welche sich die Lerninhalte vor der zweiten Semesterwoche angeeignet haben):

Tag / Datum: Montag, 21. September 2026

Zeit: 11:10 - 12:00

Raum: TBD

Regulärer Prüfungstermin: 

Tag / Datum: Mittwoch, 4. November 2026  (jeweils in der 8. Semesterwoche)

Zeit: 14:15 - 15:00

Raum: TBD

Stoffumfang: ab LE3

Erlaubte Unterlagen:

1 A4 Blatt vorne und hinten beschriftet / bedruckt

Formelsammlung (werde ich euch ausdrucken): Netzwerkanalyse Formelsammlung

Hinweis: Orientiere Dich an den Übungen. Die Prüfungsaufgaben werden in einer ähnlichen Form gestellt werden. Es geht vor allem darum zu prüfen, ob die Inhalte verstanden wurden. Es können kleinere Praxisaufgaben enthalten sein, jedoch wird die praktische Anwendung vor allem mit der praktischen Arbeit geprüft.

Kurzprüfungen: Hier findest du verschiedene Kurzprüfungen zum Üben: Kurztests

Praktische Arbeit (60% gewichtet)

Du führst selbständig eine Soziale Netzwerkanalyse durch. Dazu gehört, dass Du eine geeignete Datenquelle suchst, die Informationen automatisiert in eine Graph-Struktur überführst und verschiedene Analysen darauf ausführst. Beurteilt wird die korrekte Durchführung der gesamten Analysen wie auch die Kreativität / Vielfältigkeit.

Die detaillierte Projektbeschreibung findest du im Abschnitt zur praktischen Projektarbeit (Ad Hoc Aufgabe), das Bewertungsraster im Anschluss.

Termine:

Abgabe Projekt: Spätestens Sonntag, 3.1.2027, 23:59:59 Uhr

Auf Nachfrage meinerseits: Projektbesprechungen in den beiden verbleibenden Semesterwochen

Wie wirst du unterstützt?

Der Kompetenzerwerb soll grundsätzlich selbständig durchgeführt werden, jedoch wird folgende Unterstützung angeboten*: 

Kontaktstunde

Während des Semesters stehe ich Dir am in der Kontaktstunde zur Verfügung. Ausserhalb der Kontaktstunde bin ich gut per E-Mail oder MS Teams Chat erreichbar. (siehe nächster Abschnitt)

Individueller Support

Gerne biete ich auch individuelle Unterstützung ausserhalb der regulären Sprechstunde an.

* Generell ist es hilfreich, wenn ihr mich zuvor informiert, wo es Unklarheiten gibt. So habe ich die Möglichkeit, für die Sprechstunde weitere Beispiele vorzubereiten.