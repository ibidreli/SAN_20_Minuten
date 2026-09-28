import sqlite3

import pytest

from data_extraction.candidates import Candidate
from data_extraction.db import Database
from data_extraction.page_parser import Page


def test_resume_and_candidate_transaction(tmp_path):
    path = tmp_path / "articles.sqlite"
    with Database(path) as db:
        db.seed([("fixture://a/0", "2025"), ("fixture://b/1", "2024")])
        db.seed([("fixture://a/0", "wrong")])
        page = Page(titel="Titel", lead="Lead", body="NICHT SPEICHERN", datum="2025")
        with db.transaction():
            db.mark_done(
                "fixture://a/0", page, [Candidate("Phrase", "PER", 1, False, False)]
            )
            db.mark_failed("fixture://b/1", 503)
        assert db.pending_urls(10) == []
        assert db.connection.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
        assert db.connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    with Database(path) as db:
        assert db.reset_failed(["fixture://b/1"]) == 1
        assert [row["url"] for row in db.pending_urls(10)] == ["fixture://b/1"]
        assert (
            db.connection.execute(
                "SELECT attempts FROM articles WHERE status='done'"
            ).fetchone()[0]
            == 1
        )
        assert "NICHT SPEICHERN" not in "\n".join(db.connection.iterdump())
        columns = [
            row[1] for row in db.connection.execute("PRAGMA table_info(articles)")
        ]
        assert "body" not in columns


def test_failed_batch_rolls_back(tmp_path):
    with Database(tmp_path / "articles.sqlite") as db:
        db.seed([("fixture://a/0", None)])
        with pytest.raises(sqlite3.IntegrityError), db.transaction():
            db.mark_done(
                "fixture://a/0",
                Page(body="Text"),
                [
                    Candidate("Phrase", "PER", 1, False, False),
                    Candidate("Phrase", "PER", 1, False, False),
                ],
            )
        assert len(db.pending_urls(10)) == 1
        assert (
            db.connection.execute("SELECT count(*) FROM candidates").fetchone()[0] == 0
        )


def test_skipped_is_terminal_and_retry_is_targeted(tmp_path):
    with Database(tmp_path / "articles.sqlite") as db:
        db.seed([(f"fixture://a/{i}", None) for i in range(3)])
        with db.transaction():
            db.mark_failed("fixture://a/0", 503)
            db.mark_failed("fixture://a/1", None)
            db.mark_skipped("fixture://a/2", 410)
        assert db.reset_failed(["fixture://a/0"]) == 1
        assert db.counts() == {"pending": 1, "failed": 1, "skipped": 1}
        assert db.reset_failed() == 1
