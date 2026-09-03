"""
Module: src.network_models
Description: Reusable network construction engine for Social Network Analysis (SAN) of 20 Minuten.
Implements:
1. Two-Mode (Article-Author) bipartite modeling and Newman-weighted 1-Mode co-authorship projection.
2. Information-theoretic Jensen-Shannon Divergence (JSD) on author ressort probability distributions.
3. Longitudinal Semantic Keyword Networks with fixed global vocabulary and Mutual k-NN sparsification.
4. Rolling temporal train/test split generator for Link Prediction.
"""

import itertools
import numpy as np
import pandas as pd
import networkx as nx
from scipy.spatial.distance import jensenshannon
from collections import Counter, defaultdict
from scipy.sparse import lil_matrix, csr_matrix

CANONICAL_RESSORTS = [
    'Schweiz', 'Ausland', 'Sport', 'Panorama', 'Wirtschaft',
    'People', 'Regionen', 'Digital', 'Wissen', 'Lifestyle',
    'Community', 'Gesundheit', 'Coronavirus', 'Kino & Streaming',
    'Wetter', 'Andere'
]

# -------------------------------------------------------------------------
# 1. Author Collaboration & Two-Mode Modeling
# -------------------------------------------------------------------------

def build_bipartite_author_article(df):
    """
    Builds a Two-Mode Bipartite Network B = (U, V, E).
    Nodes U (bipartite=0): Human journalists.
    Nodes V (bipartite=1): Articles with attributes (year, ressort, likes, shares, comments).
    """
    B = nx.Graph()
    
    for _, row in df.iterrows():
        art_node = f"art_{row['article_id']}"
        authors = row['authors_clean']
        if len(authors) == 0:
            continue
            
        B.add_node(
            art_node,
            bipartite=1,
            article_id=row['article_id'],
            year=row['year'],
            ressort=row['ressort'],
            likes=row['likes'],
            shares=row['shares'],
            kommentare=row['kommentare'],
            kommentare_erlaubt=row['kommentare_erlaubt']
        )
        
        for author in authors:
            if not B.has_node(author):
                B.add_node(author, bipartite=0)
            B.add_edge(author, art_node)
            
    return B


def _to_float(value):
    """Converts a possibly-missing engagement value to float, with NA -> nan."""
    return np.nan if pd.isna(value) else float(value)


