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
# Quellenzeile in Klammern am Ende des letzten Absatzes. Sie kombiniert
# Redaktionskürzel, Agenturen, "20 Minuten" und selten ausgeschriebene Namen:
# "(sda)", "(chi/sep/sda)", "(ann/dp/meg/jor/jep/aeg/sda)", "(ct/20 Minuten)",
# "(scc/Vasilije Mustur)". Bildnachweise ("(Quelle: YouTube)") und normale
# Klammern ("(aus Freiburg)", "(Video)") sind keine Quellenzeile.
SOURCE_SUFFIX = re.compile(r"\s*\(([^():]{1,150})\)\s*$")
# Nachrichtenagenturen; alle übrigen Kleinbuchstaben-Kürzel gelten als
# Redaktionskürzel einer Person. bang = Bang Showbiz, si = Sportinformation.
AGENCIES = frozenset(
    "sda si afp ap dpa dapd ddp apa reuters bang sid kna epd ats ansa".split()
) | {
    # Partnerdienste, die das CMS wie Autoren führt.
    "spot on news",
    "spot on",
    "spoton",
    "cover media",
    "bang showbiz",
    "heute.at",
}
KUERZEL = re.compile(r"[a-zäöü]{1,8}")
PERSON_NAME = re.compile(r"[A-ZÄÖÜ][\w'-]+(?: [A-ZÄÖÜ][\w'-]+){1,2}")


@dataclass(frozen=True)
class Source:
    kuerzel: str
    art: str  # redaktion | agentur | 20min | name


def classify_source_part(part: str) -> Source | None:
    lower = part.lower()
    if lower in AGENCIES:
        return Source(lower, "agentur")
    if lower.replace(" ", "") in {"20minuten", "20min", "20minuten.ch"}:
        return Source("20 Minuten", "20min")
    if KUERZEL.fullmatch(part):
        return Source(part, "redaktion")
    if PERSON_NAME.fullmatch(part):
        return Source(part, "name")
    return None


def split_source_suffix(text: str) -> tuple[tuple[Source, ...], str]:
    match = SOURCE_SUFFIX.search(text)
    if not match:
        return (), text
    parts = [p.strip() for p in re.split(r"[/,;]", match.group(1)) if p.strip()]
    sources = [classify_source_part(p) for p in parts]
    # Alle Teile müssen erkennbar sein, und mindestens einer darf kein
    # ausgeschriebener Name sein, sonst ist es eine gewöhnliche Klammer.
    if not sources or None in sources or all(s.art == "name" for s in sources):
        return (), text
    return tuple(sources), text[: match.start()].rstrip()


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
    art: str = "person"  # person | kuerzel | agentur | 20min | sonstige


@dataclass(frozen=True)
class Page:
    titel: str = ""
    lead: str = ""
    body: str = ""
    ressort: str = "unbekannt"
    ressort_pfad: str | None = None
    datum: str | None = None
    likes: int | None = None
    shares: int | None = None
    kommentare: int | None = None
    quellen: tuple[Source, ...] = ()
    wortanzahl: int | None = None
    views: int | None = None
    aktualisiert: str | None = None
    autoren: tuple[Author, ...] = ()
    format: str = "artikel"  # artikel | ticker
    paragraph_count: int = 0
    kept_paragraph_count: int = 0

    @property
    def quelle_kuerzel(self) -> str | None:
        # Ganze Quellenzeile wie gedruckt, z. B. "chi/sep/sda".
        return "/".join(s.kuerzel for s in self.quellen) or None


def clean_text(text: str) -> str:
    # Weiche Trennstriche und Nullbreitenzeichen entfernen.
    text = re.sub("[\u00ad\u200b\u200c\u200d\ufeff]", "", text)
    # Paare wie "Biontech/Pfizer" oder "Dumoulin/Zosso" in zwei Wörter
    # trennen, damit beide Namen erkannt werden.
    text = re.sub(
        r"([A-Za-zÄÖÜäöü\u00df])[:/\\|·•]+([A-Za-zÄÖÜäöü\u00df])", r"\1 \2", text
    )
    # Bewusst keine Trennung an Binnenmajuskeln oder Bindestrichen: Eine
    # Messung an 150 Artikeln ergab dabei fast nur Schäden (ChatGPT,
    # PostFinance, DJs, Port-au-Prince, Start-up) und einen einzigen echten
    # Klebefehler. get_text(" ") trennt HTML-Elemente bereits mit Leerzeichen.
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
    # Ohne articleSection die tiefste Stufe des Breadcrumb-Pfads. Der letzte
    # Breadcrumb-Eintrag ist der Artikel selbst und nie ein Ressort.
    path = extract_ressort_path(soup)
    return path.split(RESSORT_PATH_SEPARATOR)[-1] if path else "unbekannt"


