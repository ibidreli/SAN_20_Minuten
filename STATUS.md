# STATUS: SAN-Projekt 20 Minuten

**Stand:** 2026-09-17, verifiziert durch Ausführung der Checks, nicht aus dem Gedächtnis
**Branch:** `2-featurecleaning`, letzter Commit `f1fe17c`
**Team:** Elias, Luca

> Dieses Dokument ist das Lagebild. Die **offenen Punkte werden in `TODO.md`
> geführt**, dort stehen die Checklisten im Detail. Hier steht nur, wo das
> Projekt insgesamt steht und was davon geprüft ist.

---

## 1. Kurzfassung

Analyse, Code und Notebook sind fertig und über vier Review-Runden abgesichert.
Die Abgabe ist trotzdem **nicht möglich**, weil zwei Pflichtbestandteile fehlen,
die nicht aus dem Code entstehen: die KI-Deklaration mit Prompts und die
aufgezeichnete Präsentation.

| Bereich | Zustand |
|---|---|
| Analyse, Code, Notebook | fertig und verifiziert |
| Reproduzierbarkeit | hergestellt (Tests, Manifest, Qualitätsgate) |
| KI-Deklaration mit Prompts | **fehlt, blockierend, Risiko Note 1** |
| Aufgezeichnete Präsentation | **fehlt, wird primär bewertet** |
| Gephi-Bilder (LE2) | fehlen |
| Arbeitsstand committet | **nein, 9 geänderte und 2 neue Dateien** |
| Abgabepaket | veraltet, muss neu gebaut werden |

---

## 2. Heute verifizierte Checks

Alle vier Kommandos wurden am 2026-09-17 ausgeführt, die Spalte „Ergebnis" ist
die tatsächliche Ausgabe:

| Check | Kommando | Ergebnis |
|---|---|---|
| Unit-Tests | `python src/network_models.py` | **17/17 bestanden** |
| Qualitätsgate | `python scripts/validate_notebook.py` | **7/7 bestanden**, mit bekannter Lücke (siehe 5.2) |
| Datenintegrität | `python scripts/build_manifest.py --check` | **4/4 OK** |
| Notebook | `src/02_analyse.ipynb` | 41 Zellen, **0 Ausführungsfehler**, 14 Abbildungen nummeriert und inline |

---

## 3. Was inhaltlich vorliegt

### 3.1 Datenbasis

- 118'302 bereinigte Artikel, 2020 bis 2024, aus eigenem Crawler
- 781 Journalist:innen nach Entfernung von 166 institutionellen Knoten
- Kollaborationsnetzwerk: 554 Knoten, 2'717 Kanten, Dichte 1.77%
- Riesenkomponente: 361 Knoten (65.2%)
- Ground-Truth-Validierung gegen 20min.ch, n = 60, mit erzeugendem Skript

### 3.2 Abgedeckte Lernergebnisse

| LE | Analyse | Abschnitt |
|---|---|---|
| LE3 | Two-Mode-Modellierung, Newman-Projektion | 1 |
| LE5 | Burt Constraint und Effective Size, Betweenness | 2.1 |
| LE7 | Ressort-Homophilie, Label-Permutation | 2.2 |
| LE7 | Kanten-JSD gegen Maslov-Sneppen-Nullmodell | 2.3 |
| LE7 | QAP, gemeinsame Zeilen- und Spaltenpermutation | 2.4 |
| LE7 | OLS auf Leave-One-Out-JSD | 2.5 |
| LE4, LE6 | Cliquen, k-Core, Artikulationspunkte, Connectivity | 2.6 |
| LE6 | Makro-Metriken, Zentralisierung C_D und C_B | 3.1 |
| LE6 | Sensitivitätsanalyse k in {5, 10, 20} | 3.2 |
| LE4 | Louvain-Communities | 3.3 |
| LE6 | Prüfung Hypothese 2 inklusive Grenzen des Messdesigns | 3.4 |
| LE8 | Rollierende Link-Prediction, fünf Algorithmen | 4 |
| LE9 | Independent-Cascade-Diffusion mit p-Sweep | 5 |

**Nicht abgedeckt:** LE10 (Graphlets), bewusst, im Ausblick benannt.

### 3.3 Zentrale Befunde

- Ressort-Homophilie: r = 0.3621, p = 0.0002, über drei Nullmodelle bestätigt
- Kanten-JSD 0.3355 gegen 0.6199 im gradtreuen Nullmodell
- QAP: r = -0.1393, p = 0.0005
- OLS: N = 6'586, adj. R² = 0.3610, Koeffizient `mean_jsd` = 0.6754
- Link-Prediction: Adamic-Adar PR-AUC 0.1939 gegen Zufall 0.0635, Bootstrap-KI
  der Differenz zu Preferential Attachment [0.0387, 0.0811]
- Diffusion: Negativbefund, die Wahl der Startmenge bringt nichts
- Hypothese 2: nur teilweise bestätigt, die Grenzen des Messdesigns sind
  quantifiziert und offengelegt

---

## 4. Bewertungsraster und Selbsteinschätzung

Maximal 24 Punkte, dazu Bonus bis +0.5 für den eigenen Crawler und Malus bis
-0.2 bei Abgabe nicht über MS Teams.

| Kriterium | Gewicht | Skala | Einschätzung |
|---|---|---|---|
| Explorative Datenanalyse, Quelldaten-Validierung | 1 | 0 bis 2 | voll erfüllt |
| Vielfalt der Netzwerk-Analysen | 2 | 0 bis 5 | voll erfüllt |
| Nachvollziehbarkeit, korrekte Masse, Schlussfolgerungen | 2 | 0 bis 4 | voll erfüllt |
| Anschaulichkeit der Resultate | 1 | 0 bis 2 | voll erfüllt, Gephi-Bilder fehlen |
| Ausblick | 1 | 0 bis 2 | voll erfüllt |

