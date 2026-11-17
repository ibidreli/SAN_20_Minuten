# KI-Prompts (Elias)

Automatisch erzeugt mit `python scripts/ki_prompts.py` aus den Claude-Code-Sitzungen. Werkzeug: Claude Code (Anthropic). Zeiten in UTC. Zusammenfassung und Einordnung: [KI-Deklaration.md](KI-Deklaration.md).

### 2026-11-12 17:36 · Sitzung e1b6ccaf

```text
wie start @data_extraction/ wie geht das ganze welche keywords bekommme ich jetzt
```

### 2026-11-12 17:42 · Sitzung e1b6ccaf

```text
nein bitte untersuche die aufgabenstellung in docs und mache mir eine roadmap was die nächsten Schritte sind und erstelle mir in docs ROADMAP.md
```

### 2026-11-12 17:46 · Sitzung 3081844c

```text
okay starte hier bitte einmal eine test extraktion
```

### 2026-11-12 17:48 · Sitzung 3081844c

```text
wo wird dsa ganze jetzt abgespeichert wo kann ich es ansehen
```

### 2026-11-12 17:57 · Sitzung 3081844c

```text
Als input ziel ist ein nachbau der ähndlich wie bei https://www.dkriesel.com/spiegelmining
```

### 2026-11-12 17:59 · Sitzung 3081844c

```text
okay füge in userem extraktor die variabel textlänge hinzu 
```

### 2026-11-12 18:02 · Sitzung 3081844c

```text
ja gerne ich möchte die autoren auch gerne extrahieren
```

### 2026-11-12 18:06 · Sitzung 3081844c

```text
und die kywords extraction wie funktioniert die und läuft sie und ist sie gut
```

### 2026-11-12 18:12 · Sitzung 3081844c

```text
wie wir es genau machen ist mir egal ich möchte einfach die best möglichsten keywords habe die analysen zulassen und die möglichst ähdlich "grundsätzlich sind" welche methode findest du am besten ich habe dir noch die päsi zu spiegel mining hoch geladen dort sieht man am besten was das ziel ist von uns
[Anhang: Bild/PDF]
```

### 2026-11-12 18:17 · Sitzung 3081844c

```text
oke setzte alles um Ich möchte die best möglichste qualität damit die analyse später einfacher ist verstanden?!
```

### 2026-11-12 18:39 · Sitzung 3081844c

```text
erkläre mir die candidates spalte
```

### 2026-11-12 18:41 · Sitzung 3081844c

```text
aber kann mann das nicht direkt clean machen
```

### 2026-11-12 18:42 · Sitzung 3081844c

```text
ja gerne baue einfach als beispiel das ich sehe das das resultat genug gut ist Soll ich diesen Keyword-Schritt bauen und an den 100 Testartikeln zeigen, was dabei herauskommt?
```

### 2026-11-12 18:45 · Sitzung 3081844c

```text
ist der crawl fertig
```

### 2026-11-12 18:46 · Sitzung 3081844c

```text
wieviel jetzt
```

### 2026-11-12 18:47 · Sitzung 3081844c

```text
okay aber sonst denkst du das data extraction soweit in ordnung ist
```

### 2026-11-12 18:57 · Sitzung 3081844c

```text
afp/dob chi/sep ann/dp/meg/jor/jep/aeg das sind unterschiedliche kürzel obwohl sie so angeschrieben sind untersuche das bitte
```

### 2026-11-12 19:05 · Sitzung 3081844c

```text
wiso habe die ander autoren keine id?
[Anhang: Bild/PDF]
```

### 2026-11-12 19:07 · Sitzung 3081844c

```text
wsa ist der unterschied zwischen Namen und kürzel
```

### 2026-11-12 19:09 · Sitzung 3081844c

```text
untersuche die datenqualität aller tabbellen und gib mir erkentnisse untersuche wircklick tief
```

### 2026-11-12 19:21 · Sitzung 3081844c

```text
und wieviel ist durch
```

### 2026-11-12 19:30 · Sitzung 3081844c

```text
welche csv in data kann mann löschen
```

### 2026-11-12 19:32 · Sitzung 3081844c

```text
gerne ja
```

### 2026-11-12 19:33 · Sitzung 3081844c

```text
449'190 Artikel bis 25.09.2025) was  ist dann jjetz der fall
```

### 2026-11-12 19:34 · Sitzung 3081844c

```text
wie lange würde es gehen bis heute die artikel zu hollen
```

### 2026-11-12 19:35 · Sitzung 3081844c

```text
führe ab den letzten stand get data durch
```

### 2026-11-12 19:39 · Sitzung 3081844c

```text
okay denkst du das andere ist ausführ fertig also die extraction pro artile und denkst du nicht das es zu gross wird die datenbank?
[Anhang: Bild/PDF]
```

### 2026-11-12 19:41 · Sitzung 3081844c

```text
<pasted_content id="0691">
views und updated mitspeichern: Aufrufzahlen und Zeitpunkt der letzten Änderung stehen in der Seite und kosten nichts.
Agenturliste ergänzen: „spot on news“, „SpotOn“ und „Cover Media“ würden sonst als Personen gezählt.
.gitignore ergänzen um *.sqlite, *.sqlite-wal und *.sqlite-shm.
README nachführen und alles committen, damit der Stand, mit dem ihr crawlt, festgehalten und für die Abgabe nachvollziehbar ist.
</pasted_content id="0691">

setzte das um führe den test nocheinmal mit beispielen nach ende 2019 um und analysiere die qualität
```

### 2026-11-12 19:45 · Sitzung 3081844c

```text
wie ist der stand
```

### 2026-11-12 20:07 · Sitzung 3081844c

```text
wie steht der crawl
```

### 2026-11-12 20:08 · Sitzung 3081844c

```text
nocheinmal
```

### 2026-11-12 20:15 · Sitzung 3081844c

```text
okay also denkst du auf jetzigen stand ist es gut brauchbar?
```

### 2026-11-12 20:18 · Sitzung 3081844c

```text
also dann wie starte ich die extraktion für nach ende 2019
```

### 2026-11-12 20:21 · Sitzung 3081844c

```text
würde es etwas nützen mehrfach mit threading zu starten
```

### 2026-11-12 20:33 · Sitzung 3081844c

```text
okay bitte alles umsetzten
```

### 2026-11-12 20:33 · Sitzung 3081844c

```text
okay dann können wir ja jetz schon etwas weiterarbeiten wenn das noch läuft was wären den die nächsten schritte wir können ja mit dem beispiel unter C:\Users\elias\AppData\Local\Temp\claude\61fac5619ea7eec8\3081844c-0c2e-46d4-b30a-bed3e13a4bca\scratchpad 

was wären jetzt die nächsten schritte?
```
