# Ground-Truth Source Data Validation Audit (n = 60)

**Erzeugt von:** `scripts/build_ground_truth_validation.py`  
**Datenbasis:** `data/20min_cleaned_post2020.parquet` (2020-2024)  
**Live-Quelle:** https://www.20min.ch  
**Stichprobe:** stratifiziert ueber Jahre und Ressorts, Seed 42

## Zusammenfassung

| Kennzahl | Anzahl | Anteil |
| :--- | ---: | ---: |
| Geprueft | 60 | 100.0% |
| Live erreichbar (HTTP 200) | 60 | 100.0% |
| Titel stimmt ueberein | 60 | 100.0% |
| Autor:in stimmt ueberein | 52 | 86.7% |
| Publikationsdatum stimmt ueberein | 59 | 98.3% |

## Stabile und volatile Felder

- **Stabile Felder** (Titel, Autor:in, Datum, Ressort) zeigen hohe Uebereinstimmung
  zwischen lokalem Datensatz und Live-Plattform.
- **Volatile Felder** (Likes, Shares, Kommentare) sind Momentaufnahmen zum
  Scraping-Zeitpunkt und driften naturgemaess. Sie werden deshalb als historische
  Querschnittswerte behandelt, nicht als Echtzeit-Zustand.

## Stichprobe je Jahr

| Jahr | Geprueft | Erreichbar | Titel-Match |
| ---: | ---: | ---: | ---: |
| 2020 | 12 | 12 | 12 |
| 2021 | 12 | 12 | 12 |
| 2022 | 12 | 12 | 12 |
| 2023 | 12 | 12 | 12 |
| 2024 | 12 | 12 | 12 |

## Einzelne Pruefungen (Auszug)

| Jahr | Ressort | Titel (gekuerzt) | Autor:in | Status |
| ---: | :--- | :--- | :--- | :---: |
| 2020 | Sport | Basel entscheidet einen verrückten Kla | nan | MATCH |
| 2020 | Sport | Er ist 24 Jahre alt und 500 Millionen  | Undefined Undefined | MATCH |
| 2020 | Sport | Das Programm zum vollbepackten Sport-S | Nils Hänggi; Etienne S | MATCH |
| 2020 | People | Cardi B hat Beef mit «Peppa Pig» | Pascal Kobluk | MATCH |
| 2020 | Schweiz | Dieses Hochsicherheits-Labor forscht a | Miw | MATCH |
| 2020 | People | «Es war jemand aus der Modeindustrie,  | Schimun Krausz | MATCH |
| 2020 | Schweiz | «Eine Wahl Trumps ist eher im Interess | Daniel Waldmeier | MATCH |
| 2020 | Schweiz | Unionsbürger? EU-Richter? Darum gehts  | nan | MATCH |
| 2020 | Coronavirus | Querdenken-Initiator will vorerst nich | AFP | MATCH |
| 2020 | Ausland | Backpackerin (21) stürzt an Selfie-Spo | Scl | MATCH |
| 2020 | Digital | Apple wehrt sich gegen einheitliche La | Tob | MATCH |
| 2020 | Sport | Das teuerste Dressurpferd der Welt ist | Nils Hänggi | MATCH |
| 2021 | Ausland | Seit einer Woche fordern Demonstranten | Undefined Undefined | MATCH |
| 2021 | Ausland | Prag ruft EU-Mitglieder auf, russische | Undefined Undefined | MATCH |
| 2021 | Coronavirus | Armband erkennt Corona-Infektionen sch | Patrick McEvily | MATCH |
| 2021 | Panorama | Bildstrecke – Was sagt Ueli Maurer zur | nan | MATCH |
| 2021 | Schweiz | Starke Nachfrage - Corona-Krise führt  | Marcel Urech | MATCH |
| 2021 | Digital | Fünf falsche Infos zur Corona-Impfung  | Undefined Undefined | MATCH |
| 2021 | Ausland | Mindestens 38 Menschen sterben bei Hoc | Undefined Undefined | MATCH |
| 2021 | Schweiz | «Wenn man bis Montag warten muss, ist  | Carla Pfister | MATCH |