RESSORT_PATH_SEPARATOR = " > "


def extract_ressort_path(soup: BeautifulSoup) -> str | None:
    # Breadcrumb "News > Ausland > Donald Trump > <Titel>": ohne die Wurzel
    # und ohne den Artikel selbst bleibt die Ressort-Hierarchie.
    for node in json_ld_nodes(soup):
        if node.get("@type") != "BreadcrumbList":
            continue
        names = []
        for entry in node.get("itemListElement", [])[1:-1]:
            item = entry.get("item") if isinstance(entry, dict) else None
            name = (item.get("name") if isinstance(item, dict) else None) or (
                entry.get("name") if isinstance(entry, dict) else None
            )
            if isinstance(name, str) and name.strip():
                names.append(name.strip())
        if names:
            return RESSORT_PATH_SEPARATOR.join(names)
    return None


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


AGENCY_NAMES = {
    "deutsche presse-agentur": "dpa",
    "agence france-presse": "afp",
    "keystone-sda": "sda",
    "schweizerische depeschenagentur": "sda",
    "associated press": "ap",
}
HOUSE_NAMES = {"20 minuten", "20 minuten newsdesk", "20m", "2n", "20min"}


def classify_author(name: str, kuerzel: str | None, autor_id: int | None) -> Author:
    lower, short = name.lower(), (kuerzel or "").lower()
    if lower in HOUSE_NAMES or short in HOUSE_NAMES:
        return Author(name, kuerzel, autor_id, "20min")
    if lower in AGENCIES or short in AGENCIES or lower in AGENCY_NAMES:
        code = AGENCY_NAMES.get(lower) or (lower if lower in AGENCIES else short)
        return Author(name, code, autor_id, "agentur")
    if autor_id is None and (
        KUERZEL.fullmatch(name) or re.fullmatch(r"[A-ZÄÖÜ]{2,4}", name)
    ):
        # Nur ein Redaktionskürzel bekannt (Artikel ca. 2008-2020).
        return Author(lower, lower, None, "kuerzel")
    if " " in name or autor_id is not None:
        return Author(name, kuerzel, autor_id, "person")
    return Author(name, kuerzel, autor_id, "sonstige")


def clean_author_name(name: str) -> str:
    # Ortszusätze der Reporter entfernen: "Tobias Wedermann (aus Köln)",
    # "Florian Gnägi aus Stuttgart", "Thomas Sennhauser (vor Ort)". Zusätze
    # ohne "aus" ("Tobias Wedermann Bukarest") bleiben; dort vereint die ID.
    name = re.sub(r"\s*\([^)]*\)", "", name)
    name = re.sub(r"\s+(aus|vor Ort)\b.*$", "", name)
    return re.sub(r"\s+", " ", name).strip()


def extract_authors(meta: dict) -> tuple[Author, ...]:
    # Reihenfolge wie auf der Seite. Das CMS führt Kombinationen wie
    # "AFP/sys", "chi/sep" oder "Marius Egger/rub" als einen einzigen Autor;
    # sie werden in ihre Bestandteile zerlegt.
    authors = []
    for entry in meta.get("authors") or []:
        if not isinstance(entry, dict):
            continue
        name = clean_author_name(str(entry.get("name") or ""))
        if not name:
            continue
        kuerzel = str(entry.get("shortName") or "").strip() or None
        autor_id = parse_count(entry.get("publicUserId"))
        parts = [p.strip() for p in re.split(r"[/,]", name) if p.strip()]
        if len(parts) == 1:
            authors.append(classify_author(name, kuerzel, autor_id))
            continue
        for part in parts:
            authors.append(classify_author(part, None, None))
    return tuple(authors)


def is_boilerplate(paragraph: Tag, article: Tag) -> bool:
    for tag in (paragraph, *paragraph.parents):
        if tag is article:
            break
        if tag.name == "article":
            return True  # eingebettete Artikel-Karte
        if (
            tag.name in EXCLUDED_TAGS
            or tag.get("data-testid") in EXCLUDED_TESTIDS
            or tag.get("id") in {"comments", "commentSection"}
        ):
            return True
    text = paragraph.get_text(" ", strip=True)
    return any(re.fullmatch(pattern, text) for pattern in READER_INVITATIONS)


