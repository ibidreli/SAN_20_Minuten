"""Lädt die Tabellen der Crawler-Datenbank als pandas-DataFrames.

Alle Notebooks und `netzwerk.py` lesen die Daten nur über dieses Modul.
So gelten dieselben Filter (nur fertige Artikel, Zeitraum, Format) überall.

Die Datenbank wird nur lesend geöffnet; ein laufender Crawl stört nicht.
"""

import os
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
# Mit der Umgebungsvariable SAN_DB lassen sich die Notebooks auf einer
# anderen Datenbank ausführen, z. B. auf einer kleinen Test-DB.
DEFAULT_DB = Path(os.environ.get("SAN_DB", ROOT / "data" / "articles.sqlite"))
RESSORT_SEPARATOR = " > "
# Likes, Shares und Kommentare gibt es erst seit dem Reaktionssystem des
# neuen CMS (Mai 2020). Davor liefert die Quelle 0 bzw. keine Kommentare:
# das ist keine Messung, sondern fehlend. Geprüft am Monatsmedian, im neuen
# Crawl und in der alten CSV gleich.
REAKTIONEN_AB = "2020-06-01"
REAKTIONEN = ["likes", "shares", "kommentare"]
# Die oberste Stufe des Ressort-Pfads enthält neben den Ressorts auch
# Ereignisseiten ("Ski-WM", "Iran-Krieg", "#WIRSINDZUKUNFT"). Für Vergleiche
# zählen nur die Ressorts mit mindestens ~1 % der Artikel; der Rest wird zu
# "andere". Coronavirus war 2020/21 ein eigenes Ressort und bleibt.
HAUPTRESSORTS = [
    "Regionen", "Ausland", "Schweiz", "Sport", "People", "Wirtschaft",
    "Lifestyle", "Wissen", "Community", "Digital", "Coronavirus",
]


def connect(db_path: str | Path = DEFAULT_DB) -> sqlite3.Connection:
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"Datenbank fehlt: {db_path}")
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


SNAPSHOT_DB = ROOT / "data" / "articles_snapshot.sqlite"


def standard_db() -> Path:
    """Datenbank für die Notebooks.

    Die Hauptdatenbank, sobald sie Keywords und Personen enthält (also nach
    dem Crawl und den Schritten keywords/autoren). Bis dahin die Kopie
    `articles_snapshot.sqlite`, falls vorhanden. SAN_DB hat immer Vorrang.
    """
    if "SAN_DB" in os.environ:
        return DEFAULT_DB
    if DEFAULT_DB.exists():
        with connect(DEFAULT_DB) as connection:
            if has_table(connection, "keywords") and has_table(connection, "article_persons"):
                return DEFAULT_DB
    if SNAPSHOT_DB.exists():
        return SNAPSHOT_DB
    return DEFAULT_DB


def has_table(connection: sqlite3.Connection, name: str) -> bool:
    return (
        connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
        ).fetchone()
        is not None
    )


