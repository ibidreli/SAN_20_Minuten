"""Bisheriger Einstiegspunkt; die Implementierung liegt in fetch_articles."""


def main():
    if __package__:
        from data_extraction.fetch_articles import main as fetch_main
    else:
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from data_extraction.fetch_articles import main as fetch_main
    return fetch_main()


if __name__ == "__main__":
    raise SystemExit(main())
