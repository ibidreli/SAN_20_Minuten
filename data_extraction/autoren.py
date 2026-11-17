"""Personen-Schicht: führt Autorennamen, Kürzel und IDs zu Personen zusammen.

Läuft nach dem Crawl auf der Datenbank und schreibt die Tabellen
`personen` und `article_persons` neu. Wie `keywords.py` beliebig oft
wiederholbar, ohne neu zu crawlen.

Das Problem: Dieselbe Person erscheint je nach CMS-Epoche als
- voller Name mit ID ("Jean-Claude Gerber", Kürzel "jcg", ID 26970202),
- voller Name ohne ID ("Viviane Widmer"),
- abgekürzter Name ("B. Zanni"),
- nur Kürzel in der Byline ("jcg") oder in der Quellenzeile ("dpa/jcg").

Vorgehen:
1. Personen mit ID: kanonischer Name = häufigster Name pro ID.
   Gleicher Name ohne ID -> dieselbe Person (Methode "name").
2. Kürzel-Wörterbuch aus allen Zeilen, in denen Name und echtes Kürzel
   gemeinsam vorkommen. Ein Kürzel gilt als eindeutig, wenn eine Person
   mindestens `KUERZEL_SHARE` der Belege hat. Sonst entscheidet die Person,
   deren Belege zeitlich am nächsten am Artikel liegen (höchstens
   `MAX_GAP_DAYS` entfernt).
3. Abgekürzte Namen ("B. Zanni") -> voller Name mit gleichem Nachnamen und
   gleicher Initiale, wenn genau einer passt (Methode "initiale").
4. Nicht auflösbare Kürzel bleiben als eigene Person "kürzel:xyz" erhalten:
   hinter einem Kürzel steht fast immer genau eine Person, nur ihr Name
   ist unbekannt.

Agenturen, "20 Minuten" und Ortsangaben ("aus Melbourne") sind keine
Personen und landen nicht in `article_persons`.
"""

import argparse
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

KUERZEL = re.compile(r"[a-zäöü]{1,8}")
ABGEKUERZT = re.compile(r"([A-ZÄÖÜ])\.\s*(\S.*)")
# Ein Kürzel ist eindeutig, wenn eine Person diesen Anteil der Belege hat.
KUERZEL_SHARE = 0.8
# Zeitliche Auflösung mehrdeutiger Kürzel: grösster erlaubter Abstand.
MAX_GAP_DAYS = 365
UNRESOLVED_PREFIX = "kürzel:"


@dataclass
class Belege:
    """Wann eine Person unter einem Kürzel belegt ist."""

    count: int = 0
    dates: list = field(default_factory=list)


def parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value[:19])
    except ValueError:
        return None


ZUSATZ = re.compile(r"\s*\([^)]*\)|\s+(aus|vor Ort)\b.*$")


def clean_name(name: str) -> str:
    # "Thomas Sennhauser (vor Ort)", "Sven Forster aus Adelboden" -> Name.
    return ZUSATZ.sub("", name).strip()


def is_kuerzel(value: str | None) -> bool:
    return bool(value) and KUERZEL.fullmatch(value) is not None


def is_full_name(name: str) -> bool:
    # Mindestens zwei Teile, nicht abgekürzt ("B. Zanni"): sonst kein
    # verlässlicher Personenname.
    return len(name.split()) >= 2 and not ABGEKUERZT.fullmatch(name)


