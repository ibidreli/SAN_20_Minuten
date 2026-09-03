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
import os
import tempfile
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
# 3a. QAP: Dyadic Hypothesis Testing on Edge Matrices (LE7)
# -------------------------------------------------------------------------

def edge_matrix_from_edge_attribute(G, nodes, attribute, default=0.0):
    """
    Dense symmetric matrix of an edge attribute over the given node order.
    Non-adjacent pairs receive `default`.
    """
    idx = {n: i for i, n in enumerate(nodes)}
    M = np.full((len(nodes), len(nodes)), float(default))
    for u, v, data in G.edges(data=True):
        if u in idx and v in idx:
            i, j = idx[u], idx[v]
            val = float(data.get(attribute, default))
            M[i, j] = val
            M[j, i] = val
    np.fill_diagonal(M, 0.0)
    return M


def edge_matrix_from_node_attribute(G, nodes, attribute, same_value=1.0, diff_value=0.0):
    """
    Projects a categorical NODE attribute onto a dyadic matrix: entry (i, j) is
    `same_value` when i and j share the attribute and `diff_value` otherwise.

    This is the "Knotenattribute als Kanten abbilden" strategy from LE7, which
    turns a monadic attribute into something a dyadic QAP test can consume
    (mixed monadic-dyadic hypothesis test).
    """
    labels = [G.nodes[n].get(attribute) for n in nodes]
    n = len(nodes)
    M = np.full((n, n), float(diff_value))
    for i in range(n):
        for j in range(i + 1, n):
            if labels[i] is not None and labels[i] == labels[j]:
                M[i, j] = M[j, i] = float(same_value)
    np.fill_diagonal(M, 0.0)
    return M


def jsd_matrix_from_profiles(G, nodes, attribute='ressort_distribution'):
    """
    Full pairwise JSD matrix over ALL dyads, not only adjacent ones.

    Necessary for QAP: an edge-attribute matrix is zero for non-adjacent pairs,
    so correlating it against another edge-attribute matrix partly measures
    mere co-presence of edges rather than the substantive relationship. The
    ressort profile exists for every author, so the divergence is defined for
    every pair.
    """
    profiles = [np.asarray(G.nodes[n][attribute], dtype=float) for n in nodes]
    n = len(nodes)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            M[i, j] = M[j, i] = compute_jsd(profiles[i], profiles[j])
    return M


def _upper_triangle(M):
    """Off-diagonal upper triangle as a flat vector (undirected: no double counting)."""
    iu = np.triu_indices_from(M, k=1)
    return M[iu]


def qap_correlation_test(matrix_a, matrix_b, n_perm=5000, seed=42, alternative='greater'):
    """
    Quadratic Assignment Procedure (QAP) for the correlation of two dyadic
    matrices over the same node set.

    The null distribution comes from permuting node labels JOINTLY on rows and
    columns of matrix_a. That joint permutation is what makes this QAP rather
    than a plain element-wise shuffle: it preserves the internal dependency
    structure of the network (a cell is not independent of the other cells in
    its row and column), which is exactly the assumption an ordinary
    correlation test violates on network data.

    Returns a dict with the observed Pearson r, the empirical p-value, and the
    mean and standard deviation of the null distribution.
    """
    A = np.asarray(matrix_a, dtype=float)
    B = np.asarray(matrix_b, dtype=float)
    if A.shape != B.shape or A.shape[0] != A.shape[1]:
        raise ValueError('Both matrices must be square and of equal shape')

    b_vec = _upper_triangle(B)

    def _corr(a_vec):
        if np.std(a_vec) == 0 or np.std(b_vec) == 0:
            return 0.0
        return float(np.corrcoef(a_vec, b_vec)[0, 1])

    r_obs = _corr(_upper_triangle(A))

    rng = np.random.default_rng(seed)
    n = A.shape[0]
    perm_r = np.zeros(n_perm)
    for b in range(n_perm):
        order = rng.permutation(n)
        # Joint row/column permutation: A[order][:, order]
        perm_r[b] = _corr(_upper_triangle(A[np.ix_(order, order)]))

    if alternative == 'greater':
        p_val = (np.sum(perm_r >= r_obs) + 1) / (n_perm + 1)
    elif alternative == 'less':
        p_val = (np.sum(perm_r <= r_obs) + 1) / (n_perm + 1)
    else:
        p_val = (np.sum(np.abs(perm_r) >= abs(r_obs)) + 1) / (n_perm + 1)

    return {
        'r_observed': r_obs,
        'p_value': float(p_val),
        'n_perm': n_perm,
        'null_mean': float(perm_r.mean()),
        'null_std': float(perm_r.std()),
        'null_distribution': perm_r,
        'alternative': alternative
    }


