"""HTML-Auswertung; der Artikelkörper bleibt ausschliesslich im Speicher."""

import json
import re
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

EXCLUDED_TAGS = {"figure", "figcaption", "aside", "script", "style", "nav", "footer"}
EXCLUDED_TESTIDS = {
    "InfoBox",
    "Rating",
    "RelatedArticles",
    "Related",
    "Comments",
    "CommentSection",
    "Disclaimer",
    "Newsletter",
    "PushNotification",
    "WhatsApp",
}
AGENCY_SUFFIX = r"\s*\((?:sda|si|afp|dpa|ap|reuters|dia/sda)\)\s*$"
READER_INVITATIONS = (
    r"Sagen Sie uns, [^.!?]+[.!?]",
    r"Hast du [^?]+\?\s*Erzähl uns davon\.",
)


class LayoutError(ValueError):
    """Das Layout erlaubt keine eindeutige Auswahl des Artikelkörpers."""


@dataclass(frozen=True)
class Author:
    # Rohwerte aus dem CMS. Ältere Artikel tragen oft nur ein Kürzel als Name
    # und keine ID; die Zuordnung Kürzel -> Person folgt in der Analyse.
    name: str
    kuerzel: str | None = None
    autor_id: int | None = None


@dataclass(frozen=True)
class Page:
    titel: str = ""
    lead: str = ""
    body: str = ""
    ressort: str = "unbekannt"
    datum: str | None = None
    likes: int | None = None
    shares: int | None = None
    kommentare: int | None = None
    wortanzahl: int | None = None
    autoren: tuple[Author, ...] = ()
    body_class: str = ""
    paragraph_count: int = 0
    kept_paragraph_count: int = 0


def clean_text(text: str) -> str:
    # Zusammengeklebte Woerter trennen, ohne Eigennamen mit Binnenmajuskel zu
    # zerlegen. Der linke Teil braucht mindestens drei Kleinbuchstaben, sonst
    # fallen AfD, BaZ, iPhone, eBay und McLaren auseinander. Der Preis sind
    # Klebefehler nach sehr kurzen Woertern wie "im" oder "zu".
    text = re.sub(r"([a-zäöü\u00df]{3,})([A-ZÄÖÜ])", r"\1 \2", text)
    text = re.sub(r"([A-ZÄÖÜ])([A-ZÄÖÜ][a-zäöü\u00df])", r"\1 \2", text)
    text = re.sub(
        r"([A-Za-zÄÖÜäöü\u00df])[:/\\|·•]+([A-Za-zÄÖÜäöü\u00df])", r"\1 \2", text
    )
    # Bindestriche nur zwischen Kleinbuchstaben aufloesen, damit
    # Baden-Wuerttemberg, Covid-19 und Corona-Krise eine Einheit bleiben.
    text = re.sub(r"([a-zäöü\u00df])[\-–—]+([a-zäöü\u00df])", r"\1 \2", text)
    return re.sub(r"\s+", " ", text).strip()


def json_ld_nodes(soup: BeautifulSoup) -> Iterator[dict]:
    def walk(value):
        if isinstance(value, list):
            for item in value:
                yield from walk(item)
        elif isinstance(value, dict):
            yield value
            yield from walk(value.get("@graph", []))

    for block in soup.find_all("script", type="application/ld+json"):
        try:
            yield from walk(json.loads(block.get_text()))
        except (ValueError, TypeError):
            continue


def extract_ressort_from_html(soup: BeautifulSoup) -> str:
    nodes = list(json_ld_nodes(soup))
    for node in nodes:
        section = node.get("articleSection")
        if isinstance(section, str) and section:
            return section
        if isinstance(section, list) and section and isinstance(section[0], str):
            return section[0]
    for node in nodes:
        if node.get("@type") == "BreadcrumbList":
            items = node.get("itemListElement", [])
            if len(items) >= 2:
                item = items[1].get("item", {})
                name = (
                    item.get("name") if isinstance(item, dict) else items[1].get("name")
                )
                if name:
                    return name
    return "unbekannt"


def extract_datum_from_html(
    soup: BeautifulSoup, fallback_datum: str | None
) -> str | None:
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"]
    time_tag = soup.find("time", datetime=True)
    if time_tag:
        return time_tag["datetime"]
    for node in json_ld_nodes(soup):
        if node.get("datePublished"):
            return node["datePublished"]
    return fallback_datum


