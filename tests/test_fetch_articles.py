from threading import Event
from unittest.mock import Mock

import pytest

from data_extraction.db import Database
from data_extraction.fetch_articles import csv_records, main, run, stop_on_signal
from data_extraction.sources import FixtureSource


def test_interrupted_batch_commits_and_resumes(tmp_path, fixture_dir, nlp):
    source = FixtureSource(fixture_dir)
    stop = Event()
    fetch = source.fetch

    def interrupted_fetch(url):
        stop.set()
        return fetch(url)

    source.fetch = interrupted_fetch
    with Database(tmp_path / "resume.sqlite") as db:
        db.seed(source.records(26))
        run(db, source, nlp, batch_size=5, stop=stop)
        assert db.counts() == {"done": 5, "pending": 21}
        source.fetch = fetch
        run(db, source, nlp, batch_size=5)
        assert db.counts() == {"done": 24, "skipped": 2}
        assert (
            db.connection.execute("SELECT max(attempts) FROM articles").fetchone()[0]
            == 1
        )


def test_statuses_and_parser_failure_are_persisted(tmp_path, nlp):
    source = Mock()
    source.fetch.side_effect = [
        (503, None),
        (None, None),
        (200, "<html></html>"),
        (410, None),
    ]
    with Database(tmp_path / "errors.sqlite") as db:
        db.seed([(f"fixture://error/{i}", None) for i in range(4)])
        assert run(db, source, nlp, workers=1) == {"failed": 3, "skipped": 1}
        assert (
            db.connection.execute("SELECT min(attempts) FROM articles").fetchone()[0]
            == 1
        )


def test_unexpected_failure_rolls_back_entire_batch(tmp_path, fixture_dir, nlp):
    source = FixtureSource(fixture_dir)
    records = list(source.records(3))
    fetch = source.fetch

    def broken_fetch(url):
        if url == records[1][0]:
            raise RuntimeError("Testabbruch")
        return fetch(url)

    source.fetch = broken_fetch
    with Database(tmp_path / "rollback.sqlite") as db:
        db.seed(records)
        with pytest.raises(RuntimeError, match="Testabbruch"):
            run(db, source, nlp, workers=1)
        assert db.counts() == {"pending": 3}
        assert (
            db.connection.execute("SELECT count(*) FROM candidates").fetchone()[0] == 0
        )


def test_dry_run_does_not_load_model_or_create_db(tmp_path, monkeypatch):
    load = Mock(side_effect=AssertionError("Modellladen im Dry-run"))
    monkeypatch.setattr("data_extraction.fetch_articles.load_model", load)
    path = tmp_path / "dry.sqlite"
    assert main(["--source", "fixtures", "--db", str(path), "--dry-run"]) == 0
    assert not path.exists()
    load.assert_not_called()


@pytest.mark.parametrize(
    "arguments",
    [
        ["--batch-size", "0"],
        ["--workers", "-1"],
        ["--retry-failed", "--retry-url", "fixture://x/0"],
        ["--input", "ignored.csv"],
    ],
)
def test_invalid_cli_arguments_fail_before_work(tmp_path, arguments):
    with pytest.raises(SystemExit) as error:
        main(
            [
                "--source",
                "fixtures",
                "--db",
                str(tmp_path / "unused.sqlite"),
                *arguments,
            ]
        )
    assert error.value.code == 2


def test_signal_handlers_are_restored():
    import signal

    original = signal.getsignal(signal.SIGINT)
    stop = Event()
    with stop_on_signal(stop):
        signal.raise_signal(signal.SIGINT)
        assert stop.is_set()
    assert signal.getsignal(signal.SIGINT) is original


def test_csv_streaming_and_missing_columns(tmp_path):
    path = tmp_path / "input.csv"
    path.write_text("url,datum\nfixture://a/0,2025-01-01\n", encoding="utf-8")
    assert list(csv_records(path)) == [("fixture://a/0", "2025-01-01")]
    path.write_text("url\nfixture://a/0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Spalten"):
        list(csv_records(path))


def test_cli_idempotence_and_targeted_retry(tmp_path, nlp, monkeypatch):
    monkeypatch.setattr("data_extraction.fetch_articles.load_model", lambda model: nlp)
    path = tmp_path / "cli.sqlite"
    arguments = ["--source", "fixtures", "--db", str(path), "--fixture-count", "13"]
    assert main(arguments) == 0
    assert main(arguments) == 0
    with Database(path) as db:
        first_url = db.connection.execute(
            "SELECT url FROM articles ORDER BY rowid"
        ).fetchone()[0]
        before = db.connection.execute("SELECT count(*) FROM candidates").fetchone()[0]
        with db.transaction():
            db.connection.execute(
                "UPDATE articles SET status='failed' WHERE url=?", (first_url,)
            )
    assert main([*arguments, "--retry-url", first_url]) == 0
    with Database(path) as db:
        assert db.counts() == {"done": 12, "skipped": 1}
        assert (
            db.connection.execute("SELECT count(*) FROM candidates").fetchone()[0]
            == before
        )
        assert (
            db.connection.execute(
                "SELECT attempts FROM articles WHERE url=?", (first_url,)
            ).fetchone()[0]
            == 2
        )


def test_fixture_cli_rejects_foreign_database(tmp_path, nlp, monkeypatch):
    monkeypatch.setattr("data_extraction.fetch_articles.load_model", lambda model: nlp)
    path = tmp_path / "foreign.sqlite"
    with Database(path) as db:
        db.seed([("https://example.invalid/story", "2025")])
    with pytest.raises(SystemExit) as error:
        main(["--source", "fixtures", "--db", str(path)])
    assert error.value.code == 2
    with Database(path) as db:
        assert db.counts() == {"pending": 1}
