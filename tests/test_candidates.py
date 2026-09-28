from unittest.mock import Mock

import pytest
import spacy

from data_extraction.candidates import extract_candidates, load_model
from data_extraction.page_parser import parse_page


def test_federer_is_one_entity(nlp):
    candidates = extract_candidates(
        nlp,
        titel="Roger Federer gewinnt",
        lead="Roger Federer spielt Tennis.",
        body="Roger Federer gewinnt das Turnier in Basel.",
    )
    by_key = {(c.phrase, c.label): c for c in candidates}
    federer = by_key["Roger Federer", "PER"]
    assert (federer.count, federer.in_titel, federer.in_lead) == (3, True, True)
    assert not {"Roger", "Federer"} & {c.phrase for c in candidates}
    assert ("Roger Federer", "NOUN_CHUNK") not in by_key
    assert {"parser", "ner", "lemmatizer"} <= set(nlp.pipe_names)


def test_fixture_has_multiword_entity(nlp, fixture_dir):
    page = parse_page((fixture_dir / "artikel_2025_2.html").read_text())
    candidates = extract_candidates(
        nlp, titel=page.titel, lead=page.lead, body=page.body
    )
    assert any(c.phrase == "Elon Musk" and c.label == "PER" for c in candidates)


def test_surface_forms_and_field_boundaries(nlp):
    candidates = extract_candidates(
        nlp,
        titel="Die roten Autos",
        lead="Die roten Autos sind schnell.",
        body="Die roten Autos fahren. Ein Auto steht still.",
    )
    by_key = {(c.phrase, c.label): c for c in candidates}
    assert by_key["Die roten Autos", "MISC"].count == 3
    assert ("Ein Auto", "NOUN_CHUNK") in by_key
    assert extract_candidates(nlp, titel="", lead="", body="") == []


def test_model_without_required_components_is_rejected(monkeypatch):
    monkeypatch.setattr(spacy, "load", lambda name: Mock(pipe_names=["ner"]))
    with pytest.raises(ValueError, match="lemmatizer, parser"):
        load_model("incomplete")
