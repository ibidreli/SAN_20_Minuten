import re
from collections import Counter

import pytest
from bs4 import BeautifulSoup

from data_extraction.page_parser import LayoutError, clean_text, parse_page


def test_fixture_metadata(fixture_dir, fixture_metadata):
    for name, expected in fixture_metadata.items():
        raw = (fixture_dir / name).read_bytes()
        soup = BeautifulSoup(raw.decode("utf-8"), "html.parser")
        if expected.get("http") == 410:
            assert soup.article is None
            continue
        assert len(raw) == expected["bytes"], name
        assert len(soup.find_all("article")) == 1, name
        paragraphs = soup.article.find_all("p")
        counts = Counter(" ".join(p.get("class", [])) for p in paragraphs)
        body_class, body_count = counts.most_common(1)[0]
        assert (len(paragraphs), body_count, len(paragraphs) - body_count) == (
            expected["p_total"],
            expected["p_body"],
            expected["p_other"],
        ), name
        assert body_class == expected["body_class"], name
        testids = {tag.get("data-testid") for tag in soup.select("[data-testid]")}
        assert (
            sorted(testids & {"Crosshead", "InfoBox", "Rating"}) == expected["testids"]
        )
        assert ("Crosshead" in testids) == expected["hat_crosshead"]
        assert ("InfoBox" in testids) == expected["hat_infobox"]
        text = soup.article.get_text(" ", strip=True)
        assert (
            bool(re.search(r"\((?:sda|si|dia/sda)\)", text)) == expected["agentur"]
        ), name
        assert ("Newsdesk-Team" in text) == expected["newsdesk"], name


def test_all_article_fixtures(fixture_dir, fixture_metadata):
    for name, expected in fixture_metadata.items():
        if expected.get("http") == 410:
            continue
        page = parse_page((fixture_dir / name).read_text(), "fallback")
        assert page.titel and page.lead and page.body, name
        assert page.datum != "fallback", name
        assert page.ressort != "unbekannt", name
        assert page.body_class == expected["body_class"], name
        assert page.paragraph_count == expected["p_body"], name
        for boilerplate in (
            "Sagen Sie uns",
            "Erzähl uns davon",
            "My 20 Minuten",
            "Folgst du schon",
            "Abonniere den",
            "Darum wurde das Kommentarfeld",
            "arbeitet seit 2014",
            "arbeitet seit 2020",
            "(sda)",
            "(si)",
            "(dia/sda)",
        ):
            assert boilerplate not in page.body, (name, boilerplate)


def test_reader_invitation_is_removed(fixture_dir):
    page = parse_page((fixture_dir / "artikel_2019_2.html").read_text())
    assert page.paragraph_count == 10
    assert page.kept_paragraph_count == 8
    assert "Sagen Sie uns" not in page.body
    assert "Alexander Hermann" in page.body


def test_class_hash_changes_and_embedded_boilerplate():
    html = """<article><h1>Ein Titel</h1><p>Ein Lead.</p>
    <p class="new-build">Der erste Artikelabsatz.</p>
    <p class="new-build">Der zweite Artikelabsatz. (sda)</p>
    <figure><p class="new-build">Eine Bildlegende.</p></figure>
    <div data-testid="InfoBox"><p class="new-build">Ein Hinweis.</p></div>
    <p class="new-build">(si)</p><p>Eine Umfrage?</p></article>"""
    page = parse_page(html, "2025-01-01")
    assert page.body == "Der erste Artikelabsatz.\n\nDer zweite Artikelabsatz."
    assert page.lead == "Ein Lead."
    assert page.datum == "2025-01-01"


@pytest.mark.parametrize(
    "html",
    [
        "<html></html>",
        '<article><p class="a">A</p><p class="b">B</p></article>',
        "<article><p>Nur Lead</p></article>",
        "<article></article><article></article>",
    ],
)
def test_unknown_layout_fails_explicitly(html):
    with pytest.raises(LayoutError):
        parse_page(html)


def test_metadata_graph_and_interactions():
    html = """<script type="application/ld+json">invalid</script>
    <script type="application/ld+json">{"@graph":[
    {"@type":"NewsArticle","articleSection":"Sport","datePublished":"2025-01-02"}
    ]}</script><article><h1>Titel</h1><p>Lead</p><p class="a">Text.</p></article>
    <button data-testid="RatingButton"></button><span>1’234</span>
    <button data-testid="ButtonShare"></button><span>42</span>
    <section id="comments"><button data-testid="ButtonComment"></button><span>7</span></section>"""
    page = parse_page(html)
    assert (page.ressort, page.datum) == ("Sport", "2025-01-02")
    assert (page.likes, page.shares, page.kommentare) == (1234, 42, 7)


def test_clean_text_runs_before_nlp():
    assert clean_text("NachrufRobert EUBehörde") == "Nachruf Robert EU Behörde"


@pytest.mark.parametrize(
    ("roh", "erwartet"),
    [
        # Binnenmajuskeln gehoeren zum Namen und duerfen nicht zerfallen.
        ("AfD", "AfD"),
        ("BaZ", "BaZ"),
        ("iPhone", "iPhone"),
        ("eBay", "eBay"),
        ("McLaren", "McLaren"),
        # Bindestriche halten Komposita und Eigennamen zusammen.
        ("Baden-Württemberg", "Baden-Württemberg"),
        ("Covid-19", "Covid-19"),
        ("Corona-Krise", "Corona-Krise"),
        # Echte Klebefehler werden weiterhin getrennt.
        ("NachrufRobert", "Nachruf Robert"),
        ("EUBehörde", "EU Behörde"),
        ("SchweizÖsterreich", "Schweiz Österreich"),
        # Trennzeichen ausser dem Bindestrich bleiben Worttrenner.
        ("Schweiz:Österreich", "Schweiz Österreich"),
        ("gut·schlecht", "gut schlecht"),
    ],
)
def test_clean_text_preserves_proper_names(roh, erwartet):
    assert clean_text(roh) == erwartet


def test_reader_invitation_filter_preserves_article_statements():
    html = """<article><p>Lead</p>
    <p class="a">Die Studie fragt, welche Tipps Leser für Meetings haben.</p>
    <p class="a">„Sagen Sie uns, was passiert ist“, bat die Polizei.</p>
    <p class="a">Sagen Sie uns, was Sie für Tipps für langweilige Meetings haben.</p>
    </article>"""
    page = parse_page(html)
    assert page.kept_paragraph_count == 2
    assert "Die Studie fragt" in page.body
    assert "bat die Polizei" in page.body


def test_breadcrumb_date_and_unavailable_interaction_fallbacks():
    html = """<script type="application/ld+json">[
    {"@type":"BreadcrumbList","itemListElement":[
    {"item":{"name":"Start"}},{"item":{"name":"Wissen"}}]},
    {"commentCount": 0}]</script>
    <time datetime="2025-02-03"></time>
    <article><p>Lead</p><p class="a">Artikel.</p></article>
    <div><span>3’456</span><button data-testid="ButtonComment"></button></div>
    <button data-testid="RatingButton"></button><span>unbekannt</span>"""
    page = parse_page(html)
    assert page.ressort == "Wissen"
    assert page.datum == "2025-02-03"
    assert page.kommentare == 3456
    assert page.likes is None
