import os
import re
import sys
import json
import signal
import spacy
import yake
import pandas as pd
from bs4 import BeautifulSoup
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime
import trafilatura

# ---------------- Konfiguration ----------------
INPUT_CSV = "data/20min_artikel_sortiert.csv"
OUTPUT_CSV = "data/20min_metadaten_keywords.csv"
THREADS = 25
CHUNK_SIZE = 1000
SAVE_BATCH_SIZE = 100
CLEAN_TERMS_TOPN = 10  # wie viele "clean terms" pro Artikel

# spaCy nur POS-Tagging (ohne NER etc. für Speed/Stabilität)
nlp = spacy.load(
    "de_core_news_sm",
    exclude=["ner", "textcat", "parser", "senter", "attribute_ruler", "lemmatizer"],
)

# Keyword-Extractor (YAKE)
kw_extractor = yake.KeywordExtractor(lan="de", n=1, top=5)

# ---------------- Hilfsdaten (Filter) ----------------
MONTHS = {"januar","februar","märz","maerz","april","mai","juni","juli",
          "august","september","oktober","november","dezember"}
WEEKDAYS = {"montag","dienstag","mittwoch","donnerstag","freitag","samstag","sonntag"}
ADDITIONAL_STOP = {
    "publiziert", "minuten", "update", "video", "bild", "bilder", "leser", "kommentar",
    "story", "autor", "artikel", "photos", "copyright", "agenturen"
}
BLOCK_SINGLE_TOKENS = MONTHS | WEEKDAYS | ADDITIONAL_STOP

# ---------------- Bereits verarbeitete URLs ----------------
if os.path.exists(OUTPUT_CSV):
    try:
        processed_df = pd.read_csv(OUTPUT_CSV, usecols=["url"])
        processed_urls = set(processed_df["url"])
    except Exception as e:
        print(f"⚠️ Fehler beim Laden von {OUTPUT_CSV}: {e}")
        processed_urls = set()
else:
    processed_urls = set()

artikel_df = pd.read_csv(INPUT_CSV, parse_dates=["datum"])
artikel_df = artikel_df[~artikel_df["url"].isin(processed_urls)]
total_to_process = len(artikel_df)
print(f"🟢 Zu verarbeitende Artikel: {total_to_process}")

executor = None  # wird im Main gesetzt