def load_articles(
    db_path: str | Path = DEFAULT_DB,
    *,
    von: str | None = None,
    bis: str | None = None,
    alle_status: bool = False,
    reaktionen_vor_start: bool = False,
) -> pd.DataFrame:
    """Artikel mit abgeleiteten Spalten.

    `von`/`bis` sind ISO-Daten (inklusive), z. B. "2020-01-01".
    Zusätzliche Spalten: jahr, monat, ressort_1 (oberste Ressort-Stufe),
    hauptressort (ressort_1 auf HAUPTRESSORTS reduziert, sonst "andere"),
    ticker (bool), reaktionen_gueltig (bool), interaktionen
    (likes + shares + kommentare).

    Vor `REAKTIONEN_AB` werden likes/shares/kommentare auf fehlend gesetzt,
    ausser `reaktionen_vor_start=True` (Rohwerte, nur für die EDA).
    """
    with connect(db_path) as connection:
        articles = pd.read_sql_query("SELECT * FROM articles", connection)
    if not alle_status:
        articles = articles[articles["status"] == "done"].copy()
    articles["datum"] = pd.to_datetime(articles["datum"], utc=True, errors="coerce")
    articles["aktualisiert"] = pd.to_datetime(
        articles["aktualisiert"], utc=True, errors="coerce"
    )
    if von:
        articles = articles[articles["datum"] >= pd.Timestamp(von, tz="UTC")]
    if bis:
        articles = articles[
            articles["datum"] < pd.Timestamp(bis, tz="UTC") + pd.Timedelta(days=1)
        ]
    # Zeitstempel sind UTC; für Jahres- und Monatsgrenzen zählt die Schweizer Zeit.
    lokal = articles["datum"].dt.tz_convert("Europe/Zurich")
    articles["jahr"] = lokal.dt.year.astype("Int64")
    articles["monat"] = lokal.dt.strftime("%Y-%m")
    articles["quartal"] = (
        lokal.dt.year.astype("Int64").astype(str) + "-Q" + lokal.dt.quarter.astype("Int64").astype(str)
    )
    articles["wochentag"] = lokal.dt.dayofweek
    articles["stunde"] = lokal.dt.hour
    articles["ressort_1"] = (
        articles["ressort_pfad"].fillna("").str.split(RESSORT_SEPARATOR).str[0]
    ).replace("", "unbekannt")
    articles["hauptressort"] = articles["ressort_1"].where(
        articles["ressort_1"].isin(HAUPTRESSORTS), "andere"
    )
    articles["ticker"] = articles["format"] == "ticker"
    articles["reaktionen_gueltig"] = articles["datum"] >= pd.Timestamp(
        REAKTIONEN_AB, tz="UTC"
    )
    if not reaktionen_vor_start:
        articles[REAKTIONEN] = articles[REAKTIONEN].astype("Float64")
        articles.loc[~articles["reaktionen_gueltig"], REAKTIONEN] = pd.NA
    articles["interaktionen"] = articles[REAKTIONEN].sum(
        axis=1, min_count=1
    )
    return articles.reset_index(drop=True)


def load_keywords(
    db_path: str | Path = DEFAULT_DB, *, mit_ressort: bool = False
) -> pd.DataFrame:
    """Keywords pro Artikel (Tabelle aus `data_extraction.keywords`)."""
    with connect(db_path) as connection:
        if not has_table(connection, "keywords"):
            raise RuntimeError(
                "Tabelle keywords fehlt: zuerst "
                "`python -m data_extraction.keywords --db ...` ausführen"
            )
        keywords = pd.read_sql_query("SELECT * FROM keywords", connection)
    if not mit_ressort:
        keywords = keywords[keywords["typ"] != "RESSORT"]
    return keywords.reset_index(drop=True)


def load_persons(
    db_path: str | Path = DEFAULT_DB, *, rollen: tuple[str, ...] = ("autor",)
) -> pd.DataFrame:
    """Personen pro Artikel (Tabelle aus `data_extraction.autoren`)."""
    with connect(db_path) as connection:
        if not has_table(connection, "article_persons"):
            raise RuntimeError(
                "Tabelle article_persons fehlt: zuerst "
                "`python -m data_extraction.autoren --db ...` ausführen"
            )
        persons = pd.read_sql_query("SELECT * FROM article_persons", connection)
    persons = persons[persons["rolle"].isin(rollen)]
    persons["aufgeloest"] = ~persons["person"].str.startswith("kürzel:")
    return persons.reset_index(drop=True)


def load_table(db_path: str | Path, name: str) -> pd.DataFrame:
    """Beliebige Tabelle roh laden (article_authors, article_kuerzel, personen …)."""
    with connect(db_path) as connection:
        if not has_table(connection, name):
            raise RuntimeError(f"Tabelle {name} fehlt in {db_path}")
        return pd.read_sql_query(f"SELECT * FROM {name}", connection)


def candidate_counts(db_path: str | Path = DEFAULT_DB) -> pd.DataFrame:
    """Anzahl Kandidaten pro Artikel, ohne die grosse Tabelle zu laden."""
    with connect(db_path) as connection:
        return pd.read_sql_query(
            "SELECT url, count(*) AS kandidaten FROM candidates GROUP BY url",
            connection,
        )