def _nanmean(values):
    """Mean ignoring NaN. Returns nan when every value is missing."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0 or np.all(np.isnan(arr)):
        return float('nan')
    return float(np.nanmean(arr))


def compute_author_ressort_profiles(df):
    """
    Computes for each author their total publication count, dominant ressort,
    and empirical probability vector over canonical ressorts.
    """
    ressort_idx = {r: i for i, r in enumerate(CANONICAL_RESSORTS)}
    author_counts = defaultdict(lambda: np.zeros(len(CANONICAL_RESSORTS), dtype=float))
    # Latest publication date per (author, ressort), used to break ties for dominant_ressort
    author_ressort_latest = defaultdict(
        lambda: [pd.Timestamp.min.tz_localize('UTC')] * len(CANONICAL_RESSORTS)
    )
    author_metrics = defaultdict(lambda: {'likes': [], 'shares': [], 'comments': []})
    
    for _, row in df.iterrows():
        authors = row['authors_clean']
        res = row['ressort']
        res_i = ressort_idx.get(res, ressort_idx['Andere'])
        dt = row['datum']
        
        for a in authors:
            author_counts[a][res_i] += 1
            if dt > author_ressort_latest[a][res_i]:
                author_ressort_latest[a][res_i] = dt
            # likes/shares/kommentare are nullable (missing != 0), so they are
            # collected as float NaN and aggregated with nanmean below.
            author_metrics[a]['likes'].append(_to_float(row['likes']))
            author_metrics[a]['shares'].append(_to_float(row['shares']))
            author_metrics[a]['comments'].append(_to_float(row['kommentare']))
            
    profiles = {}
    for a, counts in author_counts.items():
        total_arts = counts.sum()
        prob_vec = counts / total_arts
        
        # Dominant ressort. Ties are broken by the most recent publication in the
        # tied ressort; if those are equal too, by canonical order (fully deterministic).
        max_c = counts.max()
        best_indices = [i for i, c in enumerate(counts) if c == max_c]
        if len(best_indices) == 1:
            dominant_res = CANONICAL_RESSORTS[best_indices[0]]
        else:
            latest = author_ressort_latest[a]
            best_i = max(best_indices, key=lambda i: (latest[i], -i))
            dominant_res = CANONICAL_RESSORTS[best_i]
        
        profiles[a] = {
            'article_count': int(total_arts),
            'dominant_ressort': dominant_res,
            'ressort_counts': counts.copy(),
            'ressort_distribution': prob_vec,
            'mean_likes': _nanmean(author_metrics[a]['likes']),
            'mean_shares': _nanmean(author_metrics[a]['shares']),
            'mean_comments': _nanmean(author_metrics[a]['comments'])
        }
        
    return profiles


def leave_one_out_profile(profile, ressort):
    """
    Returns the author's ressort probability vector with one article of the given
    ressort removed, or None if that article was the author's only one.

    Required so that the JSD attached to article k is not computed from profiles
    that already contain article k.
    """
    idx = CANONICAL_RESSORTS.index(ressort) if ressort in CANONICAL_RESSORTS \
        else CANONICAL_RESSORTS.index('Andere')
    counts = profile['ressort_counts'].copy()
    counts[idx] -= 1.0
    total = counts.sum()
    if total <= 0:
        return None
    return counts / total


def compute_leave_one_out_jsd(df, profiles):
    """
    For every multi-author article k, the mean pairwise Jensen-Shannon divergence
    between its co-authors' ressort profiles with article k itself removed.

    Returns {article_id: mean_jsd}. Articles where any co-author has no remaining
    article after removal are omitted, since their profile is undefined.
    """
    result = {}
    multi_df = df[df['author_count'] > 1]

    for _, row in multi_df.iterrows():
        auths = [a for a in row['authors_clean'] if a in profiles]
        if len(auths) < 2:
            continue

        loo_vectors = {}
        for a in auths:
            vec = leave_one_out_profile(profiles[a], row['ressort'])
            if vec is None:
                loo_vectors = None
                break
            loo_vectors[a] = vec
        if loo_vectors is None:
            continue

        pairwise = [
            compute_jsd(loo_vectors[u], loo_vectors[v])
            for u, v in itertools.combinations(auths, 2)
        ]
        result[row['article_id']] = float(np.mean(pairwise))

    return result


def compute_jsd(p, q):
    """
    Computes base-2 Jensen-Shannon Divergence JSD(p || q) in [0, 1].
    """
    return float(jensenshannon(p, q, base=2) ** 2)


def project_author_collaboration(df, min_articles=2):
    """
    Projects the multi-author articles directly to a weighted One-Mode author collaboration graph
    using Newman's collaboration weighting:
        w_ij = sum_{k in V_ij} 1 / (|U_k| - 1)
    Nodes are assigned author profiles (dominant ressort, JSD divergence, metrics).
    """
    profiles = compute_author_ressort_profiles(df)
    multi_df = df[df['author_count'] > 1]
    
    G = nx.Graph()
    edge_weights = defaultdict(float)
    edge_articles = defaultdict(list)
    
    for _, row in multi_df.iterrows():
        authors = row['authors_clean']
        m = len(authors)
        increment = 1.0 / (m - 1)
        art_id = row['article_id']
        
        for u, v in itertools.combinations(sorted(authors), 2):
            edge_weights[(u, v)] += increment
            edge_articles[(u, v)].append(art_id)
            
    # Add nodes with profiles
    for a, p in profiles.items():
        if p['article_count'] >= min_articles:
            G.add_node(
                a,
                article_count=p['article_count'],
                dominant_ressort=p['dominant_ressort'],
                ressort_distribution=p['ressort_distribution'],
                mean_likes=p['mean_likes'],
                mean_shares=p['mean_shares'],
                mean_comments=p['mean_comments']
            )
            
    # Add edges
    for (u, v), w in edge_weights.items():
        if G.has_node(u) and G.has_node(v):
            p_u = G.nodes[u]['ressort_distribution']
            p_v = G.nodes[v]['ressort_distribution']
            jsd_val = compute_jsd(p_u, p_v)
            G.add_edge(
                u, v,
                weight=round(w, 4),
                article_count=len(edge_articles[(u, v)]),
                jsd=round(jsd_val, 4)
            )
            
    return G


# -------------------------------------------------------------------------
# 2. Longitudinal Keyword Networks with Mutual k-NN
# -------------------------------------------------------------------------

def extract_global_vocabulary(df, top_n=1200):
    """
    Identifies the top_n most frequent lemmatized nouns across 2020-2024.
    Filters out media boilerplate words.
    """
    BOILERPLATE = {
        'bild', 'fotos', 'video', 'story', 'minuten', 'leser', 'update',
        'artikel', 'jahr', 'jahre', 'prozent', 'montag', 'dienstag',
        'mittwoch', 'donnerstag', 'freitag', 'samstag', 'sonntag'
    }
    
    term_counter = Counter()
    for terms in df['clean_terms_list']:
        filtered = [t for t in terms if len(t) > 2 and t not in BOILERPLATE]
        term_counter.update(filtered)
        
    global_vocab = [term for term, _ in term_counter.most_common(top_n)]
    return sorted(global_vocab)


def build_annual_keyword_graph(df_year, vocab, k=10):
    """
    Builds a keyword co-occurrence network for a specific year using:
    1. Fixed global vocabulary.
    2. Salton Cosine Association weights.
    3. Mutual k-NN sparsification.
    4. Distance conversion d = 1 / weight for shortest paths.
    """
    vocab_idx = {term: i for i, term in enumerate(vocab)}
    N = len(vocab)
    
    # Sparse occurrence matrix
    row_indices = []
    col_indices = []
    
    for doc_id, terms in enumerate(df_year['clean_terms_list']):
        for t in set(terms):
            if t in vocab_idx:
                row_indices.append(doc_id)
                col_indices.append(vocab_idx[t])
                
    if not row_indices:
        return nx.Graph()
        
    data = np.ones(len(row_indices), dtype=float)
    X = csr_matrix((data, (row_indices, col_indices)), shape=(len(df_year), N))
    
    # Co-occurrence C = X.T @ X
    C = (X.T @ X).toarray()
    doc_freqs = np.diag(C).copy()
    
    # Salton Cosine association: C_ij / sqrt(df_i * df_j)
    outer_df = np.sqrt(np.outer(doc_freqs, doc_freqs))
    np.fill_diagonal(outer_df, 1.0)
    outer_df[outer_df == 0] = 1.0
    
    S = C / outer_df
    np.fill_diagonal(S, 0.0)  # No self-loops
    
    # Mutual k-NN sparsification
    # top-k neighbors for each node
    topk_masks = np.zeros((N, N), dtype=bool)
    for i in range(N):
        if doc_freqs[i] > 0:
            top_k_indices = np.argsort(S[i, :])[-k:]
            # Only keep non-zero weights
            top_k_indices = [idx for idx in top_k_indices if S[i, idx] > 0]
            topk_masks[i, top_k_indices] = True
            
    # Mutual: edge exists iff both u in topk(v) and v in topk(u)
    mutual_mask = topk_masks & topk_masks.T
    
    G = nx.Graph()
    for i in range(N):
        G.add_node(vocab[i], doc_freq=int(doc_freqs[i]))
        
    for i in range(N):
        for j in range(i + 1, N):
            if mutual_mask[i, j]:
                w = float(S[i, j])
                G.add_edge(
                    vocab[i], vocab[j],
                    weight=round(w, 5),
                    distance=round(1.0 / max(w, 1e-6), 4)
                )
                
    return G


# -------------------------------------------------------------------------
# 3. Rolling Temporal Link Prediction Split Generator
# -------------------------------------------------------------------------

def create_rolling_link_prediction_windows(df):
    """
    Generates three realistic rolling temporal windows:
    Window 1: Train 2020-2021 -> Test 2022
    Window 2: Train 2020-2022 -> Test 2023
    Window 3: Train 2020-2023 -> Test 2024
    
    For each window:
    - G_train: Active collaboration network from training years (authors with >= 2 articles).
    - candidate_nodes: Authors active in training (>=2 articles) AND active in test year (>=1 article).
    - E_pos: Genuinely new edges formed in test year among candidate nodes.
    - E_neg: All remaining unconnected candidate pairs (unbalanced ground truth).
    """
    windows_def = [
        {'train_years': [2020, 2021], 'test_year': 2022, 'label': '2020-21 -> 2022'},
        {'train_years': [2020, 2021, 2022], 'test_year': 2023, 'label': '2020-22 -> 2023'},
        {'train_years': [2020, 2021, 2022, 2023], 'test_year': 2024, 'label': '2020-23 -> 2024'}
    ]
    
    eval_splits = []
    
    for w in windows_def:
        train_df = df[df['year'].isin(w['train_years'])]
        test_df = df[df['year'] == w['test_year']]
        
        G_train = project_author_collaboration(train_df, min_articles=2)
        G_test = project_author_collaboration(test_df, min_articles=1)
        
        train_nodes = set(G_train.nodes())
        test_nodes = set(G_test.nodes())
        candidate_nodes = sorted(list(train_nodes & test_nodes))
        
        # Test edges that did NOT exist in G_train
        new_edges = set()
        for u, v in G_test.edges():
            if u in candidate_nodes and v in candidate_nodes:
                if not G_train.has_edge(u, v):
                    new_edges.add(tuple(sorted([u, v])))
                    
        # All eligible unconnected pairs
        all_candidate_pairs = set(itertools.combinations(candidate_nodes, 2))
        # G_train.edges() yields tuples in node-insertion order, whereas
        # all_candidate_pairs comes from combinations(sorted(...)). Without
        # normalising, reversed tuples never match and real training edges
        # survive the set difference as false negatives.
        train_existing_edges = {tuple(sorted(e)) for e in G_train.edges()}
        eligible_non_edges = all_candidate_pairs - train_existing_edges
        
        neg_edges = eligible_non_edges - new_edges
        
        eval_splits.append({
            'label': w['label'],
            'train_years': w['train_years'],
            'test_year': w['test_year'],
            'G_train': G_train,
            'candidate_nodes': candidate_nodes,
            'positive_edges': list(new_edges),
            'negative_edges': list(neg_edges)
        })
        
    return eval_splits


# -------------------------------------------------------------------------
# 3b. Graph Export
# -------------------------------------------------------------------------

def export_graph_gexf(G, path):
    """
    Writes G to a GEXF file for Gephi.

    GEXF only accepts scalar attribute values, so numpy arrays (such as the
    ressort_distribution probability vector) and numpy scalar types have to be
    converted first. Arrays are serialised as comma-separated strings and the
    original graph is left untouched.
    """
    def _coerce(value):
        if isinstance(value, np.ndarray):
            return ','.join(f'{x:.6f}' for x in value.ravel())
        if isinstance(value, (list, tuple)):
            return ','.join(str(x) for x in value)
        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, pd.Timestamp):
            return value.isoformat()
        return value

    H = nx.Graph() if not G.is_directed() else nx.DiGraph()
    H.graph.update({k: _coerce(v) for k, v in G.graph.items()})
    for n, data in G.nodes(data=True):
        H.add_node(n, **{k: _coerce(v) for k, v in data.items()})
    for u, v, data in G.edges(data=True):
        H.add_edge(u, v, **{k: _coerce(v_) for k, v_ in data.items()})

    nx.write_gexf(H, path)
    return path


# -------------------------------------------------------------------------
# 4. Unit Tests on Small Synthetic Graphs
# -------------------------------------------------------------------------

def run_synthetic_unit_tests():
    """
    Unit tests on small toy graphs verifying:
    1. Newman weight formula.
    2. JSD mathematical bounds [0, 1] and identity.
    3. Mutual k-NN symmetry and non-negative distance.
    """
    print('Running synthetic unit tests...')
    
    # 1. JSD Tests
    p = np.array([1.0, 0.0, 0.0])
    q = np.array([0.0, 1.0, 0.0])
    p_same = np.array([1.0, 0.0, 0.0])
    
    assert compute_jsd(p, p_same) == 0.0, 'JSD of identical vectors must be 0'
    assert abs(compute_jsd(p, q) - 1.0) < 1e-6, 'JSD of disjoint vectors must be 1.0'
    print('  [PASS] JSD identity and bound tests passed.')
    
    # 2. Newman Collaboration Weight Test
    # Article 1 has 2 authors: u, v -> increment = 1 / (2 - 1) = 1.0
    # Article 2 has 3 authors: u, v, w -> increment for u,v = 1 / (3 - 1) = 0.5
    # Total w(u, v) should be 1.5
    toy_df = pd.DataFrame([
        {
            'article_id': 1,
            'authors_clean': ['Alice', 'Bob'],
            'author_count': 2,
            'year': 2020,
            'ressort': 'Schweiz',
            'datum': pd.Timestamp('2020-01-01', tz='UTC'),
            'likes': 10, 'shares': 5, 'kommentare': 2
        },
        {
            'article_id': 2,
            'authors_clean': ['Alice', 'Bob', 'Charlie'],
            'author_count': 3,
            'year': 2020,
            'ressort': 'Sport',
            'datum': pd.Timestamp('2020-01-02', tz='UTC'),
            'likes': 20, 'shares': 10, 'kommentare': 4
        }
    ])
    
    G_toy = project_author_collaboration(toy_df, min_articles=1)
    assert abs(G_toy['Alice']['Bob']['weight'] - 1.5) < 1e-4, 'Newman weight must equal 1.5'
    assert abs(G_toy['Alice']['Charlie']['weight'] - 0.5) < 1e-4, 'Newman weight must equal 0.5'
    print('  [PASS] Newman collaboration weight test passed.')
    
    # 3. Mutual k-NN Symmetry Test
    toy_vocab = ['apple', 'banana', 'orange']
    toy_art_df = pd.DataFrame([
        {'clean_terms_list': ['apple', 'banana']},
        {'clean_terms_list': ['apple', 'banana', 'orange']},
        {'clean_terms_list': ['banana', 'orange']}
    ])
    G_knn = build_annual_keyword_graph(toy_art_df, toy_vocab, k=1)
    for u, v in G_knn.edges():
        assert G_knn.has_edge(v, u), 'Mutual k-NN must be symmetric'
        assert G_knn[u][v]['distance'] > 0, 'Distance must be positive'
    print('  [PASS] Mutual k-NN graph invariants passed.')

    # 4. Regression: training edges must never appear in the negative set.
    # G.edges() returns tuples in insertion order, so an unsorted set difference
    # silently leaves real edges in the negatives.
    G_leak = nx.Graph()
    G_leak.add_edge('Zoe', 'Adam')      # inserted as ('Zoe', 'Adam'), i.e. reversed
    G_leak.add_edge('Adam', 'Mia')
    nodes_leak = sorted(G_leak.nodes())
    all_pairs_leak = set(itertools.combinations(nodes_leak, 2))
    normalised = {tuple(sorted(e)) for e in G_leak.edges()}
    non_edges = all_pairs_leak - normalised
    for u, v in G_leak.edges():
        assert tuple(sorted([u, v])) not in non_edges, \
            'Training edge leaked into the negative set'
    assert len(non_edges) == len(all_pairs_leak) - G_leak.number_of_edges(), \
        'Negative set has the wrong cardinality'
    print('  [PASS] Link-prediction negative set excludes all training edges.')

    # 5. Dominant-ressort tie-break must follow the most recent publication date,
    # not the position in CANONICAL_RESSORTS.
    tie_df = pd.DataFrame([
        {
            'article_id': 1, 'authors_clean': ['Tie Breaker'], 'author_count': 1,
            'year': 2020, 'ressort': CANONICAL_RESSORTS[0],
            'datum': pd.Timestamp('2020-01-01', tz='UTC'),
            'likes': 0, 'shares': 0, 'kommentare': 0
        },
        {
            'article_id': 2, 'authors_clean': ['Tie Breaker'], 'author_count': 1,
            'year': 2021, 'ressort': CANONICAL_RESSORTS[1],
            'datum': pd.Timestamp('2021-06-01', tz='UTC'),
            'likes': 0, 'shares': 0, 'kommentare': 0
        }
    ])
    tie_profiles = compute_author_ressort_profiles(tie_df)
    assert tie_profiles['Tie Breaker']['dominant_ressort'] == CANONICAL_RESSORTS[1], \
        'Tie must be broken by most recent publication, not by canonical order'
    print('  [PASS] Dominant-ressort tie-break uses the most recent publication.')

    # 6. GEXF export must survive numpy node attributes (ressort_distribution).
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        gexf_path = os.path.join(tmpdir, 'toy.gexf')
        export_graph_gexf(G_toy, gexf_path)
        G_back = nx.read_gexf(gexf_path)
        assert G_back.number_of_nodes() == G_toy.number_of_nodes(), 'GEXF lost nodes'
        assert G_back.number_of_edges() == G_toy.number_of_edges(), 'GEXF lost edges'
        assert 'ressort_distribution' in G_back.nodes['Alice'], \
            'GEXF export dropped ressort_distribution'
    print('  [PASS] GEXF export handles numpy attributes.')

    # 7. Leave-one-out JSD must exclude the article it is attached to.
    loo_df = pd.DataFrame([
        {
            'article_id': 1, 'authors_clean': ['Ann', 'Ben'], 'author_count': 2,
            'year': 2020, 'ressort': 'Sport',
            'datum': pd.Timestamp('2020-01-01', tz='UTC'),
            'likes': 0, 'shares': 0, 'kommentare': 0
        },
        {
            'article_id': 2, 'authors_clean': ['Ann'], 'author_count': 1,
            'year': 2020, 'ressort': 'Schweiz',
            'datum': pd.Timestamp('2020-02-01', tz='UTC'),
            'likes': 0, 'shares': 0, 'kommentare': 0
        },
        {
            'article_id': 3, 'authors_clean': ['Ben'], 'author_count': 1,
            'year': 2020, 'ressort': 'Wirtschaft',
            'datum': pd.Timestamp('2020-03-01', tz='UTC'),
            'likes': 0, 'shares': 0, 'kommentare': 0
        }
    ])
    loo_profiles = compute_author_ressort_profiles(loo_df)
    # Naive (leaky) JSD: both profiles contain the shared Sport article
    naive = compute_jsd(loo_profiles['Ann']['ressort_distribution'],
                        loo_profiles['Ben']['ressort_distribution'])
    loo = compute_leave_one_out_jsd(loo_df, loo_profiles)
    # With article 1 removed, Ann is purely Schweiz and Ben purely Wirtschaft -> JSD = 1
    assert abs(loo[1] - 1.0) < 1e-6, f'Leave-one-out JSD must be 1.0, got {loo[1]}'
    assert loo[1] > naive, 'Leave-one-out JSD must differ from the leaky variant'
    assert leave_one_out_profile(loo_profiles['Ann'], 'Sport') is not None
    # An author with a single article has no defined leave-one-out profile
    single = compute_author_ressort_profiles(loo_df[loo_df['article_id'] == 3])
    assert leave_one_out_profile(single['Ben'], 'Wirtschaft') is None, \
        'Single-article author must yield no leave-one-out profile'
    print('  [PASS] Leave-one-out JSD excludes the focal article.')

    print('All unit tests passed successfully!')

if __name__ == '__main__':
    run_synthetic_unit_tests()
