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


def compute_author_ressort_profiles(df):
    """
    Computes for each author their total publication count, dominant ressort,
    and empirical probability vector over canonical ressorts.
    """
    ressort_idx = {r: i for i, r in enumerate(CANONICAL_RESSORTS)}
    author_counts = defaultdict(lambda: np.zeros(len(CANONICAL_RESSORTS), dtype=float))
    author_latest_date = defaultdict(lambda: pd.Timestamp.min.tz_localize('UTC'))
    author_metrics = defaultdict(lambda: {'likes': [], 'shares': [], 'comments': []})
    
    for _, row in df.iterrows():
        authors = row['authors_clean']
        res = row['ressort']
        res_i = ressort_idx.get(res, ressort_idx['Andere'])
        dt = row['datum']
        
        for a in authors:
            author_counts[a][res_i] += 1
            if dt > author_latest_date[a]:
                author_latest_date[a] = dt
            author_metrics[a]['likes'].append(row['likes'])
            author_metrics[a]['shares'].append(row['shares'])
            author_metrics[a]['comments'].append(row['kommentare'])
            
    profiles = {}
    for a, counts in author_counts.items():
        total_arts = counts.sum()
        prob_vec = counts / total_arts
        
        # Dominant ressort with deterministic tie-breaking
        max_c = counts.max()
        best_indices = [i for i, c in enumerate(counts) if c == max_c]
        dominant_res = CANONICAL_RESSORTS[best_indices[0]]
        
        profiles[a] = {
            'article_count': int(total_arts),
            'dominant_ressort': dominant_res,
            'ressort_distribution': prob_vec,
            'mean_likes': float(np.mean(author_metrics[a]['likes'])),
            'mean_shares': float(np.mean(author_metrics[a]['shares'])),
            'mean_comments': float(np.mean(author_metrics[a]['comments']))
        }
        
    return profiles


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
        train_existing_edges = set(G_train.edges())
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
    print('All unit tests passed successfully!')

if __name__ == '__main__':
    run_synthetic_unit_tests()
