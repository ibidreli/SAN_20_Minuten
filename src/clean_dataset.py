import os
import re
import json
import pandas as pd
import numpy as np

RAW_PATH = 'data/20min_metadaten_keywords.csv'
OUT_PARQUET = 'data/20min_cleaned_post2020.parquet'
DICT_PATH = 'data/data_dictionary.json'

CANONICAL_RESSORTS = {
    'Schweiz', 'Ausland', 'Sport', 'Panorama', 'Wirtschaft',
    'People', 'Regionen', 'Digital', 'Wissen', 'Lifestyle',
    'Community', 'Gesundheit', 'Coronavirus', 'Kino & Streaming',
    'Wetter'
}
# Anmerkung: '#WIRSINDZUKUNFT' ist eine Kampagnen-Rubrik, kein Ressort. Sie wird
# bewusst nach 'Andere' gemappt, damit die Ressort-Kanonik hier und in
# src/network_models.CANONICAL_RESSORTS uebereinstimmt. Zuvor war sie hier ein
# eigenes Ressort, im JSD-Vektor aber Teil von 'Andere' - ein stiller Bruch.

AGENCY_SET = {
    'sda', 'dpa', 'afp', 'reuters', 'keystone', 'sportinformation',
    'si', 'sid', 'apa', 'tages-anzeiger', 'awp', 'ap', 'ats',
    'tamedia', 'schweizerische depeschenagentur', 'deutsche presse-agentur'
}

PLACEHOLDER_SET = {
    'undefined undefined', 'redaktion', 'kein autor', 'autorenteam',
    'community', 'agenturen', 'video', 'news', 'admin', 'unbekannt',
    'anonym', '20 minuten', '20 min', 'null', 'none', 'author'
}

# Exact-string matching alone is not enough: the corpus contains compound
# bylines such as 'SDA fss', 'Rat Dpa', 'AFP her' (agency plus desk code) and
# spelled-out institution names. Without token-level filtering these enter the
# graph as if they were journalists. 'Agence France-Presse' alone carries 214
# articles and lands inside the largest clique, inflating every cohesion and
# centrality measure.
AGENCY_TOKENS = {
    # Nachrichtenagenturen und Agentur-Kuerzel
    'sda', 'dpa', 'afp', 'ap', 'ats', 'si', 'sid', 'apa', 'awp',
    'reuters', 'keystone', 'sportinformation', 'tamedia',
    # Redaktionen und Desks
    'newsdesk', 'newsdeks', 'newdesk', 'redaktion', 'sportredaktion',
    'ressort', 'verlag', 'buero', 'reporter', 'heute',
    # Content-Zulieferer und Verbaende, die als Byline auftreten
    'spot', 'spotonnews', 'sp-x', 'spx', 'storyful', 'getabstract',
    'picstars', 'agvs', 'transhelvetica', 'ampnet', 'obs', 'pd', 'spoton'
}

# Substrings that mark an institution rather than a person
# Vollstaendige Byline-Strings, die eine Institution bezeichnen. Notwendig fuer
# Formen, die die Tokenisierung nicht erfasst (z.B. 'sp-x').
AGENCY_EXACT = {
    'sp-x', 'spx', 'sp x', 'agvs-expertenteam', 'viva-mobilitaetsexperten',
    'viva-mobilitätsexperten', 'the associated press', 'associated press',
    'team news', 'newsdesk', 'newdesk', 'newsdeks'
}

# Teilstrings, die eindeutig institutionell sind. Bewusst KEINE kurzen
# Allerweltssilben wie 'verband' oder 'institut': die kaemen auch in echten
# Nachnamen vor und wuerden Personen faelschlich entfernen.
AGENCY_SUBSTRINGS = (
    'agence', 'presse-agentur', 'depeschenagentur', 'associated press',
    'nachrichtenagentur', 'newsdesk', 'newsdeks', 'redaktion',
    'experten', 'expertinnen', 'pressedienst', 'mediendienst', 'team news',
    'büro ', 'buero '
)


