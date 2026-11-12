"""NER und Nominalphrasen mit Grundform; Stoppliste und Ranking folgen später.

Pro Kandidat speichern wir neben dem Originaltext eine Grundform und für
Nominalphrasen das Kopfnomen. Beides lässt sich nach dem Crawl nicht mehr
berechnen, weil der Artikelkörper verworfen wird.
"""

from dataclasses import dataclass

import spacy
from spacy.language import Language
from spacy.tokens import Span, Token

DEFAULT_MODEL = "de_core_news_lg"
ENTITY_LABELS = {"PER", "ORG", "LOC", "MISC"}
REQUIRED_COMPONENTS = {"parser", "ner", "lemmatizer"}
# Wortarten, mit denen eine Grundform beginnen darf. Alles davor (Artikel,
# Pronomen, Präpositionen, "noch mehr") wird abgeschnitten.
CONTENT_POS = {"NOUN", "PROPN", "ADJ", "NUM", "X"}
QUOTE_TABLE = str.maketrans("", "", "«»‹›\"„“”")

@dataclass(frozen=True)
class Candidate:
    phrase: str
    label: str
    count: int
    in_titel: bool
    in_lead: bool
    lemma: str = ""
    kopf: str | None = None


def load_model(model: str = DEFAULT_MODEL) -> Language:
    nlp = spacy.load(model)
    missing = REQUIRED_COMPONENTS - set(nlp.pipe_names)
    if missing:
        raise ValueError(f"Modellkomponenten fehlen: {', '.join(sorted(missing))}")
    return nlp


def is_noun(token: Token) -> bool:
    # Als NOUN getaggte Kleinwörter ("morgen", "ganz", "zurzeit") sind
    # Taggerfehler: deutsche Nomen beginnen gross. Namen dürfen klein
    # beginnen ("iPhone", "eBay").
    if token.pos_ == "PROPN":
        return True
    return token.pos_ == "NOUN" and token.text[:1].isupper()


def token_base(token: Token, keep_adjective: bool) -> str:
    lemma = token.lemma_.strip()
    if token.pos_ == "NOUN":
        # Der Lookup-Lemmatizer liefert für unbekannte Nomen Unsinn in
        # Kleinschreibung ("Bewohnerinnen" -> "bewohnerinnenr"). Deutsche
        # Nomen sind gross, also ist eine kleine Grundform ein Fehler.
        return lemma if lemma[:1].isupper() else token.text
    if token.pos_ == "PROPN":
        # Nur Flexionsendungen entfernen ("Bidens" -> "Biden"), nie den
        # Namen selbst umschreiben.
        return lemma if lemma and token.text.startswith(lemma) else token.text
    if token.pos_ == "ADJ" and not keep_adjective:
        return lemma or token.text
    return token.text


def normalize(span: Span, is_entity: bool) -> tuple[str, str | None] | None:
    tokens = list(span)
    while tokens and tokens[0].pos_ not in CONTENT_POS:
        tokens.pop(0)
    while tokens and tokens[-1].pos_ == "PUNCT":
        tokens.pop()
    # Ohne mindestens ein Nomen ist ein Kandidat kein Keyword: so fallen
    # Pronomen ("er", "sich"), "was", "mehr" und reine Adjektive weg.
    if not any(is_noun(token) for token in tokens):
        return None
    # In Namen bleiben Adjektive unverändert ("Weisses Haus", "Rotes Kreuz").
    # Anführungszeichen ("«Misstrauensvotum", "Rhino»-Räumung") gehören nicht
    # zur Grundform.
    parts = (
        token_base(t, keep_adjective=is_entity).translate(QUOTE_TABLE)
        for t in tokens
        if t.pos_ != "PUNCT"
    )
    lemma = " ".join(part for part in parts if part)
    if not lemma:
        return None
    kopf = None
    if not is_entity and is_noun(span.root):
        kopf = token_base(span.root, keep_adjective=False).translate(QUOTE_TABLE)
    return lemma, kopf or None


def extract_candidates(
    nlp: Language, *, titel: str, lead: str, body: str
) -> list[Candidate]:
    counts: dict[tuple[str, str], list] = {}
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
            normalized = normalize(span, is_entity=label != "NOUN_CHUNK")
            if normalized is None:
                continue
            entry = counts.setdefault(
                (span.text, label), [0, 0, 0, normalized[0], normalized[1]]
            )
            entry[0] += 1
            if field_index == 0:
                entry[1] = 1
            elif field_index == 1:
                entry[2] = 1
    return [
        Candidate(phrase, label, count, bool(in_titel), bool(in_lead), lemma, kopf)
        for (phrase, label), (count, in_titel, in_lead, lemma, kopf) in counts.items()
    ]
