"""Minimalbeispiel: Wie aus Artikeln und Keywords ein Netzwerk wird.

Nimmt fuenf echte Artikel aus dem bereinigten Korpus, beschraenkt das
Vokabular auf deren zehn haeufigste Begriffe und zeichnet drei Schritte:

  A  Two-Mode: Artikel und Keywords als zwei Knotenmengen
  B  One-Mode-Projektion dieser fuenf Artikel (Kantengewicht = gemeinsame Artikel)
  C  dieselben zehn Begriffe, Gewichte aber aus dem gesamten Korpus

Aufruf vom Repository-Wurzelverzeichnis:  python src/00_beispiel_netzwerk.py
"""

import itertools
import os
import random
from collections import Counter

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

# ---------------- Konfiguration ----------------
DEFAULT_DATA = "data/20min_cleaned_post2020.parquet"
FALLBACK_DATA = (
    "/Users/lucamanna/Documents/00_Coding/fhnw/06_AngewandteDataScience/"
    "SAN_20_Minuten/data/20min_cleaned_post2020.parquet"
)
OUT_PNG = "out_plots/beispiel_5artikel_10keywords.png"
SEED_TERM = "corona"
SEED_RANDOM = 11
N_ARTICLES = 5
N_KEYWORDS = 10

# Validierte Palette (dataviz, light mode, alle sechs Checks PASS)
C_KEYWORD = "#2a78d6"
C_ARTICLE = "#eb6834"
C_SURFACE = "#fcfcfb"
C_INK = "#0b0b0b"
C_INK_2 = "#52514e"
C_EDGE = "#b8b7b2"

plt.rcParams.update({
    "figure.facecolor": C_SURFACE,
    "axes.facecolor": C_SURFACE,
    "font.size": 10,
    "text.color": C_INK,
})


def load() -> pd.DataFrame:
    path = DEFAULT_DATA if os.path.exists(DEFAULT_DATA) else FALLBACK_DATA
    return pd.read_parquet(
        path, columns=["article_id", "datum", "titel", "ressort", "clean_terms_list"]
    )


def pick_articles(df: pd.DataFrame):
    """Fuenf Artikel eines Themas, die sich teilweise, aber nicht voll ueberlappen.

    Maximale Ueberlappung waere fuer die Illustration nutzlos: die Projektion
    waere ein vollstaendiger Graph. Gesucht ist eine Auswahl, in der die
    Artikel-Cliquen sichtbar bleiben und sich an gemeinsamen Begriffen beruehren.
    """
    rng = random.Random(SEED_RANDOM)
    sub = df[df["clean_terms_list"].apply(lambda t: SEED_TERM in t)].head(4000)
    sub = sub.reset_index(drop=True)
    sets = [set(t) for t in sub["clean_terms_list"]]

    best = None
    for _ in range(20000):
        idx = rng.sample(range(len(sets)), N_ARTICLES)
        chosen = [sets[i] for i in idx]

        freq = Counter()
        for c in chosen:
            freq.update(c)
        vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))][:N_KEYWORDS]
        vset = set(vocab)
        trimmed = [c & vset for c in chosen]

        if min(len(c) for c in trimmed) < 3:
            continue
        # das Vokabular soll nicht aus Einzelvorkommen bestehen: mindestens
        # sieben der zehn Begriffe muessen in zwei oder mehr Artikeln stehen
        if sum(1 for w in vocab if freq[w] >= 2) < 7:
            continue
        pairs = set()
        for c in trimmed:
            pairs.update(itertools.combinations(sorted(c), 2))
        density = 2 * len(pairs) / (N_KEYWORDS * (N_KEYWORDS - 1))
        if not 0.35 <= density <= 0.6:
            continue
        g = nx.Graph()
        g.add_nodes_from(vocab)
        g.add_edges_from(pairs)
        if not nx.is_connected(g):
            continue
        if best is None or abs(density - 0.45) < best[0]:
            best = (abs(density - 0.45), idx)
        if best[0] < 0.02:
            break

    if best is None:
        raise RuntimeError("keine passende Artikelauswahl gefunden")
    return sub.loc[best[1]].reset_index(drop=True), [sets[i] for i in best[1]]