def _tokenize_byline(name):
    return {tok.strip('.,;:()') for tok in re.split(r'[\s\-/]+', name.lower().strip())
            if tok.strip('.,;:()')}


def _is_agency(name):
    """
    True when a byline denotes a news agency or an editorial desk.

    Checks the full string, then substrings, then individual tokens, so that
    compound forms like 'SDA fss' or 'Reuters SDA' are caught too.
    """
    low = name.lower().strip()
    if low in AGENCY_SET or low in AGENCY_EXACT:
        return True
    if any(s in low for s in AGENCY_SUBSTRINGS):
        return True
    return bool(_tokenize_byline(name) & AGENCY_TOKENS)


def _is_placeholder(name):
    """True for non-agency filler bylines such as 'Undefined Undefined'."""
    return name.lower().strip() in PLACEHOLDER_SET

def clean_author_field(raw_val):
    if pd.isna(raw_val) or not str(raw_val).strip():
        return [], False
    
    parts = [p.strip() for p in str(raw_val).split(';') if p.strip()]
    cleaned_authors = []
    has_agency = False
    
    for p in parts:
        if _is_agency(p):
            has_agency = True
            continue
        if _is_placeholder(p):
            continue
        if len(p) <= 3:
            continue
        # Preserve the byline casing from the source. Blanket capitalize() would
        # corrupt 1573 distinct names ('Patrick McEvily' -> 'Patrick Mcevily',
        # 'Michelle de Oliveira' -> 'Michelle De Oliveira', 'Jean-Claude' ->
        # 'Jean-claude'). Author strings are network node keys, so this matters.
        # Only ALL CAPS bylines (24 in the corpus) are normalised.
        if p.isupper():
            cleaned_name = ' '.join(
                '-'.join(s.capitalize() for s in w.split('-')) for w in p.split()
            )
        else:
            cleaned_name = ' '.join(p.split())
        cleaned_authors.append(cleaned_name)
        
    return cleaned_authors, has_agency

print('Starting data cleaning pipeline for 2020-2024...')
chunks = []
total_raw = 0
retained = 0

for chunk in pd.read_csv(RAW_PATH, chunksize=50000, low_memory=False):
    total_raw += len(chunk)
    
    # Parse date
    chunk['datum_dt'] = pd.to_datetime(chunk['datum'], errors='coerce', utc=True)
    
    # 1. Temporal filter: Complete years 2020 through 2024
    chunk = chunk[
        (chunk['datum_dt'] >= '2020-01-01') & 
        (chunk['datum_dt'] <= '2024-12-31 23:59:59')
    ].copy()
    
    if chunk.empty:
        continue
        
    # 2. Quality filters: Drop empty title or description
    chunk = chunk[chunk['titel'].notna() & chunk['beschreibung'].notna()].copy()
    chunk = chunk[(chunk['titel'].str.strip() != '') & (chunk['beschreibung'].str.strip() != '')]
    
    # 3. Canonical ressort mapping
    chunk['ressort_canonical'] = chunk['ressort'].apply(
        lambda x: str(x).strip() if str(x).strip() in CANONICAL_RESSORTS else 'Andere'
    )
    
    # 4. Entity resolution on authors
    author_tuples = chunk['autor'].apply(clean_author_field)
    chunk['authors_clean'] = [t[0] for t in author_tuples]
    chunk['has_agency'] = [t[1] for t in author_tuples]
    chunk['author_count'] = chunk['authors_clean'].apply(len)
    chunk['authors_str'] = chunk['authors_clean'].apply(lambda x: '; '.join(x) if x else 'Kein Autor')
    
    # 5. Clean terms parsing
    def parse_terms(x):
        if pd.isna(x) or not str(x).strip():
            return []
        return [t.strip().lower() for t in str(x).split(',') if len(t.strip()) > 1]
        
    chunk['clean_terms_list'] = chunk['clean_terms'].apply(parse_terms)
    
    # 6. Engagement & Comments numeric cleaning
    # Missing values stay missing. Filling with 0 would conflate 'interaction
    # disabled / not scraped' with 'zero likes'; 01_cleaning.qmd shows the
    # missingness is systematic (concentrated in 2020 and in certain keywords),
    # not random. Int64 is the nullable integer dtype.
    for col in ['likes', 'shares', 'kommentare']:
        chunk[col] = pd.to_numeric(chunk[col], errors='coerce').clip(lower=0).astype('Int64')
        
    # Fehlende Angaben bleiben fehlend, statt zu False zu werden. 'nicht erfasst'
    # ist nicht dasselbe wie 'Kommentare deaktiviert' (vgl. Lessons Learned 2).
    _ke_raw = chunk['kommentare_erlaubt']
    _ke_str = _ke_raw.astype(str).str.strip().str.lower()
    chunk['kommentare_erlaubt'] = pd.Series(
        np.where(_ke_str.isin(['true', '1', 'yes']), True,
                 np.where(_ke_str.isin(['false', '0', 'no']), False, None)),
        index=chunk.index, dtype='boolean'
    )
    
    # Select and rename clean columns
    keep_cols = [
        'url', 'datum_dt', 'titel', 'beschreibung', 'ressort_canonical',
        'authors_clean', 'authors_str', 'author_count', 'has_agency',
        'likes', 'shares', 'kommentare', 'kommentare_erlaubt',
        'clean_terms_list'
    ]
    cleaned_chunk = chunk[keep_cols].rename(columns={
        'datum_dt': 'datum',
        'ressort_canonical': 'ressort'
    })
    
    retained += len(cleaned_chunk)
    chunks.append(cleaned_chunk)
    print(f'Processed batch: {len(cleaned_chunk)} articles retained (Running total: {retained})')