def next_data_meta(soup: BeautifulSoup) -> dict:
    # Die Interaktionsbuttons rendert erst das Browser-JavaScript; im
    # ausgelieferten HTML stehen die Zahlen nur im Next.js-Zustand.
    script = soup.find("script", id="__NEXT_DATA__")
    if script is None:
        return {}
    try:
        meta = json.loads(script.get_text())["props"]["pageProps"]["data"][
            "content"
        ]["meta"]
    except (ValueError, TypeError, KeyError):
        return {}
    return meta if isinstance(meta, dict) else {}


def parse_count(value) -> int | None:
    raw = re.sub(r"[’'.\s]", "", str(value)) if value is not None else ""
    return int(raw) if raw.isdecimal() else None


def extract_authors(meta: dict) -> tuple[Author, ...]:
    # Reihenfolge wie auf der Seite; Agenturen (z. B. dpa) stehen als
    # gewöhnliche Einträge in derselben Liste.
    authors = []
    for entry in meta.get("authors") or []:
        if not isinstance(entry, dict):
            continue
        name = re.sub(r"\s+", " ", str(entry.get("name") or "")).strip()
        if not name:
            continue
        kuerzel = str(entry.get("shortName") or "").strip() or None
        authors.append(
            Author(name, kuerzel, parse_count(entry.get("publicUserId")))
        )
    return tuple(authors)


def is_boilerplate(paragraph: Tag, article: Tag) -> bool:
    for tag in (paragraph, *paragraph.parents):
        if tag is article:
            break
        if (
            tag.name in EXCLUDED_TAGS
            or tag.get("data-testid") in EXCLUDED_TESTIDS
            or tag.get("id") in {"comments", "commentSection"}
        ):
            return True
    text = paragraph.get_text(" ", strip=True)
    return any(re.fullmatch(pattern, text) for pattern in READER_INVITATIONS)


def parse_page(html: str, fallback_datum: str | None = None) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    articles = soup.find_all("article")
    if len(articles) != 1:
        raise LayoutError("Genau ein article-Element erwartet")
    article = articles[0]
    paragraphs = article.find_all("p")
    counts = Counter(tuple(p.get("class", [])) for p in paragraphs if p.get("class"))
    most_common = counts.most_common()
    if not most_common or (
        len(most_common) > 1 and most_common[0][1] == most_common[1][1]
    ):
        raise LayoutError("Keine eindeutige häufigste Absatzklasse")
    body_class, paragraph_count = most_common[0]
    body_parts = []
    for paragraph in paragraphs:
        if tuple(paragraph.get("class", [])) != body_class or is_boilerplate(
            paragraph, article
        ):
            continue
        text = re.sub(AGENCY_SUFFIX, "", paragraph.get_text(" ", strip=True))
        text = clean_text(text)
        if text:
            body_parts.append(text)
    if not body_parts:
        raise LayoutError("Kein Artikelkörper nach der Filterung")
    lead_tag = next((p for p in paragraphs if not p.get("class")), None)
    title_tag = article.find("h1")
    title_meta = soup.find("meta", property="og:title")
    titel = (
        title_tag.get_text(" ", strip=True)
        if title_tag
        else (title_meta.get("content", "") if title_meta else "")
    )

    meta = next_data_meta(soup)
    community = (meta.get("clientdata") or {}).get("community") or {}
    settings = meta.get("settings") or {}

    return Page(
        titel=clean_text(titel),
        lead=clean_text(lead_tag.get_text(" ", strip=True)) if lead_tag else "",
        body="\n\n".join(body_parts),
        ressort=extract_ressort_from_html(soup),
        datum=extract_datum_from_html(soup, fallback_datum),
        # "likes" im Community-Objekt ist durchgehend 0; die sichtbare
        # Reaktionszahl (und die Spalte likes der alten CSV) ist contentRatings.
        likes=parse_count(community.get("contentRatings")),
        shares=parse_count(community.get("shares")),
        kommentare=(
            parse_count(community.get("comments"))
            if settings.get("commentingEnabled")
            else None
        ),
        # Wörter im extrahierten Körper (ohne Titel, Lead, Infobox). Das
        # wordCount-Feld des CMS liegt rund 80 % über dem sichtbaren Text und
        # ist nicht nachvollziehbar, darum zählen wir selbst.
        wortanzahl=sum(len(part.split()) for part in body_parts),
        autoren=extract_authors(meta),
        body_class=" ".join(body_class),
        paragraph_count=paragraph_count,
        kept_paragraph_count=len(body_parts),
    )