def main() -> None:
    df = load()
    arts, sets = pick_articles(df)

    freq = Counter()
    for s in sets:
        freq.update(s)
    # gleiche deterministische Sortierung wie in pick_articles: Haeufigkeit, dann alphabetisch
    vocab = [w for w, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))][:N_KEYWORDS]
    vset = set(vocab)
    sets = [s & vset for s in sets]
    labels = [f"A{i + 1}" for i in range(len(arts))]

    # --- B: Projektion auf die fuenf Artikel ---
    pair_small = Counter()
    for s in sets:
        for a, b in itertools.combinations(sorted(s), 2):
            pair_small[(a, b)] += 1

    # --- C: dieselben Begriffe, Gewichte aus dem Gesamtkorpus ---
    pair_full, docfreq_full = Counter(), Counter()
    for terms in df["clean_terms_list"]:
        s = sorted(set(terms) & vset)
        docfreq_full.update(s)
        for a, b in itertools.combinations(s, 2):
            pair_full[(a, b)] += 1

    fig = plt.figure(figsize=(14, 12.5))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.05, 1], hspace=0.16, wspace=0.08)
    ax_a = fig.add_subplot(gs[0, :])
    ax_b = fig.add_subplot(gs[1, 0])
    ax_c = fig.add_subplot(gs[1, 1])
    for ax in (ax_a, ax_b, ax_c):
        ax.set_axis_off()

    # ---------- Panel A: Two-Mode ----------
    B = nx.Graph()
    B.add_nodes_from(labels, bipartite=0)
    B.add_nodes_from(vocab, bipartite=1)
    for lab, s in zip(labels, sets):
        B.add_edges_from((lab, w) for w in s)

    pos = {lab: (0.0, 1 - i * (2 / (len(labels) - 1))) for i, lab in enumerate(labels)}
    pos.update(
        {w: (1.0, 1.15 - i * (2.3 / (len(vocab) - 1))) for i, w in enumerate(vocab)}
    )

    nx.draw_networkx_edges(B, pos, ax=ax_a, edge_color=C_EDGE, width=1.1, alpha=0.9)
    nx.draw_networkx_nodes(
        B, pos, nodelist=labels, ax=ax_a, node_shape="s",
        node_size=1500, node_color=C_ARTICLE, edgecolors=C_SURFACE, linewidths=2,
    )
    nx.draw_networkx_nodes(
        B, pos, nodelist=vocab, ax=ax_a,
        node_size=[260 + 420 * freq[w] for w in vocab],
        node_color=C_KEYWORD, edgecolors=C_SURFACE, linewidths=2,
    )
    nx.draw_networkx_labels(
        B, pos, labels={l: l for l in labels}, ax=ax_a, font_color="white",
        font_size=11, font_weight="bold",
    )
    for w in vocab:
        x, y = pos[w]
        ax_a.text(x + 0.055, y, f"{w}  ({freq[w]})", va="center", ha="left",
                  fontsize=11, color=C_INK)
    for lab, (x, y), row in zip(labels, [pos[l] for l in labels], arts.itertuples()):
        ax_a.text(x - 0.055, y, f"{row.titel[:52]}\n{row.datum.date()} · {row.ressort}",
                  va="center", ha="right", fontsize=8.5, color=C_INK_2)

    ax_a.set_xlim(-0.75, 1.55)
    ax_a.set_title(
        "A  Two-Mode: so liegen die Daten vor\n"
        "Quadrate = Artikel, Kreise = Keywords. Eine Kante heisst „Begriff kommt im Artikel vor“.",
        loc="left", fontsize=13, color=C_INK, pad=14,
    )

    # ---------- Panel B / C: Projektionen ----------
    def draw_projection(ax, pairs, node_weight, title, note, label_min):
        G = nx.Graph()
        G.add_nodes_from(vocab)
        G.add_weighted_edges_from((a, b, w) for (a, b), w in pairs.items())
        p = nx.spring_layout(G, seed=7, weight="weight", k=0.9, iterations=400)
        wmax = max(nx.get_edge_attributes(G, "weight").values())
        widths = [0.8 + 5.2 * (d["weight"] / wmax) for _, _, d in G.edges(data=True)]
        nx.draw_networkx_edges(G, p, ax=ax, width=widths, edge_color=C_EDGE, alpha=0.95)
        smax = max(node_weight.values())
        nx.draw_networkx_nodes(
            G, p, ax=ax, node_color=C_KEYWORD, edgecolors=C_SURFACE, linewidths=2,
            node_size=[300 + 2100 * (node_weight[w] / smax) for w in G],
        )
        for w, (x, y) in p.items():
            ax.text(x, y - 0.115, w, ha="center", va="top", fontsize=10, color=C_INK)
        # selektive Kantenlabels: nur die staerksten Verbindungen
        for a, b, d in G.edges(data=True):
            if d["weight"] >= label_min:
                xa, ya = p[a]
                xb, yb = p[b]
                ax.text((xa + xb) / 2, (ya + yb) / 2, f"{d['weight']:,}".replace(",", "'"),
                        ha="center", va="center", fontsize=8.5, color=C_INK_2,
                        bbox=dict(boxstyle="round,pad=0.18", fc=C_SURFACE, ec="none"))
        ax.margins(0.16)
        ax.set_title(title, loc="left", fontsize=13, color=C_INK, pad=10)
        ax.text(0, -0.04, note, transform=ax.transAxes, fontsize=9.5,
                color=C_INK_2, va="top", ha="left")
        return G

    draw_projection(
        ax_b, pair_small, freq,
        "B  One-Mode-Projektion der fünf Artikel",
        f"10 Knoten, {len(pair_small)} Kanten, Dichte "
        f"{2 * len(pair_small) / (N_KEYWORDS * (N_KEYWORDS - 1)):.2f}\n"
        "Knotengrösse = Anzahl Artikel · Kantenbreite = gemeinsame Artikel",
        label_min=3,
    )

    draw_projection(
        ax_c, pair_full, docfreq_full,
        "C  Dieselben zehn Begriffe, aber alle 118'302 Artikel",
        f"10 Knoten, {len(pair_full)} Kanten, Dichte "
        f"{2 * len(pair_full) / (N_KEYWORDS * (N_KEYWORDS - 1)):.2f}\n"
        "Gleiche Regel, echte Datenmenge: alles hängt mit allem zusammen",
        label_min=sorted(pair_full.values(), reverse=True)[7],
    )

    fig.suptitle(
        "Vom Artikel zum Keyword-Netzwerk · 20 Minuten, bereinigter Korpus 2020–2024",
        x=0.5, y=0.975, fontsize=15, color=C_INK,
    )
    fig.savefig(OUT_PNG, dpi=150, bbox_inches="tight", facecolor=C_SURFACE)
    print(f"gespeichert: {OUT_PNG}")
    print("Artikel:")
    for lab, row in zip(labels, arts.itertuples()):
        print(f"  {lab} [{row.article_id}] {row.datum.date()} {row.ressort}: {row.titel}")
    print(f"Vokabular: {vocab}")
    print(f"B: {len(pair_small)} Kanten | C: {len(pair_full)} Kanten")


if __name__ == "__main__":
    main()