# ---------------- Text-Cleaning ----------------
def clean_text(text: str) -> str:
    if not text:
        return text
    text = re.sub(r"([a-zäöüß])([A-ZÄÖÜ])", r"\1 \2", text)  # NachrufRobert → Nachruf Robert
    text = re.sub(r"([A-ZÄÖÜ])([A-ZÄÖÜ][a-zäöüß])", r"\1 \2", text)  # EUBehörde → EU Behörde
    text = re.sub(r"([A-Za-zÄÖÜäöüß])[:/\\|·•\-–—]+([A-Za-zÄÖÜäöüß])", r"\1 \2", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ---------------- HTML-Parsing Hilfsfunktionen ----------------
def extract_ressort_from_html(soup: BeautifulSoup) -> str:
    try:
        for block in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(block.string)
            except Exception:
                continue
            if isinstance(data, dict) and "articleSection" in data:
                return data["articleSection"]
            if isinstance(data, dict) and data.get("@type") == "BreadcrumbList":
                items = data.get("itemListElement", [])
                if len(items) >= 2:
                    return items[1]["item"]["name"]
    except Exception:
        pass
    return "unbekannt"

def extract_datum_from_html(soup: BeautifulSoup, fallback_datum):
    try:
        meta_time = soup.find("meta", {"property": "article:published_time"})
        if meta_time and meta_time.get("content"):
            return meta_time["content"]
        time_tag = soup.find("time")
        if time_tag and time_tag.get("datetime"):
            return time_tag["datetime"]
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
            except Exception:
                continue
            if isinstance(data, dict) and "datePublished" in data:
                return data["datePublished"]
    except Exception:
        pass
    return fallback_datum

def parse_count_from_sibling(button) -> int | None:
    if not button:
        return None
    span = button.find_next_sibling("span")
    if not span:
        parent = button.parent
        if parent:
            span = parent.find("span")
    if span:
        raw = span.get_text(strip=True)
        if raw:
            raw = raw.replace("’", "").replace("'", "").replace(".", "").replace(" ", "")
            if raw.isdigit():
                return int(raw)
    return None

def comments_enabled(soup: BeautifulSoup) -> bool:
    """
    Stabil: Prüft Kommentarbereich oder JSON-LD-Felder.
    """
    if soup.select_one("#commentSection") or soup.select_one("#comments"):
        return True
    # JSON-LD Fallback
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
        except Exception:
            continue
        if isinstance(data, dict) and "commentCount" in data:
            return True
        if isinstance(data, list):
            for d in data:
                if isinstance(d, dict) and "commentCount" in d:
                    return True
    return False

# ---------------- Begriffsextraktion ----------------
def extract_clean_terms(text: str, topn=CLEAN_TERMS_TOPN) -> str | None:
    doc = nlp(text)
    terms = []
    for tok in doc:
        if not tok.is_alpha:
            continue
        low = tok.text.lower()
        if low in nlp.Defaults.stop_words or low in BLOCK_SINGLE_TOKENS:
            continue
        if tok.pos_ not in ("NOUN", "PROPN"):
            continue
        if len(tok.text) < 3:
            continue
        terms.append(tok.text)

    if not terms:
        return None

    counter = Counter(terms)
    ranked = sorted(counter.items(), key=lambda kv: (kv[1], len(kv[0])), reverse=True)
    top = [w for w, _ in ranked[:topn]]
    return ", ".join(top) if top else None

# ---------------- Haupt-Worker ----------------
def fetch_keywords_and_metadata(row_dict):
    try:
        url = row_dict["url"]
        fallback_datum = row_dict["datum"]

        html = trafilatura.fetch_url(url)
        if not html:
            return None

        soup = BeautifulSoup(html, "html.parser")

        raw_text = trafilatura.extract(html)
        if not raw_text:
            return None
        text = clean_text(raw_text)

        metadata = trafilatura.extract_metadata(html)
        if not metadata:
            return None

        def extract_count(testid: str) -> int | None:
            btn = soup.find("button", {"data-testid": testid})
            return parse_count_from_sibling(btn)

        ressort = extract_ressort_from_html(soup)
        artikel_datum = extract_datum_from_html(soup, fallback_datum)

        likes = extract_count("RatingButton")
        shares = extract_count("ButtonShare")

        kommentare_erlaubt = comments_enabled(soup)
        kommentare = extract_count("ButtonComment") if kommentare_erlaubt else None

        try:
            kw_pairs = kw_extractor.extract_keywords(text)
            top_kw = sorted(kw_pairs, key=lambda x: x[1])[:5]
            keyword_data = (
                ", ".join([f"{kw} ({score:.4f})" for kw, score in top_kw]) if top_kw else None
            )
        except Exception:
            keyword_data = None

        clean_terms = extract_clean_terms(text, topn=CLEAN_TERMS_TOPN)

        return {
            "url": url,
            "datum": artikel_datum,
            "titel": metadata.title,
            "beschreibung": metadata.description,
            "autor": metadata.author,
            "quelle": metadata.sitename,
            "ressort": ressort,
            "likes": likes,
            "kommentare": kommentare,
            "kommentare_erlaubt": kommentare_erlaubt,
            "shares": shares,
            "keywords": keyword_data,
            "clean_terms": clean_terms,
        }
    except Exception as e:
        print(f"❌ Fehler bei {row_dict.get('url')}: {e}")
        return None

# ---------------- Ctrl+C Handling ----------------
def shutdown_handler(sig, frame):
    global executor
    print("\n🛑 Abbruch durch Benutzer – fahre Prozesse herunter...")
    if executor:
        executor.shutdown(wait=False, cancel_futures=True)
    sys.exit(0)

# ---------------- Main ----------------
if __name__ == "__main__":
    from multiprocessing import freeze_support

    freeze_support()
    signal.signal(signal.SIGINT, shutdown_handler)

    header_written = os.path.exists(OUTPUT_CSV) and os.path.getsize(OUTPUT_CSV) > 0
    processed_total = 0

    with ProcessPoolExecutor(max_workers=THREADS) as pool:
        executor = pool
        for i in range(0, len(artikel_df), CHUNK_SIZE):
            batch_df = artikel_df.iloc[i : i + CHUNK_SIZE]
            batch_dicts = batch_df.to_dict(orient="records")

            futures = [executor.submit(fetch_keywords_and_metadata, row) for row in batch_dicts]
            results = []

            try:
                for future in as_completed(futures):
                    result = future.result()
                    if result:
                        results.append(result)

                    if len(results) >= SAVE_BATCH_SIZE:
                        pd.DataFrame(results).to_csv(
                            OUTPUT_CSV, mode="a", index=False, header=not header_written
                        )
                        header_written = True
                        processed_total += len(results)
                        remaining = total_to_process - processed_total
                        percent_done = 100 * processed_total / max(total_to_process, 1)
                        print(
                            f"✅ {len(results)} neue Artikel gespeichert – Gesamt: {processed_total} – {percent_done:.1f}% – Verbleibend: {remaining}"
                        )
                        results.clear()

            except KeyboardInterrupt:
                shutdown_handler(None, None)

            if results:
                pd.DataFrame(results).to_csv(
                    OUTPUT_CSV, mode="a", index=False, header=not header_written
                )
                header_written = True
                processed_total += len(results)
                remaining = total_to_process - processed_total
                percent_done = 100 * processed_total / max(total_to_process, 1)
                print(
                    f"✅ {len(results)} neue Artikel gespeichert (Rest) – Gesamt: {processed_total} – {percent_done:.1f}% – Verbleibend: {remaining}"
                )
                results.clear()

    print(
        f"\n🎉 Verarbeitung abgeschlossen. Gesamt: {processed_total} Artikel gespeichert in {OUTPUT_CSV}"
    )