class PersonRegistry:
    def __init__(self, rows: list[sqlite3.Row]):
        names_by_id: dict[int, Counter] = defaultdict(Counter)
        name_counts: Counter = Counter()
        for row in rows:
            if row["art"] != "person":
                continue
            name = clean_name(row["name"])
            name_counts[name] += 1
            if row["autor_id"] is not None:
                names_by_id[row["autor_id"]][name] += 1
        # Kanonischer Name pro ID: der häufigste.
        self.id_name = {
            autor_id: names.most_common(1)[0][0]
            for autor_id, names in names_by_id.items()
        }
        # Name -> ID, nur wenn der Name genau einer ID gehört.
        owners: dict[str, set] = defaultdict(set)
        for autor_id, names in names_by_id.items():
            for name in names:
                owners[name].add(autor_id)
        self.name_id = {n: next(iter(ids)) for n, ids in owners.items() if len(ids) == 1}
        self.full_names = {
            self.canonical(name) for name in name_counts if is_full_name(name)
        }
        # Initiale + Nachname -> volle Namen ("B. Zanni" -> "Bernhard Zanni").
        self.by_initial: dict[tuple[str, str], set] = defaultdict(set)
        for name in self.full_names:
            parts = name.split()
            self.by_initial[(parts[0][0], parts[-1])].add(name)
        self.kuerzel_map = self._kuerzel_map(rows)

    def canonical(self, name: str, autor_id: int | None = None) -> str:
        if autor_id is not None and autor_id in self.id_name:
            return self.id_name[autor_id]
        if name in self.name_id:
            return self.id_name[self.name_id[name]]
        return name

    def _kuerzel_map(self, rows) -> dict[str, dict[str, Belege]]:
        evidence: dict[str, dict[str, Belege]] = defaultdict(
            lambda: defaultdict(Belege)
        )
        for row in rows:
            kuerzel = (row["kuerzel"] or "").strip()
            name = clean_name(row["name"])
            if row["art"] != "person" or not is_kuerzel(kuerzel) or kuerzel == name:
                continue
            if not is_full_name(name):
                continue
            belege = evidence[kuerzel][self.canonical(name, row["autor_id"])]
            belege.count += 1
            date = parse_date(row["datum"])
            if date:
                belege.dates.append(date)
        return evidence

    def resolve_kuerzel(self, kuerzel: str, datum: str | None) -> tuple[str, str]:
        persons = self.kuerzel_map.get(kuerzel)
        if not persons:
            return UNRESOLVED_PREFIX + kuerzel, "ungeloest"
        total = sum(b.count for b in persons.values())
        best, belege = max(persons.items(), key=lambda item: item[1].count)
        if belege.count >= KUERZEL_SHARE * total:
            return best, "kuerzel"
        # Mehrdeutig: die zeitlich nächste Person nehmen.
        date = parse_date(datum)
        if date:
            gaps = {
                person: min(abs((d - date).days) for d in b.dates)
                for person, b in persons.items()
                if b.dates
            }
            if gaps:
                nearest = min(gaps, key=gaps.get)
                ties = [p for p, gap in gaps.items() if gap == gaps[nearest]]
                if gaps[nearest] <= MAX_GAP_DAYS and len(ties) == 1:
                    return nearest, "kuerzel_zeit"
        return UNRESOLVED_PREFIX + kuerzel, "mehrdeutig"

    def resolve_name(self, name: str, autor_id: int | None) -> tuple[str, str]:
        if autor_id is not None:
            return self.canonical(name, autor_id), "id"
        if name in self.name_id:
            return self.canonical(name), "name"
        match = ABGEKUERZT.fullmatch(name)
        if match:
            candidates = self.by_initial.get((match.group(1), match.group(2)), set())
            if len(candidates) == 1:
                return next(iter(candidates)), "initiale"
        return name, "name"


def resolve_row(
    registry: PersonRegistry, name: str, kuerzel: str | None, autor_id, art, datum
) -> tuple[str, str] | None:
    """Gibt (Person, Methode) zurück oder None, wenn es keine Person ist."""
    name = clean_name(name)
    if art == "person":
        if autor_id is None and not is_full_name(name) and not ABGEKUERZT.fullmatch(name):
            # Einzelwort ohne ID ("Ella", "Lars"): Vorname ohne Nachname
            # ist zu unsicher für einen Personenknoten.
            return None
        return registry.resolve_name(name, autor_id)
    if art in ("kuerzel", "redaktion"):
        key = (kuerzel or name).strip().lower()
        if not is_kuerzel(key):
            return None
        return registry.resolve_kuerzel(key, datum)
    return None


