import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta, datetime
import csv
import os
import concurrent.futures
import time
import threading

BASE_URL = "https://www.20min.ch/sitemap/"
ARTIKEL_BASIS = "https://www.20min.ch"
START_DATUM = date(2003, 9, 24)
CSV_DATEI = "data/20min_artikel_neu.csv"
MAX_WORKERS = 10
MAX_RETRIES = 3


# Schrittweise durch alle Tage iterieren ab letztem gespeicherten Tag
def generiere_datumsliste(start, ende):
    aktuelles_datum = start
    while aktuelles_datum <= ende:
        yield aktuelles_datum
        aktuelles_datum += timedelta(days=1)


def finde_artikel_links(datum, saved_urls):
    url = f"{BASE_URL}{datum.year:04d}/{datum.month:02d}/{datum.day:02d}"
    print(f"Lade {url} ...")

    for versuch in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                print(f"Seite nicht gefunden: {url}")
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            artikel = []

            for a in soup.find_all("a", href=True):
                href = a["href"]
                if href.startswith("/story/"):
                    voll_url = ARTIKEL_BASIS + href
                    if voll_url not in saved_urls:
                        artikel.append({"datum": datum.isoformat(), "url": voll_url})

            return artikel

        except Exception as e:
            print(f"Fehler beim Laden von {url} (Versuch {versuch}): {e}")
            if versuch < MAX_RETRIES:
                time.sleep(2**versuch)  # exponentielles Backoff
            else:
                return []


# Thread-safe Schreiben in CSV-Datei
def speichere_artikel(artikel_liste, write_lock):
    if not artikel_liste:
        return
    with write_lock:
        file_exists = os.path.isfile(CSV_DATEI)
        with open(CSV_DATEI, "a", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["datum", "url"])
            if not file_exists or os.stat(CSV_DATEI).st_size == 0:
                writer.writeheader()
            for eintrag in artikel_liste:
                writer.writerow(eintrag)


def main():
    HEUTE = date.today()
    write_lock = threading.Lock()
    # Bereits gespeicherte Daten einlesen
    saved_urls = set()
    letztes_datum = START_DATUM

    if os.path.exists(CSV_DATEI):
        with open(CSV_DATEI, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                url = row.get("url")
                datum_str = row.get("datum")
                if url:
                    saved_urls.add(url)
                try:
                    datum_obj = datetime.strptime(datum_str, "%Y-%m-%d").date()
                    if datum_obj > letztes_datum:
                        letztes_datum = datum_obj
                except:
                    continue

    # Hauptfunktion mit paralleler Verarbeitung
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        daten_generator = list(generiere_datumsliste(letztes_datum, HEUTE))
        zukunft = {
            executor.submit(finde_artikel_links, tag, saved_urls): tag
            for tag in daten_generator
        }

        gesamtzahl = 0
        for future in concurrent.futures.as_completed(zukunft):
            artikel_liste = future.result()
            speichere_artikel(artikel_liste, write_lock)
            gesamtzahl += len(artikel_liste)

    print(f"Fertig. {gesamtzahl} neue Artikel-Links gespeichert.")

    EINGABE_DATEI = "data/20min_artikel_neu.csv"
    AUSGABE_DATEI = "data/20min_artikel_sortiert.csv"

    # CSV einlesen
    with open(EINGABE_DATEI, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        daten = list(reader)

    # Nach Datum sortieren
    daten.sort(key=lambda x: datetime.strptime(x["datum"], "%Y-%m-%d"))

    # CSV zurückschreiben
    with open(AUSGABE_DATEI, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["datum", "url"])
        writer.writeheader()
        writer.writerows(daten)

    print(f"Fertig: Datei ist jetzt chronologisch sortiert → {AUSGABE_DATEI}")


if __name__ == "__main__":
    main()