clean_df = pd.concat(chunks, ignore_index=True)
clean_df['year'] = clean_df['datum'].dt.year.astype('int16')

# Sort chronologically. The default quicksort is not stable, so articles sharing
# a timestamp got different ids on every run and the parquet hash was not
# reproducible. Sorting on (datum, url) with a stable kind makes the order total.
clean_df = clean_df.sort_values(['datum', 'url'], kind='mergesort').reset_index(drop=True)
clean_df['article_id'] = clean_df.index + 1

# Export to parquet
clean_df.to_parquet(OUT_PARQUET, index=False, engine='pyarrow', compression='snappy')
print(f'Successfully exported {len(clean_df)} clean articles to {OUT_PARQUET}')

# Data Dictionary
data_dict = {
    'dataset_name': '20 Minuten Cleaned Corpus (2020-2024)',
    'row_count': len(clean_df),
    'date_range': [str(clean_df['datum'].min()), str(clean_df['datum'].max())],
    'multi_author_articles': int((clean_df['author_count'] > 1).sum()),
    'single_author_articles': int((clean_df['author_count'] == 1).sum()),
    'uncredited_or_agency_only': int((clean_df['author_count'] == 0).sum()),
    'columns': {
        'article_id': 'Unique sequential integer identifier',
        'url': 'Full canonical 20 Minuten article URL',
        'datum': 'UTC publication timestamp (ISO-8601 datetime)',
        'year': 'Publication year (2020-2024)',
        'titel': 'Article headline string',
        'beschreibung': 'Article lead paragraph summary',
        'ressort': 'Standardized canonical editorial department',
        'authors_clean': 'List of resolved human author strings (agencies and initials excluded)',
        'authors_str': 'Semicolon-separated string of human authors',
        'author_count': 'Number of human authors credited on the article',
        'has_agency': 'Boolean flag indicating whether a wire agency was credited',
        'likes': 'Integer count of user likes/reactions (snapshot)',
        'shares': 'Integer count of user article shares (snapshot)',
        'kommentare': 'Integer count of approved user comments (snapshot)',
        'kommentare_erlaubt': 'Boolean flag indicating whether comments were enabled',
        'clean_terms_list': 'List of lowercase lemmatized noun keywords extracted via spaCy'
    }
}

with open(DICT_PATH, 'w', encoding='utf-8') as f:
    json.dump(data_dict, f, indent=2)

print('Data dictionary saved to', DICT_PATH)
