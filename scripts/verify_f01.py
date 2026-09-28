"""Reproduzierbarer Offline-Nachweis mit echtem SIGINT und SQLite-Vergleich."""

import argparse
import json
import re
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

DEFAULT_COUNT = 650
DEFAULT_BATCH_SIZE = 25
PROCESS_TIMEOUT_SECONDS = 600
OFFLINE_BOOTSTRAP = """
import runpy
import sys
def deny_network(event, args):
    if event.startswith('socket.'):
        raise RuntimeError('Netzwerk ist im F01-Nachweis gesperrt')
sys.addaudithook(deny_network)
runpy.run_module('data_extraction.fetch_articles', run_name='__main__')
"""


def cli_command(database: Path, count: int, batch_size: int) -> list[str]:
    return [
        sys.executable,
        "-u",
        "-c",
        OFFLINE_BOOTSTRAP,
        "--source",
        "fixtures",
        "--db",
        str(database),
        "--fixture-count",
        str(count),
        "--batch-size",
        str(batch_size),
    ]


def snapshot(database: Path) -> dict:
    with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
        return {
            "articles": connection.execute("SELECT count(*) FROM articles").fetchone()[
                0
            ],
            "statuses": dict(
                connection.execute(
                    "SELECT status, count(*) FROM articles GROUP BY status"
                )
            ),
            "candidates": connection.execute(
                "SELECT count(*) FROM candidates"
            ).fetchone()[0],
            "max_attempts": connection.execute(
                "SELECT max(attempts) FROM articles"
            ).fetchone()[0],
        }


def run_cli(
    command: list[str], *, interrupt_after: int | None = None
) -> tuple[float, dict]:
    started = time.monotonic()
    before_signal = {}
    database = Path(command[command.index("--db") + 1])
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    ) as process:
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
                match = re.search(r"Verarbeitet=(\d+)", line)
                if (
                    interrupt_after is not None
                    and match
                    and int(match[1]) >= interrupt_after
                ):
                    before_signal = snapshot(database)
                    process.send_signal(signal.SIGINT)
                    interrupt_after = None
            code = process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
            expected_code = 130 if before_signal else 0
            if code != expected_code:
                raise RuntimeError(f"CLI endete mit {code}, erwartet {expected_code}")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=PROCESS_TIMEOUT_SECONDS)
    return time.monotonic() - started, before_signal


def compare_databases(full: Path, resumed: Path) -> None:
    with sqlite3.connect(full) as connection:
        connection.execute("ATTACH DATABASE ? AS resumed", (str(resumed),))
        for table in ("articles", "candidates"):
            columns = [
                row[1]
                for row in connection.execute(f"PRAGMA table_info({table})")
                if row[1] != "fetched_at"
            ]
            fields = ", ".join(columns)
            for left, right in (("main", "resumed"), ("resumed", "main")):
                difference = connection.execute(
                    f"SELECT {fields} FROM {left}.{table} EXCEPT SELECT {fields} FROM {right}.{table}"
                ).fetchone()
                if difference is not None:
                    raise AssertionError(f"Unterschied in {table}")


def check_no_fulltext(database: Path, fixture_dir: Path) -> dict:
    from data_extraction.page_parser import parse_page

    with sqlite3.connect(database) as connection:
        schema = dict(
            connection.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
        )
        if set(schema) != {"articles", "candidates"}:
            raise AssertionError("Unerwartete Tabellen")
        for definition in schema.values():
            if re.search(
                r"\b(body|html|fulltext|content)\b", definition, re.IGNORECASE
            ):
                raise AssertionError("Volltextspalte gefunden")
        metadata = json.loads(
            (fixture_dir / "fixtures.json").read_text(encoding="utf-8")
        )
        checked = 0
        matches = 0
        for name, meta in metadata.items():
            if meta.get("http") == 410:
                continue
            page = parse_page((fixture_dir / name).read_text(encoding="utf-8"))
            # Titel und Lead sind erlaubt; geprüft werden Körper und substanzielle Absätze.
            needles = [
                page.body,
                *(part for part in page.body.split("\n\n") if len(part) >= 80),
            ]
            for needle in needles:
                checked += 1
                for table in schema:
                    fields = [
                        row[1]
                        for row in connection.execute(f"PRAGMA table_info({table})")
                        if row[2] == "TEXT"
                    ]
                    condition = " OR ".join(
                        f"instr(COALESCE({field}, ''), ?) > 0" for field in fields
                    )
                    matches += connection.execute(
                        f"SELECT count(*) FROM {table} WHERE {condition}",
                        [needle] * len(fields),
                    ).fetchone()[0]
        if matches:
            raise AssertionError(f"{matches} Volltexttreffer")
        entity = connection.execute(
            "SELECT url, phrase, label, count FROM candidates WHERE phrase='Elon Musk' AND label='PER' LIMIT 1"
        ).fetchone()
        if entity is None:
            raise AssertionError("Fixture-Mehrwortentität fehlt")
        return {
            "schema": schema,
            "checked_texts": checked,
            "fulltext_matches": matches,
            "entity": entity,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=DEFAULT_COUNT)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.count < 2 * args.batch_size or args.batch_size <= 0:
        parser.error("Mindestens zwei positive Batches sind erforderlich")
    directory = args.output_dir.resolve()
    full = directory / "uninterrupted.sqlite"
    resumed = directory / "resumed.sqlite"
    if any(path.exists() for path in (full, resumed, directory / "evidence.json")):
        parser.error(
            "Nachweisdateien existieren bereits; bitte neues Ausgabeverzeichnis wählen"
        )
    full_command = cli_command(full, args.count, args.batch_size)
    resume_command = cli_command(resumed, args.count, args.batch_size)
    if args.dry_run:
        for command in (full_command, resume_command):
            subprocess.run([*command, "--dry-run"], check=True)
        print(
            "Plan: Vollständiger Fixture-Lauf, SIGINT im zweiten Lauf, Neustart, SQL-Vergleich."
        )
        return 0
    directory.mkdir(parents=True, exist_ok=True)
    full_seconds, _ = run_cli(full_command)
    interrupted_seconds, before_signal = run_cli(
        resume_command, interrupt_after=args.count // 2
    )
    after_signal = snapshot(resumed)
    if not before_signal or not after_signal["statuses"].get("pending"):
        raise AssertionError("Kein Abbruch mitten im Lauf nachgewiesen")
    resumed_seconds, _ = run_cli(resume_command)
    compare_databases(full, resumed)
    fixture_dir = Path(__file__).resolve().parents[1] / "tests/fixtures"
    evidence = {
        "count": args.count,
        "batch_size": args.batch_size,
        "uninterrupted": snapshot(full),
        "before_sigint": before_signal,
        "after_sigint": after_signal,
        "resumed": snapshot(resumed),
        "identical_except_fetched_at": True,
        "seconds": {
            "uninterrupted": full_seconds,
            "interrupted": interrupted_seconds,
            "resumed": resumed_seconds,
        },
        "database_bytes": full.stat().st_size,
        "privacy": check_no_fulltext(full, fixture_dir),
    }
    with (directory / "evidence.json").open("x", encoding="utf-8") as handle:
        json.dump(evidence, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