def is_author_bio(paragraph: Tag, author_names: list[str]) -> bool:
    # Die Autorenbiografie am Artikelende ("Lea Hafen ist seit Mai 2025 bei
    # 20 Minuten ...") hat keine stabile Klasse. Erkennbar ist sie an der
    # Zeile "von <Name>" direkt davor oder daran, dass sie mit dem Namen
    # eines Artikelautors beginnt.
    # Biografien nennen immer den Arbeitgeber ("... bei 20 Minuten"); ohne
    # diese Bedingung würden Ticker-Einträge mit Zeile "von <Name>" davor
    # fälschlich als Biografie gelten.
    text = paragraph.get_text(" ", strip=True)
    if "20 Minuten" not in text:
        return False
    previous = paragraph.find_previous_sibling()
    if previous is not None and re.match(
        r"[Vv]on\s+\S", previous.get_text(" ", strip=True)
    ):
        return True
    return any(text.startswith(name + " ") for name in author_names)


BLOCK_TAGS = {"div", "p", "ul", "ol", "h1", "h2", "h3", "h4", "figure",
              "section", "article", "blockquote", "table", "header"}
# Ein Text-Div muss sich mindestens so oft wiederholen, um als Fliesstext zu
# gelten (Interview-Antworten), und zusammen so viele Wörter haben.
MIN_DIV_BLOCKS = 3
MIN_DIV_WORDS = 50


def is_text_div(tag: Tag) -> bool:
    # Interview-Antworten stehen in <div> ohne Blockelemente darin.
    return tag.name == "div" and not tag.find(BLOCK_TAGS)


# Das CMS markiert jeden Inhaltsblock mit einem type-Attribut. Fliesstext sind
# normale Absätze und Interview-Segmente; alles andere (infobox, poll, ad,
# image, embed, quote, crosshead, lead, title, authors, publishDate) nicht.
BODY_TYPES = {"textBlockArray", "interviewSegment"}
NON_BODY_TYPES = {"infobox", "poll", "ad", "image", "embed", "slideshow", "quote",
                  "videocms", "authors", "publishDate", "lead", "title"}


def typed_body_blocks(roots: list[Tag]) -> list[str]:
    """Fliesstext über die type-Attribute des CMS, in Dokumentreihenfolge."""
    parts = []
    for root in roots:
        for tag in root.find_all(attrs={"type": True}):
            if tag.get("type") not in BODY_TYPES:
                continue
            inside_other = False
            for parent in tag.parents:
                if parent is root:
                    break
                if parent.name == "article" or parent.get("type") in NON_BODY_TYPES | BODY_TYPES:
                    inside_other = True
                    break
            text = tag.get_text(" ", strip=True)
            if text and not inside_other:
                parts.append(text)
    return parts


def typed_text(roots: list[Tag], block_type: str) -> str:
    for root in roots:
        tag = root.find(attrs={"type": block_type})
        if tag is not None and tag.find_parent("article") is root:
            return tag.get_text(" ", strip=True)
    return ""


def body_blocks(
    roots: list[Tag], author_names: list[str]
) -> tuple[list[str], int]:
    """Rückfallebene ohne type-Attribute: Fliesstext über die CSS-Klassen.

    Massgebend ist die Absatzklasse mit der grössten Textmenge, nicht die
    häufigste: In Tickern hat jeder Eintrag einen Datums-Absatz, der häufiger
    ist als der Text. Wiederkehrende Text-Divs (Interview-Antworten, Einträge
    von Sport-Tickern) kommen hinzu.
    """
    blocks = []
    for root in roots:
        for tag in root.find_all(["p", "div"]):
            if not tag.get("class") or not (tag.name == "p" or is_text_div(tag)):
                continue
            text = tag.get_text(" ", strip=True)
            if (
                text
                and not is_boilerplate(tag, root)
                and not is_author_bio(tag, author_names)
            ):
                blocks.append((tag.name, tuple(tag.get("class")), text))
    stats: dict[tuple, list[int]] = {}
    for name, cls, text in blocks:
        entry = stats.setdefault((name, cls), [0, 0])
        entry[0] += 1
        entry[1] += len(text.split())
    chosen = set()
    p_keys = [k for k in stats if k[0] == "p"]
    if p_keys:
        chosen.add(max(p_keys, key=lambda key: stats[key][::-1]))
    div_keys = [
        k
        for k in stats
        if k[0] == "div"
        and stats[k][0] >= MIN_DIV_BLOCKS
        and stats[k][1] >= MIN_DIV_WORDS
    ]
    if div_keys:
        chosen.add(max(div_keys, key=lambda key: stats[key][::-1]))
    parts = [text for name, cls, text in blocks if (name, cls) in chosen]
    return parts, sum(stats[k][0] for k in chosen)


