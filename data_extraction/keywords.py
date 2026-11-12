"""Keyword-Schicht: wählt aus den Kandidaten die besten Keywords pro Artikel.

Läuft nach dem Crawl auf der Datenbank und schreibt die Tabelle `keywords`
neu. Der Schritt ist beliebig oft wiederholbar, ohne neu zu crawlen.

Vorgehen pro Artikel:
1. Begriff bilden: Namen (PER/ORG/LOC/MISC) über ihre Grundform,
   Nominalphrasen über ihr Kopfnomen ("die geplanten Parkhäuser" -> Parkhaus).
2. Nachnamen auf den vollen Namen im selben Artikel abbilden
   ("Sawiris" -> "Samih Sawiris").
3. Stoppliste und Zahlen entfernen (Zeitangaben, Allerweltswörter, Boilerplate).
4. Bewerten mit TF-IDF über das ganze Korpus, Bonus für Titel, Lead und Namen.
5. Die besten `top_k` Begriffe behalten; dazu die Ressort-Stufen als Typ RESSORT.

Zwei Durchgänge über die Kandidaten halten den Speicherbedarf klein:
Durchgang 1 zählt Dokumentfrequenzen und Typen, Durchgang 2 bewertet.
"""

import argparse
import math
import re
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TOP_K = 8
DEFAULT_MIN_DF = 2
ENTITY_LABELS = ("PER", "ORG", "LOC", "MISC")
# Gewichte der Bewertung.
TITLE_BONUS = 1.0
LEAD_BONUS = 0.5
ENTITY_BONUS = {"PER": 1.25, "ORG": 1.25, "LOC": 1.25, "MISC": 1.0, "THEMA": 1.0}
# Ab diesem Anteil an Namens-Labels gilt ein Begriff korpusweit als Name.
# Darunter ist es ein gewöhnliches Wort, das spaCy gelegentlich für einen
# Namen hält ("Bund", "Sohn").
ENTITY_SHARE = 0.5
# Ein Themenwort (kein Name) zählt nur, wenn es im Artikel mehrfach oder in
# Titel/Lead vorkommt. Einmal nebenbei erwähnte Wörter ("Freude", "Liste")
# sind selten das Thema.
MIN_THEMA_COUNT = 2
RESSORT_SEPARATOR = " > "

# Wörter, die nie ein Keyword sind: Zeitangaben, Mengen, Währungen,
# Allerweltswörter und Redaktions-Boilerplate. Klein geschrieben.
STOPWORDS = frozenset(
    """
    januar februar märz april mai juni juli august september oktober november dezember
    montag dienstag mittwoch donnerstag freitag samstag sonntag wochenende
    jahr jahrzehnt jahrhundert monat woche tag stunde minute sekunde uhr zeit
    zeitpunkt zeitraum ende anfang beginn mitte moment mal abend morgen nacht
    nachmittag vormittag mittag vorjahr saison
    prozent million milliarde franken euro dollar rappen zahl anzahl teil hälfte
    mehrheit rest summe betrag
    fall grund art weise sache ding frage antwort beispiel ort stelle seite punkt
    bereich thema situation möglichkeit ziel weg lage folge angabe aussage
    information bild foto video text artikel bericht meldung mitteilung anfrage
    sprecher sprecherin leute mensch person mann frau haus leben welt problem
    idee meinung rolle form geschichte grösse nähe hilfe weg schluss blick
    20 minuten 20 minute news push whatsapp leserreporter app newsletter
    news-scout news-scouts werbung umfrage community
    """.split()
) | frozenset({"20 minuten", "20 minute"})
# Zeitangaben wie "Donnerstagmorgen", "Mittwochabend", "Nacht auf Sonntag".
TIME_EXPRESSION = re.compile(
    r"((montag|dienstag|mittwoch|donnerstag|freitag|samstag|sonntag|heute|gestern)"
    r"(morgen|vormittag|mittag|nachmittag|abend|nacht)?"
    r"|(nacht|morgen|abend) (auf|vom|von|am) \w+)"
)


@dataclass
class Term:
    display: str
    labels: Counter = field(default_factory=Counter)
    count: int = 0
    in_titel: bool = False
    in_lead: bool = False

    @property
    def label(self) -> str:
        # Mehrheit der Vorkommen im Artikel; ein einzelner NER-Treffer macht
        # aus "Sohn" noch keine Person.
        return self.labels.most_common(1)[0][0]


def keep(surface: str) -> bool:
    key = surface.lower()
    if len(surface) < 2 or surface[0].isdigit() or key in STOPWORDS:
        return False
    if TIME_EXPRESSION.fullmatch(key):
        return False
    # Mehrwortbegriffe aus Stoppwörtern und Zahlen ("Ende Woche", "Jahr 2013")
    # fallen ebenfalls weg.
    return not all(part in STOPWORDS or part.isdigit() for part in key.split())


