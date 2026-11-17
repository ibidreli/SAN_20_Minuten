"""Keyword-Landkarte nach dem Vorbild von David Kriesels SpiegelMining.

Quelle: dkriesel.com/blog/2016/1028_spiegelmining_think_big (Artikellandschaft).
Übernommen werden seine Modellierungsentscheide:

- Knoten: Keywords in mehr als MIN_DF Artikeln (Kriesel: > 10 bei 80'000 Artikeln).
- Kantengewicht "gegenseitige Wichtigkeit" in Prozent:
      w(A, B) = 100 * (n_AB / df_A + n_AB / df_B)      (0 % bis 200 %)
  Ein Paar ist stark, wenn die Keywords füreinander wichtig sind. Grosse
  Hubs (Schweiz, Polizei) verbinden sich so nicht automatisch mit allem.
- Ausdünnung lokal: Jeder Knoten behält seine stärksten ANTEIL_KANTEN (20 %)
  Kanten. Eine Kante bleibt, wenn sie für einen ihrer Endknoten dazugehört.
- Farbe = dominantes Ressort (> 50 % der Artikel), sonst grau.
- Grösse = Anzahl Artikel (df).

Farbe, Grösse und Label stehen direkt im GEXF (viz-Attribute), Gephi
übernimmt sie beim Import. Das Layout macht Gephi (ForceAtlas 2).

Aufruf aus dem Projektordner:  python src/keyword_landkarte.py
"""

import math
import sys
from collections import Counter
from itertools import combinations
from pathlib import Path

import networkx as nx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import daten  # noqa: E402
import netzwerk as nw  # noqa: E402

MIN_DF = 20
MIN_ANZAHL = 2
ANTEIL_KANTEN = 0.20
DOMINANZ = 0.5
ZIEL = daten.ROOT / "Graphen" / "keywords_landkarte"

GRAU = "#c8c8c8"
FARBEN = {
    "Ausland": "#e5413b",
    "Schweiz": "#f08c1e",
    "Regionen": "#3fae49",
    "Sport": "#8e44ad",
    "People": "#2f7fd0",
    "Digital": "#14b8b0",
    "Wissen": "#c9a227",
    "Wirtschaft": "#8b5a2b",
    "Lifestyle": "#e0529c",
    "Coronavirus": "#5b5b5b",
}


def hex_rgb(farbe: str) -> dict:
    farbe = farbe.lstrip("#")
    return {"r": int(farbe[0:2], 16), "g": int(farbe[2:4], 16), "b": int(farbe[4:6], 16), "a": 1.0}


def landkarte_netz(paare) -> nx.Graph:
    gruppen = [sorted(set(g)) for g in paare.groupby("url")["keyword"].agg(list)]
    df = Counter(k for g in gruppen for k in g)
    anzahl: Counter = Counter()
    for g in gruppen:
        anzahl.update(combinations(g, 2))

    # Pro Knoten alle Kanten mit dem Gewicht "gegenseitige Wichtigkeit" sammeln, dann Top 20 % behalten.
    nachbarn: dict[str, list] = {k: [] for k in df}
    for (a, b), n in anzahl.items():
        if n < MIN_ANZAHL:
            continue
        w = 100 * (n / df[a] + n / df[b])
        nachbarn[a].append((w, b, n))
        nachbarn[b].append((w, a, n))

    graph = nx.Graph()
    graph.add_nodes_from((k, {"df": v}) for k, v in df.items())
    for knoten, liste in nachbarn.items():
        if not liste:
            continue
        liste.sort(reverse=True)
        for w, andere, n in liste[: max(1, math.ceil(ANTEIL_KANTEN * len(liste)))]:
            graph.add_edge(knoten, andere, weight=round(w, 3), anzahl=n)
    return graph


def main() -> None:
    artikel = daten.load_articles(daten.ROOT / "data" / "articles.sqlite")
    keywords = daten.load_keywords(daten.ROOT / "data" / "articles.sqlite")
    paare = nw.keyword_zuordnung(keywords, artikel, min_df=MIN_DF)
    graph = landkarte_netz(paare)
    nw._knotenattribute(graph, paare, "keyword", artikel)
    graph = nw.groesste_komponente(graph)

    df_max = max(d for _, d in graph.nodes(data="df"))
    for knoten, attr in graph.nodes(data=True):
        dominant = attr.get("ressort_anteil", 0) > DOMINANZ
        attr["farbe_ressort"] = attr["ressort"] if dominant else "gemischt"
        farbe = FARBEN.get(attr["ressort"], GRAU) if dominant else GRAU
        # Fläche proportional zu df: Radius ~ Wurzel(df).
        groesse = 3 + 60 * math.sqrt(attr["df"] / df_max)
        attr["viz"] = {"color": hex_rgb(farbe), "size": round(groesse, 2)}
        attr["label"] = str(knoten).lower()

    sauber = nx.Graph()
    for k, attr in graph.nodes(data=True):
        werte = {s: (w.item() if hasattr(w, "item") else w) for s, w in attr.items() if s != "viz"}
        sauber.add_node(k, viz=attr["viz"], **werte)
    sauber.add_edges_from(graph.edges(data=True))
    ZIEL.parent.mkdir(exist_ok=True)
    nx.write_gexf(sauber, ZIEL.with_suffix(".gexf"))

    verteilung = Counter(a["farbe_ressort"] for _, a in graph.nodes(data=True))
    print(f"Knoten: {graph.number_of_nodes():,}  Kanten: {graph.number_of_edges():,}")
    print("Farbe:", dict(verteilung.most_common()))
    print("Gespeichert:", ZIEL.with_suffix(".gexf"))


if __name__ == "__main__":
    main()
