"""Transaktionen und Wiederaufnahme der Kandidatenschicht."""

import sqlite3
from collections.abc import Iterable
from datetime import datetime, timezone
from pathlib import Path

from data_extraction.candidates import Candidate
from data_extraction.page_parser import Page

SEED_BATCH_SIZE = 1000
SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    url TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'done', 'failed', 'skipped')),
    attempts INTEGER NOT NULL DEFAULT 0,
    http_code INTEGER,
    fetched_at TEXT,
    datum TEXT,
    titel TEXT,
    lead TEXT,
    ressort TEXT,
    ressort_pfad TEXT,
    likes INTEGER,
    shares INTEGER,
    kommentare INTEGER,
    quelle_kuerzel TEXT,
    wortanzahl INTEGER,
    views INTEGER,
    aktualisiert TEXT,
    format TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
    url TEXT NOT NULL REFERENCES articles(url),
    phrase TEXT NOT NULL,
    label TEXT NOT NULL CHECK (label IN ('PER', 'ORG', 'LOC', 'MISC', 'NOUN_CHUNK')),
    count INTEGER NOT NULL CHECK (count > 0),
    in_titel INTEGER NOT NULL CHECK (in_titel IN (0, 1)),
    in_lead INTEGER NOT NULL CHECK (in_lead IN (0, 1)),
    lemma TEXT,
    kopf TEXT,
    PRIMARY KEY (url, phrase, label)
);
CREATE TABLE IF NOT EXISTS article_authors (
    url TEXT NOT NULL REFERENCES articles(url),
    position INTEGER NOT NULL CHECK (position >= 1),
    name TEXT NOT NULL,
    kuerzel TEXT,
    autor_id INTEGER,
    art TEXT,
    PRIMARY KEY (url, position)
);
CREATE TABLE IF NOT EXISTS article_kuerzel (
    url TEXT NOT NULL REFERENCES articles(url),
    position INTEGER NOT NULL CHECK (position >= 1),
    kuerzel TEXT NOT NULL,
    art TEXT NOT NULL CHECK (art IN ('redaktion', 'agentur', '20min', 'name')),
    PRIMARY KEY (url, position)
);
CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
CREATE INDEX IF NOT EXISTS idx_candidates_phrase ON candidates(phrase);
"""
# Spalten, die nach dem ersten Schema dazugekommen sind (Tabelle, Spalte, Typ).
ADDED_COLUMNS = (
    ("articles", "wortanzahl", "INTEGER"),
    ("articles", "ressort_pfad", "TEXT"),
    ("articles", "quelle_kuerzel", "TEXT"),
    ("articles", "views", "INTEGER"),
    ("articles", "aktualisiert", "TEXT"),
    ("articles", "format", "TEXT"),
    ("article_authors", "art", "TEXT"),
    ("candidates", "lemma", "TEXT"),
    ("candidates", "kopf", "TEXT"),
)


class Database:
    def __init__(self, path: str | Path):
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript(SCHEMA)
        self._add_missing_columns()

    def _add_missing_columns(self) -> None:
        # Ältere Datenbanken ohne die später ergänzten Spalten nachrüsten.
        for table, column, sql_type in ADDED_COLUMNS:
            existing = {
                row["name"]
                for row in self.connection.execute(f"PRAGMA table_info({table})")
            }
            if column not in existing:
                self.connection.execute(
                    f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"
                )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_candidates_lemma ON candidates(lemma)"
        )
        self.connection.commit()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.connection.close()

    def transaction(self):
        return self.connection

    def seed(self, records: Iterable[tuple[str, str | None]]) -> None:
        batch = []
        for row in records:
            batch.append(row)
            if len(batch) == SEED_BATCH_SIZE:
                self._seed_batch(batch)
                batch.clear()
        if batch:
            self._seed_batch(batch)

    def _seed_batch(self, rows):
        with self.transaction():
            self.connection.executemany(
                "INSERT INTO articles(url, datum) VALUES (?, ?) ON CONFLICT(url) DO NOTHING",
                rows,
            )

    def pending_urls(self, limit: int) -> list[sqlite3.Row]:
        if limit <= 0:
            raise ValueError("Batchgrösse muss positiv sein")
        return self.connection.execute(
            "SELECT url, datum FROM articles WHERE status='pending' ORDER BY rowid LIMIT ?",
            (limit,),
        ).fetchall()

    def mark_done(self, url: str, page: Page, candidates: list[Candidate]) -> None:
        self.connection.execute("DELETE FROM candidates WHERE url=?", (url,))
        self.connection.executemany(
            """INSERT INTO candidates
            (url, phrase, label, count, in_titel, in_lead, lemma, kopf)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    url,
                    c.phrase,
                    c.label,
                    c.count,
                    c.in_titel,
                    c.in_lead,
                    c.lemma,
                    c.kopf,
                )
                for c in candidates
            ],
        )
        self.connection.execute("DELETE FROM article_kuerzel WHERE url=?", (url,))
        self.connection.executemany(
            """INSERT INTO article_kuerzel (url, position, kuerzel, art)
            VALUES (?, ?, ?, ?)""",
            [
                (url, position, s.kuerzel, s.art)
                for position, s in enumerate(page.quellen, start=1)
            ],
        )
        self.connection.execute("DELETE FROM article_authors WHERE url=?", (url,))
        self.connection.executemany(
            """INSERT INTO article_authors
            (url, position, name, kuerzel, autor_id, art)
            VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (url, position, a.name, a.kuerzel, a.autor_id, a.art)
                for position, a in enumerate(page.autoren, start=1)
            ],
        )
        self.connection.execute(
            """UPDATE articles SET status='done', attempts=attempts+1, http_code=200,
            fetched_at=?, datum=?, aktualisiert=?, titel=?, lead=?, ressort=?,
            ressort_pfad=?, likes=?, shares=?, kommentare=?, views=?,
            quelle_kuerzel=?, wortanzahl=?, format=?
            WHERE url=?""",
            (
                self._now(),
                page.datum,
                page.aktualisiert,
                page.titel,
                page.lead,
                page.ressort,
                page.ressort_pfad,
                page.likes,
                page.shares,
                page.kommentare,
                page.views,
                page.quelle_kuerzel,
                page.wortanzahl,
                page.format,
                url,
            ),
        )

    def mark_failed(self, url: str, http_code: int | None) -> None:
        self._mark_status(url, "failed", http_code)

    def mark_skipped(self, url: str, http_code: int) -> None:
        self._mark_status(url, "skipped", http_code)

    def _mark_status(self, url, status, http_code):
        self.connection.execute(
            "UPDATE articles SET status=?, attempts=attempts+1, http_code=?, fetched_at=? WHERE url=?",
            (status, http_code, self._now(), url),
        )

    def reset_failed(self, urls: Iterable[str] | None = None) -> int:
        with self.transaction():
            if urls is None:
                return self.connection.execute(
                    "UPDATE articles SET status='pending' WHERE status='failed'"
                ).rowcount
            changed = 0
            for url in urls:
                changed += self.connection.execute(
                    "UPDATE articles SET status='pending' WHERE status='failed' AND url=?",
                    (url,),
                ).rowcount
            return changed

    def counts(self) -> dict[str, int]:
        return dict(
            self.connection.execute(
                "SELECT status, count(*) FROM articles GROUP BY status"
            )
        )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