# -------------------------------------------------------------------------
# 3c. Cohesion & Connectivity (LE4 / LE6, Skript Kap. 5.2 und 9)
# -------------------------------------------------------------------------

def analyze_cohesion_and_connectivity(G, top_k=10):
    """
    Cohesive subgroup structure and structural robustness of G.

    Cliques and k-cores describe how tightly knit the collaboration core is;
    articulation points and bridges describe how fragile it is. Connectivity
    measures are computed on the giant component, since they are undefined for
    a disconnected graph.
    """
    components = sorted(nx.connected_components(G), key=len, reverse=True)
    gcc_nodes = components[0] if components else set()
    GCC = G.subgraph(gcc_nodes).copy()

    maximal_cliques = list(nx.find_cliques(GCC))
    clique_sizes = [len(c) for c in maximal_cliques]
    largest_clique = max(maximal_cliques, key=len) if maximal_cliques else []

    core_numbers = nx.core_number(GCC)
    max_core = max(core_numbers.values()) if core_numbers else 0
    main_core = [n for n, c in core_numbers.items() if c == max_core]

    articulation = sorted(nx.articulation_points(GCC))
    bridges = list(nx.bridges(GCC))

    # Rank cut vertices by how much damage their removal does
    cut_impact = []
    for node in articulation:
        H = GCC.copy()
        H.remove_node(node)
        parts = sorted(nx.connected_components(H), key=len, reverse=True)
        cut_impact.append({
            'node': node,
            'ressort': GCC.nodes[node].get('dominant_ressort'),
            'degree': GCC.degree(node),
            'components_after_removal': len(parts),
            'largest_fragment': len(parts[0]) if parts else 0,
            'nodes_split_off': len(GCC) - 1 - (len(parts[0]) if parts else 0)
        })
    cut_impact.sort(key=lambda d: d['nodes_split_off'], reverse=True)

    return {
        'n_components': len(components),
        'component_sizes': [len(c) for c in components],
        'n_isolates': sum(1 for c in components if len(c) == 1),
        'gcc_nodes': GCC.number_of_nodes(),
        'gcc_edges': GCC.number_of_edges(),
        'gcc_share': GCC.number_of_nodes() / G.number_of_nodes() if G.number_of_nodes() else 0.0,
        'n_maximal_cliques': len(maximal_cliques),
        'clique_number': max(clique_sizes) if clique_sizes else 0,
        'clique_size_distribution': dict(Counter(clique_sizes)),
        'largest_clique_members': sorted(largest_clique),
        'max_core_number': max_core,
        'main_core_size': len(main_core),
        'main_core_members': sorted(main_core),
        'core_numbers': core_numbers,
        'n_articulation_points': len(articulation),
        'n_bridges': len(bridges),
        'node_connectivity': nx.node_connectivity(GCC) if GCC.number_of_nodes() > 1 else 0,
        'edge_connectivity': nx.edge_connectivity(GCC) if GCC.number_of_nodes() > 1 else 0,
        'top_cut_vertices': cut_impact[:top_k],
        'bridges': bridges
    }


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
# 3d. Network Rendering
# -------------------------------------------------------------------------

