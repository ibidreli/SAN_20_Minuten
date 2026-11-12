"""Begrenzte Batches, austauschbare Quelle und atomare Fortschrittssicherung."""

import argparse
import csv
import signal
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from threading import Event

from data_extraction.candidates import DEFAULT_MODEL, extract_candidates, load_model
from data_extraction.db import Database
from data_extraction.page_parser import LayoutError, parse_page
from data_extraction.sources import HttpSource, Source

DEFAULT_WORKERS = 4
DEFAULT_BATCH_SIZE = 25
TERMINAL_HTTP_CODES = {404, 410}


@contextmanager
def stop_on_signal(stop: Event):
    def request_stop(signum, frame):
        stop.set()

    previous = {
        sig: signal.signal(sig, request_stop) for sig in (signal.SIGINT, signal.SIGTERM)
    }
    try:
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def run(
    db: Database,
    source: Source,
    nlp,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    workers: int = DEFAULT_WORKERS,
    stop: Event | None = None,
) -> dict[str, int]:
    if batch_size <= 0 or workers <= 0:
        raise ValueError("Batchgrösse und Workerzahl müssen positiv sein")
    stop = stop if stop is not None else Event()
    started = time.monotonic()
    processed = failures = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        while not stop.is_set():
            rows = db.pending_urls(batch_size)
            if not rows:
                break
            responses = pool.map(source.fetch, (row["url"] for row in rows))
            with db.transaction():
                for row, (status, html) in zip(rows, responses):
                    url = row["url"]
                    if status in TERMINAL_HTTP_CODES:
                        db.mark_skipped(url, status)
                    elif status != 200 or not html:
                        db.mark_failed(url, status)
                        failures += 1
                    else:
                        try:
                            page = parse_page(html, row["datum"])
                        except LayoutError as error:
                            print(f"Parserfehler {url}: {error}", flush=True)
                            db.mark_failed(url, status)
                            failures += 1
                        else:
                            candidates = extract_candidates(
                                nlp, titel=page.titel, lead=page.lead, body=page.body
                            )
                            db.mark_done(url, page, candidates)
                            del page, candidates
                    processed += 1
                    del html
            counts = db.counts()
            elapsed = max(time.monotonic() - started, 0.001)
            rate = processed / elapsed
            remaining = counts.get("pending", 0)
            print(
                f"Verarbeitet={processed} done={counts.get('done', 0)} "
                f"failed={counts.get('failed', 0)} skipped={counts.get('skipped', 0)} "
                f"pending={remaining} Durchsatz={rate:.2f}/s "
                f"Fehlerquote={failures / processed:.1%} Restdauer={remaining / rate:.1f}s",
                flush=True,
            )
    if stop.is_set():
        print(
            "Abbruch: laufender Batch committet; Neustart verarbeitet pending.",
            flush=True,
        )
    return db.counts()


def csv_records(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {"url", "datum"} <= set(reader.fieldnames):
            raise ValueError("CSV benötigt die Spalten url und datum")
        for row in reader:
            if row["url"]:
                yield row["url"], row["datum"] or None


def positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Wert muss positiv sein")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="F01: Artikel zu Kandidaten verdichten"
    )
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument(
        "--input", type=Path, help="URL-Datum-CSV; nur für eine neue Datenbank"
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch-size", type=positive_int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--workers", type=positive_int, default=DEFAULT_WORKERS)
    parser.add_argument("--retry-failed", action="store_true")
    parser.add_argument(
        "--retry-url",
        action="append",
        help="Nur diese fehlgeschlagene URL erneut versuchen",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Plan ohne Abruf, Modellladen oder Schreibzugriff",
    )
    args = parser.parse_args(argv)
    if args.retry_failed and args.retry_url:
        parser.error("--retry-failed und --retry-url sind Alternativen")
    if not args.db.exists() and not args.input:
        parser.error("Eine neue Datenbank benötigt --input")
    if args.dry_run:
        print(
            f"Plan: db={args.db} model={args.model} batch_size={args.batch_size} "
            f"workers={args.workers} input={args.input} "
            f"retry_failed={args.retry_failed} retry_url={args.retry_url}"
        )
        return 0
    source = HttpSource()
    stop = Event()
    with stop_on_signal(stop):
        nlp = load_model(args.model)
        with Database(args.db) as db:
            if args.input:
                db.seed(csv_records(args.input))
            if args.retry_failed or args.retry_url:
                db.reset_failed(args.retry_url)
            counts = run(
                db,
                source,
                nlp,
                batch_size=args.batch_size,
                workers=args.workers,
                stop=stop,
            )
    if stop.is_set():
        return 130
    return 1 if counts.get("failed") else 0


if __name__ == "__main__":
    raise SystemExit(main())