def parse_page(html: str, fallback_datum: str | None = None) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    # In Artikel eingebettete Artikel-Karten ("Mehr zum Thema") sind
    # verschachtelte <article>; massgebend sind nur die äussersten. Mehrere
    # gleichrangige <article> sind die Einträge eines Livetickers.
    roots = [a for a in soup.find_all("article") if a.find_parent("article") is None]
    if not roots:
        raise LayoutError("Kein article-Element gefunden")
    article = roots[0]
    format_ = "ticker" if len(roots) > 1 else "artikel"
    paragraphs = [p for root in roots for p in root.find_all("p")]
    meta = next_data_meta(soup)
    autoren = extract_authors(meta)
    author_names = [a.name for a in autoren if " " in a.name]
    # Videos und Bildstrecken haben keinen Fliesstext: Titel und Lead
    # bleiben verwertbar, der Körper ist leer.
    # Pro <article> entscheiden: Hat es Fliesstext-Blöcke mit type-Attribut,
    # gelten nur diese. Die übrigen (ältere Layouts, Ticker-Einträge ohne
    # type) laufen gemeinsam durch die Klassen-Heuristik, weil ein einzelner
    # Ticker-Eintrag zu wenige Absätze für eine Mehrheitsentscheidung hat.
    raw_parts, untyped = [], []
    for root in roots:
        parts = typed_body_blocks([root])
        if parts:
            raw_parts += parts
        else:
            untyped.append(root)
    paragraph_count = len(raw_parts)
    if untyped:
        parts, count = body_blocks(untyped, author_names)
        raw_parts += parts
        paragraph_count += count
    # Quellenzeile: eigener Block "( AFP/chk )" oder Klammer am Textende. Vor
    # jeder Bereinigung lesen: AGENCY_SUFFIX würde "(sda)" entfernen und
    # clean_text macht aus "kmo/sda" "kmo sda".
    quellen: tuple[Source, ...] = ()
    agencies_block = typed_text(roots, "agencies")
    if agencies_block:
        quellen, _ = split_source_suffix(agencies_block)
    if raw_parts:
        suffix_quellen, raw_parts[-1] = split_source_suffix(raw_parts[-1])
        # Block "( hua )" und Klammer "(hua/sda)" können sich ergänzen.
        seen = {s.kuerzel for s in quellen}
        quellen += tuple(s for s in suffix_quellen if s.kuerzel not in seen)
    body_parts = []
    for text in raw_parts:
        text = clean_text(re.sub(AGENCY_SUFFIX, "", text))
        if text:
            body_parts.append(text)
    lead_tag = next(
        (
            p
            for root in roots
            for p in root.find_all("p")
            if not p.get("class")
            and p.find_parent("article") is root
            and not is_boilerplate(p, root)
        ),
        None,
    )
    lead = clean_text(
        typed_text(roots, "lead")
        or (lead_tag.get_text(" ", strip=True) if lead_tag else "")
    )
    if format_ == "ticker" or not lead:
        # Liveticker haben keinen Lead im Artikel; der Teaser des CMS ist der
        # Lead, den die Startseite zeigt.
        teaser = ((meta.get("teaser") or {}).get("default") or {}).get("lead")
        if isinstance(teaser, str) and teaser.strip():
            lead = clean_text(teaser)
    # Die sichtbare Überschrift steht im aktuellen Layout ausserhalb von
    # <article>; og:title ist eine abweichende Social-Media-Variante.
    title_tag = article.find("h1") or soup.find("h1")
    title_meta = soup.find("meta", property="og:title")
    titel = (
        title_tag.get_text(" ", strip=True)
        if title_tag
        else (title_meta.get("content", "") if title_meta else "")
    )
    if not titel.strip():
        raise LayoutError("Keine Überschrift gefunden")

    community = (meta.get("clientdata") or {}).get("community") or {}
    settings = meta.get("settings") or {}

    return Page(
        titel=clean_text(titel),
        lead=lead,
        format=format_,
        body="\n\n".join(body_parts),
        ressort=extract_ressort_from_html(soup),
        ressort_pfad=extract_ressort_path(soup),
        datum=extract_datum_from_html(soup, fallback_datum),
        # "likes" im Community-Objekt ist durchgehend 0; die sichtbare
        # Reaktionszahl (und die Spalte likes der alten CSV) ist contentRatings.
        likes=parse_count(community.get("contentRatings")),
        shares=parse_count(community.get("shares")),
        quellen=quellen,
        kommentare=(
            parse_count(community.get("comments"))
            if settings.get("commentingEnabled")
            else None
        ),
        # Wörter im extrahierten Körper (ohne Titel, Lead, Infobox). Das
        # wordCount-Feld des CMS liegt rund 80 % über dem sichtbaren Text und
        # ist nicht nachvollziehbar, darum zählen wir selbst.
        wortanzahl=sum(len(part.split()) for part in body_parts),
        views=parse_count(community.get("views")),
        aktualisiert=meta.get("updated") or None,
        autoren=autoren,
        paragraph_count=paragraph_count,
        kept_paragraph_count=len(body_parts),
    )