def draw_network(G, path, color_by=None, size_by=None, title='', highlight_nodes=None,
                 label_top_n=0, label_nodes=None, seed=42, figsize=(13, 10), cmap_name='tab20',
                 edge_alpha=0.15, node_size_range=(15, 700), legend_title=None):
    """
    Renders G to a PNG with a seeded spring layout.

    color_by  -- categorical node attribute driving colour, or None for uniform
    size_by   -- dict {node: value} driving node area, or None for uniform
    highlight_nodes -- iterable drawn with a red outline (e.g. articulation points)
    label_top_n -- label the n largest nodes by `size_by`
    label_nodes -- explicit iterable of nodes to label, overrides label_top_n

    The layout seed is fixed so the same graph always renders identically.
    """
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D

    pos = nx.spring_layout(G, seed=seed, k=1.6 / np.sqrt(max(G.number_of_nodes(), 1)),
                           iterations=120, weight='weight')

    if size_by:
        vals = np.array([float(size_by.get(n, 0.0)) for n in G.nodes()])
        lo, hi = vals.min(), vals.max()
        norm = (vals - lo) / (hi - lo) if hi > lo else np.zeros_like(vals)
        sizes = node_size_range[0] + norm * (node_size_range[1] - node_size_range[0])
    else:
        sizes = np.full(G.number_of_nodes(), 60.0)

    if color_by:
        cats = [G.nodes[n].get(color_by, 'Andere') for n in G.nodes()]
        uniques = sorted(set(cats), key=str)
        cmap = plt.get_cmap(cmap_name)
        cmap_lookup = {c: cmap(i % cmap.N) for i, c in enumerate(uniques)}
        colors = [cmap_lookup[c] for c in cats]
    else:
        colors = '#4878A8'
        uniques, cmap_lookup = [], {}

    fig, ax = plt.subplots(figsize=figsize)
    nx.draw_networkx_edges(G, pos, ax=ax, alpha=edge_alpha, width=0.6, edge_color='#666666')
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=sizes, node_color=colors,
                           linewidths=0.4, edgecolors='white')

    if highlight_nodes:
        hl = [n for n in highlight_nodes if n in G]
        if hl:
            hl_sizes = [sizes[list(G.nodes()).index(n)] for n in hl]
            nx.draw_networkx_nodes(G, pos, nodelist=hl, ax=ax, node_size=hl_sizes,
                                   node_color='none', linewidths=1.6, edgecolors='crimson')

    if label_nodes:
        top = [n for n in label_nodes if n in G]
    elif label_top_n and size_by:
        top = [n for n, _ in sorted(size_by.items(), key=lambda x: x[1], reverse=True)
               if n in G][:label_top_n]
    else:
        top = []
    if top:
        # Offset labels above their node and give them a white halo, otherwise
        # they collide with each other in the dense centre of the layout.
        span_y = (max(p[1] for p in pos.values()) - min(p[1] for p in pos.values())) or 1.0
        for rank, n in enumerate(top):
            x, y = pos[n]
            # Alternate the offset direction so neighbouring labels separate
            dy = span_y * (0.035 if rank % 2 == 0 else -0.035)
            ax.annotate(
                n, xy=(x, y), xytext=(x, y + dy), ha='center',
                va='bottom' if dy > 0 else 'top',
                fontsize=8, fontweight='bold', zorder=5,
                bbox=dict(boxstyle='round,pad=0.22', facecolor='white',
                          edgecolor='#999999', alpha=0.85, linewidth=0.5),
                arrowprops=dict(arrowstyle='-', color='#999999', linewidth=0.6,
                                shrinkA=0, shrinkB=2)
            )

    handles = []
    if uniques:
        handles += [Line2D([0], [0], marker='o', color='w', label=str(c),
                           markerfacecolor=cmap_lookup[c], markersize=9)
                    for c in uniques]
    if highlight_nodes:
        handles.append(Line2D([0], [0], marker='o', color='w', label='Artikulationspunkt',
                              markerfacecolor='none', markeredgecolor='crimson',
                              markeredgewidth=1.6, markersize=9))
    if handles:
        ax.legend(handles=handles, title=legend_title or color_by, loc='upper left',
                  bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False)

    ax.set_title(title, fontsize=13)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(path, dpi=300, bbox_inches='tight')
    plt.close(fig)
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

    # 8. QAP must find no association between independent matrices and a
    # perfect one between a matrix and itself.
    rng_t = np.random.default_rng(7)
    n_q = 25
    A_rand = rng_t.random((n_q, n_q)); A_rand = (A_rand + A_rand.T) / 2
    np.fill_diagonal(A_rand, 0.0)
    B_rand = rng_t.random((n_q, n_q)); B_rand = (B_rand + B_rand.T) / 2
    np.fill_diagonal(B_rand, 0.0)

    qap_indep = qap_correlation_test(A_rand, B_rand, n_perm=500, seed=1)
    assert qap_indep['p_value'] > 0.05, \
        f"QAP must not find structure in independent matrices (p={qap_indep['p_value']})"
    qap_self = qap_correlation_test(A_rand, A_rand, n_perm=500, seed=1)
    assert abs(qap_self['r_observed'] - 1.0) < 1e-9, 'QAP self-correlation must be r = 1'
    assert qap_self['p_value'] < 0.01, 'QAP self-correlation must be significant'
    # The joint permutation must actually permute: a shuffled matrix differs
    assert qap_indep['null_std'] > 0, 'QAP null distribution must not be degenerate'
    print('  [PASS] QAP separates independent matrices from identical ones.')

    # 9. Node attributes projected onto edges, and edge-attribute extraction.
    G_attr = nx.Graph()
    G_attr.add_node('a', dominant_ressort='Sport')
    G_attr.add_node('b', dominant_ressort='Sport')
    G_attr.add_node('c', dominant_ressort='Wirtschaft')
    G_attr.add_edge('a', 'b', weight=2.0)
    G_attr.add_edge('b', 'c', weight=5.0)
    order = ['a', 'b', 'c']
    M_same = edge_matrix_from_node_attribute(G_attr, order, 'dominant_ressort')
    assert M_same[0, 1] == 1.0 and M_same[1, 2] == 0.0, 'Same-ressort projection wrong'
    assert np.allclose(M_same, M_same.T), 'Projected matrix must be symmetric'
    M_w = edge_matrix_from_edge_attribute(G_attr, order, 'weight')
    assert M_w[0, 1] == 2.0 and M_w[1, 2] == 5.0 and M_w[0, 2] == 0.0, 'Edge matrix wrong'
    assert M_w.trace() == 0.0, 'Diagonal must be zero'
    print('  [PASS] Node-to-edge projection and edge matrices are correct.')

    # 10. Cohesion and connectivity on a graph with a known cut vertex.
    # Two triangles joined through the single node 'x' -> x is the only
    # articulation point, both joining edges are bridges.
    G_cut = nx.Graph()
    G_cut.add_edges_from([('a', 'b'), ('b', 'c'), ('a', 'c'),
                          ('c', 'x'), ('x', 'd'),
                          ('d', 'e'), ('e', 'f'), ('d', 'f')])
    G_cut.add_node('lonely')  # isolate, must not break the analysis
    coh = analyze_cohesion_and_connectivity(G_cut)
    assert coh['n_isolates'] == 1, 'Isolate not counted'
    assert coh['gcc_nodes'] == 7, f"GCC should hold 7 nodes, got {coh['gcc_nodes']}"
    assert coh['clique_number'] == 3, f"Clique number should be 3, got {coh['clique_number']}"
    assert coh['n_articulation_points'] == 3, \
        f"Expected 3 articulation points (c, x, d), got {coh['n_articulation_points']}"
    assert coh['n_bridges'] == 2, f"Expected 2 bridges, got {coh['n_bridges']}"
    assert coh['node_connectivity'] == 1, 'A graph with a cut vertex has connectivity 1'
    assert coh['top_cut_vertices'][0]['node'] == 'x', \
        'The most damaging cut vertex must be x (splits the graph evenly)'
    print('  [PASS] Cohesion and connectivity detect cliques, cores and cut vertices.')

    # 11. Network rendering produces a deterministic, non-trivial file.
    with tempfile.TemporaryDirectory() as tmpdir:
        p1 = os.path.join(tmpdir, 'a.png')
        p2 = os.path.join(tmpdir, 'b.png')
        deg = dict(G_cut.degree())
        draw_network(G_cut, p1, size_by=deg, title='Test', highlight_nodes=['x'])
        draw_network(G_cut, p2, size_by=deg, title='Test', highlight_nodes=['x'])
        assert os.path.getsize(p1) > 5000, 'Rendered network is suspiciously small'
        with open(p1, 'rb') as f1, open(p2, 'rb') as f2:
            assert f1.read() == f2.read(), 'Rendering must be deterministic'
    print('  [PASS] Network rendering is deterministic and non-trivial.')

    print('All unit tests passed successfully!')

if __name__ == '__main__':
    run_synthetic_unit_tests()