**Wichtig:** Das ist eine Einschätzung, keine Messung. Laut Projektbeschreibung
sind „die Informationen aus der Präsentation und der Schlussbesprechung"
ausschlaggebend. Das Repository kann eine gute Note vorbereiten, aber nicht
sichern.

---

## 5. Offene Punkte

Die Checklisten stehen in `TODO.md`. Hier nur der Stand und was seither
dazugekommen ist.

### 5.1 Blockierend

| Punkt | Stand |
|---|---|
| **KI-Deklaration mit Prompts** | `docs/KI-Deklaration.md` existiert nicht. Notebook-Abschnitt 6.4 trägt weiterhin den Hinweis, dass die Prompts fehlen. Ohne Prompts droht Note 1 für die ganze Gruppe. |
| **Aufgezeichnete Präsentation** | `praesentation/` ist angelegt und leer. Maximal 30 Minuten, Ablauf laut Projektbeschreibung. |
| **Arbeitsstand nicht committet** | 9 geänderte und 2 neue Dateien nur im Arbeitsverzeichnis, darunter `scripts/validate_notebook.py` und `data/notebook_facts.json`. Eine komplette Arbeitsrunde ist ungesichert. |

### 5.2 Lücke im Qualitätsgate

Prüfung [4] in `scripts/validate_notebook.py` sucht jede Zahl aus dem Fliesstext
als **Teilzeichenkette** in den Zellenausgaben. Eine im Test erfundene Zahl kam
durch, weil sie in einer längeren Dezimalzahl enthalten war. Das Gate meldete
trotzdem „Alle Prüfungen bestanden".

Das ist heikel, weil Lessons Learned Nummer 10 und die Evidence Map dem Bewerter
zusagen, das Gate breche ab, sobald eine Zahl im Text in keiner Zellenausgabe
vorkommt.

**Empfohlene Behebung:** Da jede Zahl im Text ohnehin über `fact()` läuft, gegen
die Werte in `data/notebook_facts.json` und `ALLOWED_NUMBERS` prüfen statt gegen
einen Teilstring der Ausgaben. Zusätzlich sollte „registriert, aber nicht im Text
verwendet" ein Fehler sein statt eines Hinweises, denn genau das zeigt an, dass
ein Platzhalter von Hand überschrieben wurde.

### 5.3 Kleinere Punkte

- `README.md:251` sagt, die Diffusions-Strategien unterschieden sich „um weniger
  als 2%". Gemessen sind maximal 2.1% bei p = 0.05. Das Notebook schreibt
  korrekt „nie 2.1%".
- `submission/SAN-Projekt_20min_Netzwerkanalyse.zip` (169 MB) stammt vom
  3.9.2026, das Notebook vom 4.9.2026. Das Paket ist veraltet.
- Gephi-Exporte aus den `.gexf`-Dateien fehlen (Tool-Kompetenz LE2).

---

## 6. Review-Historie

Vier Runden, jeweils mit Verifikation gegen den ausgeführten Code:

| Runde | Wesentliche Befunde | Zustand |
|---|---|---|
| 1 | Datenleck in der Link-Prediction, fehlerhafte Leave-One-Out-JSD, `fillna(0)`, nicht reproduzierbare `article_id` | behoben |
| 2 | Fehlende Interpretationen, nicht implementierte Sensitivitätszusage, falsch etikettierte Burt-Kennzahl, fehlendes C_B | behoben |
| 3 | Falsche Gewichtssemantik bei Betweenness, Agenturlecks (`Spot`, `Agvs`), fehlendes `python-louvain`, veraltete Zahlen im Text | behoben |
| 4 | Zwei Interpretationszellen mit Zahlen des vorherigen Laufs, widersprüchliche README-Zeile, „Siegerstrategie" ohne Streuungsmass | behoben |

Aus Runde 4 ist als strukturelle Lehre der `fact()`-Mechanismus entstanden: alle
78 Kennzahlen im Fliesstext werden zur Laufzeit eingesetzt statt von Hand
geschrieben. Die verbleibende Lücke steht unter 5.2.

---

## 7. Nächste Schritte in Reihenfolge

1. Arbeitsstand committen
2. KI-Deklaration mit Prompts erstellen (`docs/KI-Deklaration.md`)
3. Qualitätsgate schliessen und README-Zahl korrigieren (5.2, 5.3)
4. Gephi-Bilder erzeugen
5. Präsentation aufzeichnen und nach `praesentation/` legen
6. Paket neu bauen und Integrität prüfen
7. Termin, Gruppennummer und Abgabeweg mit dem Dozenten klären (siehe `TODO.md`)

---

## 8. Reproduktion

Jeweils vom Repository-Wurzelverzeichnis aus:

```bash
python src/clean_dataset.py                     # Rohdaten -> Parquet
python scripts/build_analysis_notebook.py       # erzeugt src/02_analyse.ipynb
python scripts/run_notebook.py                  # führt das Notebook headless aus
python scripts/validate_notebook.py             # Qualitätsgate
python src/network_models.py                    # 17 Unit-Tests
python scripts/build_manifest.py --check        # Datenintegrität
python scripts/package_submission.py --dry-run  # Abgabepaket anzeigen
python scripts/package_submission.py            # Abgabepaket bauen
```