def article_terms(rows: list[sqlite3.Row]) -> dict[str, Term]:
    """Fasst die Kandidaten eines Artikels zu Begriffen zusammen."""
    raw: list[tuple[str, str, sqlite3.Row]] = []
    for row in rows:
        surface = row["lemma"] if row["label"] in ENTITY_LABELS else row["kopf"]
        if surface and keep(surface.strip()):
            raw.append((surface.strip(), row["label"], row))
    # Nachname oder Vorname -> voller Name, nur wenn im Artikel eindeutig
    # ("Sawiris" und "Samih" -> "Samih Sawiris").
    full_names: dict[str, set[str]] = defaultdict(set)
    persons = set()
    for surface, label, _ in raw:
        parts = surface.split()
        if label == "PER" and len(parts) >= 2:
            full_names[parts[-1]].add(surface)
            full_names[parts[0]].add(surface)
            persons.add(surface)
    terms: dict[str, Term] = {}
    for surface, label, row in raw:
        if " " not in surface and len(full_names.get(surface, ())) == 1:
            surface, label = next(iter(full_names[surface])), "PER"
        else:
            # Rolle vor dem Namen ("Swiss-Chef André Dosé") -> "André Dosé",
            # wenn die kürzere Form im Artikel als Person vorkommt.
            for person in persons:
                if surface != person and surface.endswith(" " + person):
                    surface, label = person, "PER"
                    break
        key = surface.lower()
        term = terms.setdefault(key, Term(surface))
        # Als Name erkannte Schreibweise bevorzugen ("Basel" statt "basel").
        if label != "NOUN_CHUNK" and not any(
            k != "NOUN_CHUNK" for k in term.labels
        ):
            term.display = surface
        term.labels[label] += row["count"]
        term.count += row["count"]
        term.in_titel |= bool(row["in_titel"])
        term.in_lead |= bool(row["in_lead"])
    return terms


def iter_articles(connection: sqlite3.Connection) -> Iterator[tuple[str, list]]:
    cursor = connection.execute(
        """SELECT c.url, c.phrase, c.label, c.lemma, c.kopf, c.count, c.in_titel,
        c.in_lead FROM candidates c JOIN articles a ON a.url = c.url
        WHERE a.status = 'done' ORDER BY c.url"""
    )
    current, rows = None, []
    for row in cursor:
        if row["url"] != current and rows:
            yield current, rows
            rows = []
        current = row["url"]
        rows.append(row)
    if rows:
        yield current, rows


def corpus_statistics(connection):
    """Durchgang 1: Dokumentfrequenz, Typ und Schreibweise pro Begriff."""
    df: Counter = Counter()
    labels: dict[str, Counter] = defaultdict(Counter)
    displays: dict[str, Counter] = defaultdict(Counter)
    n_docs = 0
    for _, rows in iter_articles(connection):
        n_docs += 1
        for key, term in article_terms(rows).items():
            df[key] += 1
            labels[key][term.label] += 1
            displays[key][term.display] += 1
    types = {}
    for key, counts in labels.items():
        entity = Counter({k: v for k, v in counts.items() if k != "NOUN_CHUNK"})
        total = sum(counts.values())
        if entity and sum(entity.values()) >= ENTITY_SHARE * total:
            types[key] = entity.most_common(1)[0][0]
        else:
            types[key] = "THEMA"
    display = {key: c.most_common(1)[0][0] for key, c in displays.items()}
    return n_docs, df, types, display


def score(term: Term, df: int, n_docs: int, typ: str) -> float:
    tf = 1 + math.log(term.count)
    idf = math.log(n_docs / df)
    position = 1 + TITLE_BONUS * term.in_titel + LEAD_BONUS * term.in_lead
    return tf * idf * position * ENTITY_BONUS[typ]


def build_keywords(
    db_path: Path, top_k: int = DEFAULT_TOP_K, min_df: int = DEFAULT_MIN_DF
) -> dict[str, int]:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    n_docs, df, types, display = corpus_statistics(connection)
    if n_docs == 0:
        raise ValueError("Keine fertig verarbeiteten Artikel in der Datenbank")
    ressorts = dict(
        connection.execute(
            "SELECT url, ressort_pfad FROM articles WHERE status = 'done'"
        ).fetchall()
    )
    connection.execute("DROP TABLE IF EXISTS keywords")
    connection.execute(
        """CREATE TABLE keywords (
        url TEXT NOT NULL REFERENCES articles(url),
        keyword TEXT NOT NULL,
        typ TEXT NOT NULL CHECK (typ IN
            ('RESSORT', 'PER', 'ORG', 'LOC', 'MISC', 'THEMA')),
        rang INTEGER NOT NULL,
        score REAL,
        df INTEGER,
        PRIMARY KEY (url, keyword, typ))"""
    )
    batch = []
    for url, rows in iter_articles(connection):
        path = ressorts.get(url)
        for level, name in enumerate(path.split(RESSORT_SEPARATOR) if path else ()):
            batch.append((url, name, "RESSORT", level, None, None))
        scored = []
        for key, term in article_terms(rows).items():
            if df[key] < min_df:
                continue  # Kommt nur in einem Artikel vor: bildet keine Kante.
            typ = types[key]
            if (
                typ == "THEMA"
                and term.count < MIN_THEMA_COUNT
                and not (term.in_titel or term.in_lead)
            ):
                continue
            scored.append((score(term, df[key], n_docs, typ), key, typ))
        scored.sort(key=lambda item: (-item[0], item[1]))
        for rank, (value, key, typ) in enumerate(scored[:top_k], start=1):
            batch.append((url, display[key], typ, rank, round(value, 3), df[key]))
    with connection:
        connection.executemany(
            "INSERT INTO keywords VALUES (?, ?, ?, ?, ?, ?)", batch
        )
        connection.execute("CREATE INDEX idx_keywords_keyword ON keywords(keyword)")
    counts = dict(
        connection.execute("SELECT typ, count(*) FROM keywords GROUP BY typ")
    )
    connection.close()
    return {"artikel": n_docs, **counts}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Keywords pro Artikel aus der Kandidatenschicht bilden"
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument(
        "--min-df",
        type=int,
        default=DEFAULT_MIN_DF,
        help="Mindestanzahl Artikel, in denen ein Keyword vorkommen muss",
    )
    args = parser.parse_args(argv)
    if not args.db.exists():
        parser.error(f"Datenbank fehlt: {args.db}")
    print(build_keywords(args.db, args.top_k, args.min_df))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