def build_persons(db_path: Path) -> dict[str, int]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    authors = connection.execute(
        """SELECT x.url, x.position, x.name, x.kuerzel, x.autor_id, x.art, a.datum
        FROM article_authors x JOIN articles a ON a.url = x.url
        WHERE a.status = 'done'"""
    ).fetchall()
    sources = connection.execute(
        """SELECT k.url, k.position, k.kuerzel, k.art, a.datum
        FROM article_kuerzel k JOIN articles a ON a.url = k.url
        WHERE a.status = 'done' AND k.art = 'redaktion'"""
    ).fetchall()
    registry = PersonRegistry(authors)

    rows, seen = [], set()
    for row in authors:
        resolved = resolve_row(
            registry, row["name"], row["kuerzel"], row["autor_id"], row["art"], row["datum"]
        )
        if resolved and (row["url"], "autor", resolved[0]) not in seen:
            seen.add((row["url"], "autor", resolved[0]))
            rows.append((row["url"], "autor", row["position"], *resolved, row["art"]))
    for row in sources:
        resolved = resolve_row(
            registry, row["kuerzel"], row["kuerzel"], None, "redaktion", row["datum"]
        )
        # Wer schon als Autor genannt ist, zählt nicht zusätzlich als Quelle.
        if resolved and (row["url"], "autor", resolved[0]) not in seen and (
            row["url"], "quelle", resolved[0]
        ) not in seen:
            seen.add((row["url"], "quelle", resolved[0]))
            rows.append((row["url"], "quelle", row["position"], *resolved, "redaktion"))

    kuerzel_of: dict[str, set] = defaultdict(set)
    for kuerzel, persons in registry.kuerzel_map.items():
        for person in persons:
            kuerzel_of[person].add(kuerzel)
    id_of = {name: autor_id for autor_id, name in registry.id_name.items()}

    connection.executescript(
        """DROP TABLE IF EXISTS article_persons;
        DROP TABLE IF EXISTS personen;
        CREATE TABLE article_persons (
            url TEXT NOT NULL REFERENCES articles(url),
            rolle TEXT NOT NULL CHECK (rolle IN ('autor', 'quelle')),
            position INTEGER NOT NULL,
            person TEXT NOT NULL,
            methode TEXT NOT NULL CHECK (methode IN
                ('id', 'name', 'initiale', 'kuerzel', 'kuerzel_zeit',
                 'mehrdeutig', 'ungeloest')),
            art_original TEXT,
            PRIMARY KEY (url, rolle, person));
        CREATE TABLE personen (
            person TEXT PRIMARY KEY,
            autor_id INTEGER,
            kuerzel TEXT,
            aufgeloest INTEGER NOT NULL,
            n_autor INTEGER NOT NULL,
            n_quelle INTEGER NOT NULL,
            erstes TEXT,
            letztes TEXT);"""
    )
    with connection:
        connection.executemany(
            "INSERT INTO article_persons VALUES (?, ?, ?, ?, ?, ?)", rows
        )
        connection.execute(
            """INSERT INTO personen
            SELECT p.person, NULL, NULL,
                p.person NOT LIKE 'kürzel:%',
                sum(p.rolle = 'autor'), sum(p.rolle = 'quelle'),
                min(a.datum), max(a.datum)
            FROM article_persons p JOIN articles a ON a.url = p.url
            GROUP BY p.person"""
        )
        connection.executemany(
            "UPDATE personen SET autor_id = ?, kuerzel = ? WHERE person = ?",
            [
                (id_of.get(person), "/".join(sorted(kuerzel_of.get(person, ()))) or None, person)
                for (person,) in connection.execute("SELECT person FROM personen")
            ],
        )
        connection.execute(
            "CREATE INDEX idx_article_persons_person ON article_persons(person)"
        )
    stats = dict(
        connection.execute(
            "SELECT methode, count(*) FROM article_persons GROUP BY methode"
        )
    )
    stats["personen"] = connection.execute("SELECT count(*) FROM personen").fetchone()[0]
    connection.close()
    return stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Autorennamen, Kürzel und IDs zu Personen zusammenführen"
    )
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"Datenbank fehlt: {args.db}")
    print(build_persons(args.db))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
