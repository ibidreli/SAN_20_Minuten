"""Lokaler Modellvergleich; kein Ersatz für den geschichteten Teampilot."""

import argparse
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path

from data_extraction.candidates import ENTITY_LABELS, extract_candidates, load_model
from data_extraction.page_parser import parse_page

MODEL_NAMES = ("de_core_news_sm", "de_core_news_md", "de_core_news_lg")
TOP_PHRASES = 50


def benchmark(model: str, directory: Path) -> dict:
    metadata = json.loads((directory / "fixtures.json").read_text(encoding="utf-8"))
    pages = {
        name: parse_page((directory / name).read_text(encoding="utf-8"))
        for name, meta in metadata.items()
        if meta.get("http") != 410
    }
    started = time.perf_counter()
    nlp = load_model(model)
    load_seconds = time.perf_counter() - started
    started = time.perf_counter()
    per_article = []
    phrases = Counter()
    for name, page in pages.items():
        candidates = extract_candidates(
            nlp, titel=page.titel, lead=page.lead, body=page.body
        )
        per_article.append(
            {
                "fixture": name,
                "entities": sum(
                    c.count for c in candidates if c.label in ENTITY_LABELS
                ),
                "candidate_rows": len(candidates),
                "body_paragraphs": page.kept_paragraph_count,
            }
        )
        for candidate in candidates:
            phrases[candidate.phrase] += candidate.count
    extraction_seconds = time.perf_counter() - started
    rss_bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform != "darwin":
        rss_bytes *= 1024
    return {
        "model": model,
        "model_version": nlp.meta["version"],
        "articles": len(pages),
        "load_seconds": load_seconds,
        "extraction_seconds": extraction_seconds,
        "peak_rss_mib": rss_bytes / 1024**2,
        "entities_per_article": sum(row["entities"] for row in per_article)
        / len(pages),
        "per_article": per_article,
        "top50": phrases.most_common(TOP_PHRASES),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=MODEL_NAMES)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parents[1] / "tests/fixtures"
    if args.output.exists():
        parser.error("Ausgabedatei existiert bereits")
    if args.dry_run:
        print(f"Plan: model={args.model} fixtures={directory} output={args.output}")
        return 0

    def deny_network(event, arguments):
        if event.startswith("socket."):
            raise RuntimeError("Netzwerk ist im Modellvergleich gesperrt")

    sys.addaudithook(deny_network)
    result = benchmark(args.model, directory)
    with args.output.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
