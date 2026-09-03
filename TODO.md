# TODO: SAN-Projekt 20 Minuten

Abgabe: **Sonntag, 3.1.2027, 23:59:59** (gemaess `docs/SAN-portrait.md`)
Studiengang: Bsc Data Science, Abgabe als Download-Link auf ein komplettes Zip

---

## BLOCKIEREND: KI-Deklaration mit Prompts

**Status: offen. Muss vor der Abgabe erledigt werden.**

Die Projektbeschreibung ist hier eindeutig:

> Jegliche Form von Betrug (nicht deklarierte Kopien aus dem Internet, verwenden
> von KI **ohne Deklaration & Angabe des Prompts**, usw.) fuehrt automatisch zur
> **Note 1 fuer die komplette Gruppe**.

Die aktuelle Deklaration in `src/02_analyse.ipynb`, Abschnitt 5.4, nennt zwar die
verwendeten Werkzeuge, enthaelt aber **keine Prompts**. Das reicht nicht.

Zu erledigen:

- [ ] Prompts aus den Antigravity-Sessions exportieren
- [ ] Prompts aus den Claude-Code-Sessions exportieren
- [ ] Beides als `docs/KI-Deklaration.md` zusammenfuehren, chronologisch, mit
      Angabe welches Werkzeug welchen Teil erzeugt hat
- [ ] Abschnitt 5.4 im Notebook auf dieses Dokument verweisen lassen
- [ ] Mit Elias abgleichen, ob er weitere KI-Nutzung zu deklarieren hat

---

## Praesentation (max. 30 Minuten, aufgezeichnet)

**Status: offen. Wird nicht von Claude erstellt.**

Die Bewertung stuetzt sich primaer hierauf: „Ausschlaggebend sind die
Informationen aus der Praesentation und der Schlussbesprechung.“

Vorgegebener Ablauf aus der Projektbeschreibung:

- [ ] 1. Datenbeschaffung (inkl. Pruefung der Quellen-Eignung)
- [ ] 2. Explorative Datenanalyse (Erkenntnisse und abgeleitete Massnahmen)
- [ ] 3. Modellierung (One-/Two-Mode, Transformation, Knoten- und Kantenattribute)
- [ ] 4. Soziale Netzwerkanalyse (Kennzahlen, Filterkriterien, Interpretation)
- [ ] 5. Ausblick
- [ ] 6. Lessons Learned
- [ ] Jeweils erwaehnen, in welcher Datei die Implementation zu finden ist
- [ ] Aufzeichnung nach `Praesentation/` legen und neu paketieren

---

## Gephi-Visualisierungen

**Status: offen. Wird nicht von Claude erstellt.**

Python-Renderings liegen in `out_plots/`. Zusaetzlich belegen eigene
Gephi-Bilder die Tool-Kompetenz aus LE2.

- [ ] `graphen/author_collaboration_2020_2024.gexf` in Gephi layouten und als
      PNG nach `out_plots/gephi_*.png` exportieren
- [ ] Mindestens ein Keyword-Netzwerk (2020 oder 2024) ebenso

---

## Rueckfragen an den Dozenten

- [ ] **Abgabetermin bestaetigen.** `docs/SAN-portrait.md` nennt den 3.1.2027,
      `docs/SAN-Projektbeschreibung.pdf` den 31.5.2026. Das PDF stammt
      vermutlich aus einem frueheren Semester.
- [ ] Gruppennummer eintragen (Bsc Data Science: ab Nummer 21)
- [ ] MS-Teams-Chat umbenennen zu „SAN-Projekt - Gruppe xx“
- [ ] Bestaetigen, dass der Download-Link ueber Teams geschickt werden soll
      (das Bewertungsraster kennt einen Malus von -0.2 fuer „Abgabe nicht per
      MS-Teams“)

---

## Bewusst nicht abgedeckt

LE9 (Diffusion, Skript Kap. 13) und LE10 (Graphlets, Skript Kap. 14) werden in
diesem Projekt nicht behandelt. Das ist eine bewusste Entscheidung und im
Ausblick des Notebooks als naechster Schritt benannt.
