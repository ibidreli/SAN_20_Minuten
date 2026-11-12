"""NER und Nominalphrasen ohne Normalisierung, Stopplisten oder Ranking."""

from dataclasses import dataclass

import spacy
from spacy.language import Language

DEFAULT_MODEL = "de_core_news_lg"
ENTITY_LABELS = {"PER", "ORG", "LOC", "MISC"}
REQUIRED_COMPONENTS = {"parser", "ner", "lemmatizer"}


@dataclass(frozen=True)
class Candidate:
    phrase: str
    label: str
    count: int
    in_titel: bool
    in_lead: bool


def load_model(model: str = DEFAULT_MODEL) -> Language:
    nlp = spacy.load(model)
    missing = REQUIRED_COMPONENTS - set(nlp.pipe_names)
    if missing:
        raise ValueError(f"Modellkomponenten fehlen: {', '.join(sorted(missing))}")
    return nlp


def extract_candidates(
    nlp: Language, *, titel: str, lead: str, body: str
) -> list[Candidate]:
    counts: dict[tuple[str, str], list[int]] = {}
    # Feldgrenzen dürfen weder Entitäten noch Nominalphrasen verbinden.
    for field_index, doc in enumerate(nlp.pipe((titel, lead, body))):
        entities = [span for span in doc.ents if span.label_ in ENTITY_LABELS]
        spans = [(span, span.label_) for span in entities]
        for chunk in doc.noun_chunks:
            if not any(
                chunk.start < entity.end and entity.start < chunk.end
                for entity in entities
            ):
                spans.append((chunk, "NOUN_CHUNK"))
        for span, label in spans:
            entry = counts.setdefault((span.text, label), [0, 0, 0])
            entry[0] += 1
            if field_index == 0:
                entry[1] = 1
            elif field_index == 1:
                entry[2] = 1
    return [
        Candidate(phrase, label, count, bool(in_titel), bool(in_lead))
        for (phrase, label), (count, in_titel, in_lead) in counts.items()
    ]
