"""Netzwerke aus Keywords und Personen bauen, messen und exportieren.

Modellierung (Skript Kap. 3):
- Two-Mode: Artikel – Keyword bzw. Artikel – Person.
- One-Mode-Projektion auf Keywords bzw. Personen. Jede Kante trägt drei
  Gewichte, `weight` ist das gewählte:
    anzahl  = Anzahl gemeinsamer Artikel (Kookkurrenz)
    newman  = Summe über gemeinsame Artikel von 1 / (n_Artikel - 1)
              (Newman's Weighted Projection: Artikel mit vielen Keywords
              zählen pro Paar weniger)
    salton  = anzahl / sqrt(df_i * df_j) (Kosinus; neutralisiert, dass
              häufige Begriffe überall mitkommen)
- `distanz` = 1 / weight für Pfad-basierte Masse (Betweenness, Closeness).

Achtung Clique-Artefakt: Jeder Artikel verbindet alle seine Keywords
untereinander. Das Clustering der Projektion ist deshalb künstlich hoch;
`nullmodell_clustering` liefert den Vergleichswert.
"""

import math
import random
from collections import Counter, defaultdict
from collections.abc import Iterable
from itertools import combinations
from pathlib import Path

import networkx as nx
import pandas as pd

GEWICHTE = ("anzahl", "newman", "salton")


# --------------------------------------------------------------------------
# Projektion
# --------------------------------------------------------------------------


def _gruppen(zuordnung: pd.DataFrame, spalte: str) -> list[list[str]]:
    """Pro Artikel die sortierte Liste der Knoten (ohne Duplikate)."""
    return [
        sorted(set(werte))
        for werte in zuordnung.groupby("url")[spalte].agg(list).tolist()
    ]


def projektion(
    zuordnung: pd.DataFrame,
    spalte: str,
    *,
    gewicht: str = "newman",
    min_anzahl: int = 1,
) -> nx.Graph:
    """One-Mode-Projektion einer Two-Mode-Zuordnung (url, spalte).

    Knoten bekommen `df` (Anzahl Artikel). Kanten unter `min_anzahl`
    gemeinsamen Artikeln werden verworfen.
    """
    if gewicht not in GEWICHTE:
        raise ValueError(f"gewicht muss eines von {GEWICHTE} sein")
    gruppen = _gruppen(zuordnung, spalte)
    df = Counter(knoten for gruppe in gruppen for knoten in gruppe)
    anzahl: Counter = Counter()
    newman: defaultdict = defaultdict(float)
    for gruppe in gruppen:
        n = len(gruppe)
        if n < 2:
            continue
        for paar in combinations(gruppe, 2):
            anzahl[paar] += 1
            newman[paar] += 1 / (n - 1)
    graph = nx.Graph()
    graph.add_nodes_from((knoten, {"df": wert}) for knoten, wert in df.items())
    for (a, b), wert in anzahl.items():
        if wert < min_anzahl:
            continue
        kante = {
            "anzahl": wert,
            "newman": newman[(a, b)],
            "salton": wert / math.sqrt(df[a] * df[b]),
        }
        kante["weight"] = kante[gewicht]
        kante["distanz"] = 1 / kante["weight"]
        graph.add_edge(a, b, **kante)
    return graph


def zweimodus(zuordnung: pd.DataFrame, spalte: str) -> nx.Graph:
    """Bipartiter Graph Artikel – Knoten mit Attribut `modus`."""
    graph = nx.Graph()
    graph.add_nodes_from(zuordnung["url"].unique(), modus="artikel", bipartite=0)
    graph.add_nodes_from(zuordnung[spalte].unique(), modus=spalte, bipartite=1)
    graph.add_edges_from(zuordnung[["url", spalte]].itertuples(index=False))
    return graph


# --------------------------------------------------------------------------
# Keyword- und Personennetze
# --------------------------------------------------------------------------


def keyword_zuordnung(
    keywords: pd.DataFrame,
    artikel: pd.DataFrame,
    *,
    jahre: Iterable[int] | None = None,
    typen: Iterable[str] | None = None,
    ohne_ticker: bool = True,
    min_df: int = 5,
) -> pd.DataFrame:
    """Artikel–Keyword-Paare für einen Ausschnitt.

    `min_df` gilt im Ausschnitt: Keywords in weniger Artikeln fallen weg.
    Liveticker sammeln Dutzende Themen in einem Artikel und erzeugen grosse
    Cliquen; sie sind deshalb standardmässig ausgeschlossen.
    """
    auswahl = artikel
    if jahre is not None:
        auswahl = auswahl[auswahl["jahr"].isin(list(jahre))]
    if ohne_ticker:
        auswahl = auswahl[~auswahl["ticker"]]
    paare = keywords[keywords["url"].isin(auswahl["url"])]
    if typen is not None:
        paare = paare[paare["typ"].isin(list(typen))]
    paare = paare[["url", "keyword", "typ"]].drop_duplicates(["url", "keyword"])
    df = paare["keyword"].map(paare["keyword"].value_counts())
    return paare[df >= min_df].reset_index(drop=True)


def keyword_netz(
    keywords: pd.DataFrame,
    artikel: pd.DataFrame,
    *,
    jahre: Iterable[int] | None = None,
    typen: Iterable[str] | None = None,
    min_df: int = 5,
    min_anzahl: int = 2,
    gewicht: str = "newman",
    ohne_ticker: bool = True,
) -> nx.Graph:
    """Keyword–Keyword-Netz mit Knotenattributen.

    Knotenattribute: typ, df, ressort (häufigstes oberstes Ressort),
    ressort_anteil, erstes_jahr, likes_median, kommentare_median.
    """
    paare = keyword_zuordnung(
        keywords, artikel, jahre=jahre, typen=typen, ohne_ticker=ohne_ticker, min_df=min_df
    )
    graph = projektion(paare, "keyword", gewicht=gewicht, min_anzahl=min_anzahl)
    _knotenattribute(graph, paare, "keyword", artikel)
    typ = paare.drop_duplicates("keyword").set_index("keyword")["typ"]
    nx.set_node_attributes(graph, typ.to_dict(), "typ")
    return graph


def personen_zuordnung(
    personen: pd.DataFrame,
    artikel: pd.DataFrame,
    *,
    jahre: Iterable[int] | None = None,
    nur_aufgeloest: bool = False,
) -> pd.DataFrame:
    auswahl = artikel if jahre is None else artikel[artikel["jahr"].isin(list(jahre))]
    paare = personen[personen["url"].isin(auswahl["url"])]
    if nur_aufgeloest:
        paare = paare[paare["aufgeloest"]]
    return paare[["url", "person"]].drop_duplicates().reset_index(drop=True)


def koautoren_netz(
    personen: pd.DataFrame,
    artikel: pd.DataFrame,
    *,
    jahre: Iterable[int] | None = None,
    nur_aufgeloest: bool = False,
    gewicht: str = "anzahl",
) -> nx.Graph:
    """Co-Autorschaft: Personen, die gemeinsam einen Artikel zeichnen.

    Alle Personen mit Artikeln im Ausschnitt sind Knoten, auch ohne
    Co-Autor (isolierte Knoten gehören zur Aussage).
    """
    paare = personen_zuordnung(
        personen, artikel, jahre=jahre, nur_aufgeloest=nur_aufgeloest
    )
    graph = projektion(paare, "person", gewicht=gewicht)
    _knotenattribute(graph, paare, "person", artikel)
    nx.set_node_attributes(
        graph, {p: not p.startswith("kürzel:") for p in graph}, "aufgeloest"
    )
    return graph


def autoren_themen_netz(
    personen: pd.DataFrame,
    keywords: pd.DataFrame,
    artikel: pd.DataFrame,
    *,
    jahre: Iterable[int] | None = None,
    min_artikel: int = 10,
    min_aehnlichkeit: float = 0.1,
    nachbarn: int = 10,
) -> nx.Graph:
    """Personen verbunden nach thematischer Ähnlichkeit (Kosinus über Keywords).

    Jede Person ist ein Vektor ihrer Keyword-Häufigkeiten. Pro Person
    bleiben die `nachbarn` ähnlichsten Personen über `min_aehnlichkeit`
    (k-NN-Backbone), sonst wird das Netz fast vollständig.
    """
    paare = personen_zuordnung(personen, artikel, jahre=jahre)
    n_artikel = paare["person"].value_counts()
    paare = paare[paare["person"].map(n_artikel) >= min_artikel]
    themen = paare.merge(keywords[["url", "keyword"]], on="url")
    vektoren = themen.groupby("person")["keyword"].agg(Counter)
    normen = {p: math.sqrt(sum(v * v for v in c.values())) for p, c in vektoren.items()}
    # Invertierter Index: nur Paare mit gemeinsamem Keyword vergleichen.
    index: defaultdict = defaultdict(list)
    for person, zaehler in vektoren.items():
        for keyword, wert in zaehler.items():
            index[keyword].append((person, wert))
    skalar: defaultdict = defaultdict(float)
    for eintraege in index.values():
        for (a, wa), (b, wb) in combinations(sorted(eintraege), 2):
            skalar[(a, b)] += wa * wb
    aehnlich: defaultdict = defaultdict(list)
    for (a, b), wert in skalar.items():
        kosinus = wert / (normen[a] * normen[b])
        if kosinus >= min_aehnlichkeit:
            aehnlich[a].append((kosinus, b))
            aehnlich[b].append((kosinus, a))
    graph = nx.Graph()
    graph.add_nodes_from(vektoren.index)
    for person, liste in aehnlich.items():
        for kosinus, andere in sorted(liste, reverse=True)[:nachbarn]:
            graph.add_edge(person, andere, weight=kosinus, distanz=1 / kosinus)
    _knotenattribute(graph, paare, "person", artikel)
    top = themen.groupby("person")["keyword"].agg(
        lambda s: ", ".join(s.value_counts().index[:5])
    )
    nx.set_node_attributes(graph, top.to_dict(), "top_keywords")
    return graph


def _knotenattribute(
    graph: nx.Graph, paare: pd.DataFrame, spalte: str, artikel: pd.DataFrame
) -> None:
    info = paare.merge(
        artikel[["url", "jahr", "hauptressort", "likes", "kommentare", "ticker"]],
        on="url",
    )
    gruppen = info.groupby(spalte)
    nx.set_node_attributes(graph, gruppen["url"].nunique().to_dict(), "df")
    nx.set_node_attributes(graph, gruppen["jahr"].min().astype(int).to_dict(), "erstes_jahr")
    ressort = gruppen["hauptressort"].agg(
        lambda s: s.value_counts().index[0] if s.notna().any() else "unbekannt"
    )
    anteil = gruppen["hauptressort"].agg(
        lambda s: round(s.value_counts(normalize=True).iloc[0], 3) if s.notna().any() else 0.0
    )
    nx.set_node_attributes(graph, ressort.to_dict(), "ressort")
    nx.set_node_attributes(graph, anteil.to_dict(), "ressort_anteil")
    # Reaktionen ohne Liveticker: Ticker sammeln Likes über Tage.
    ohne = info[~info["ticker"]].groupby(spalte)
    for feld in ("likes", "kommentare"):
        median = ohne[feld].median().fillna(-1)
        nx.set_node_attributes(graph, median.to_dict(), f"{feld}_median")


# --------------------------------------------------------------------------
# Reduktion
# --------------------------------------------------------------------------


def backbone(graph: nx.Graph, nachbarn: int = 10, attribut: str = "weight") -> nx.Graph:
    """k-NN-Backbone: jede Kante bleibt, wenn sie für mindestens einen ihrer
    Endknoten zu den `nachbarn` stärksten gehört. Alle Knoten bleiben."""
    behalten = set()
    for knoten in graph:
        kanten = sorted(
            graph[knoten].items(), key=lambda item: item[1][attribut], reverse=True
        )
        for andere, _ in kanten[:nachbarn]:
            behalten.add(tuple(sorted((knoten, andere))))
    reduziert = nx.Graph()
    reduziert.add_nodes_from(graph.nodes(data=True))
    reduziert.add_edges_from((a, b, graph[a][b]) for a, b in behalten)
    return reduziert


def groesste_komponente(graph: nx.Graph) -> nx.Graph:
    if graph.number_of_nodes() == 0:
        return graph.copy()
    knoten = max(nx.connected_components(graph), key=len)
    return graph.subgraph(knoten).copy()


def ego_netz(graph: nx.Graph, knoten: str, radius: int = 1, top: int | None = 30) -> nx.Graph:
    """Ego-Netz; mit `top` nur die stärksten direkten Nachbarn."""
    if knoten not in graph:
        raise KeyError(f"{knoten!r} ist nicht im Netz")
    ego = nx.ego_graph(graph, knoten, radius=radius)
    if top is not None:
        nachbarn = sorted(
            graph[knoten].items(), key=lambda item: item[1]["weight"], reverse=True
        )[:top]
        ego = graph.subgraph([knoten, *(n for n, _ in nachbarn)]).copy()
    return ego


# --------------------------------------------------------------------------
# Kennzahlen
# --------------------------------------------------------------------------


def kennzahlen(graph: nx.Graph, *, durchmesser_bis: int = 3000) -> dict:
    """Globale Kennzahlen (Skript Kap. 8–9). Durchmesser nur bis
    `durchmesser_bis` Knoten der Giant Component, sonst zu teuer."""
    n, m = graph.number_of_nodes(), graph.number_of_edges()
    werte = {"knoten": n, "kanten": m, "dichte": nx.density(graph) if n > 1 else 0.0}
    if n == 0:
        return werte
    komponenten = list(nx.connected_components(graph))
    giant = groesste_komponente(graph)
    grade = [d for _, d in graph.degree()]
    werte.update(
        komponenten=len(komponenten),
        isolierte=sum(1 for d in grade if d == 0),
        giant_anteil=giant.number_of_nodes() / n,
        grad_mittel=sum(grade) / n,
        grad_max=max(grade),
        clustering=nx.average_clustering(graph),
        transitivitaet=nx.transitivity(graph),
    )
    if 1 < giant.number_of_nodes() <= durchmesser_bis:
        werte["durchmesser"] = nx.diameter(giant)
        werte["pfadlaenge_mittel"] = nx.average_shortest_path_length(giant)
    if m:
        werte["grad_zentralisierung"] = grad_zentralisierung(graph)
    return werte


def grad_zentralisierung(graph: nx.Graph) -> float:
    """Freeman-Zentralisierung des Grads (Skript Kap. 7): 1 = Stern, 0 = gleich."""
    n = graph.number_of_nodes()
    if n < 3:
        return 0.0
    grade = [d for _, d in graph.degree()]
    return sum(max(grade) - d for d in grade) / ((n - 1) * (n - 2))


def zentralitaeten(
    graph: nx.Graph, *, betweenness_stichprobe: int | None = 500, seed: int = 42
) -> pd.DataFrame:
    """Zentralitäten pro Knoten (Skript Kap. 6) als Tabelle.

    Betweenness über `distanz` (starke Kanten = kurz). Ab
    `betweenness_stichprobe` Knoten wird sie über eine Stichprobe von
    Quellknoten geschätzt.
    """
    k = None
    if betweenness_stichprobe and graph.number_of_nodes() > betweenness_stichprobe:
        k = betweenness_stichprobe
    tabelle = pd.DataFrame(
        {
            "grad": dict(graph.degree()),
            "staerke": dict(graph.degree(weight="weight")),
            "grad_zentralitaet": nx.degree_centrality(graph),
            "betweenness": nx.betweenness_centrality(
                graph, k=k, weight="distanz", seed=seed
            ),
        }
    )
    giant = groesste_komponente(graph)
    try:
        eigen = nx.eigenvector_centrality(giant, weight="weight", max_iter=1000)
    except (nx.PowerIterationFailedConvergence, nx.NetworkXException):
        eigen = {}
    tabelle["eigenvektor"] = pd.Series(eigen)
    for attribut in ("typ", "df", "ressort"):
        werte = nx.get_node_attributes(graph, attribut)
        if werte:
            tabelle[attribut] = pd.Series(werte)
    return tabelle.sort_values("staerke", ascending=False)


def communities(graph: nx.Graph, *, methode: str = "louvain", seed: int = 42) -> dict:
    """Communities (Skript Kap. 5) setzen das Knotenattribut `community`.

    Gibt Anzahl, Modularität und die Communities (gross nach klein) zurück.
    """
    if methode == "louvain":
        gruppen = nx.community.louvain_communities(graph, weight="weight", seed=seed)
    elif methode == "label_propagation":
        gruppen = list(nx.community.asyn_lpa_communities(graph, weight="weight", seed=seed))
    else:
        raise ValueError("methode: louvain oder label_propagation")
    gruppen = sorted(gruppen, key=len, reverse=True)
    for nummer, gruppe in enumerate(gruppen):
        for knoten in gruppe:
            graph.nodes[knoten]["community"] = nummer
    return {
        "anzahl": len(gruppen),
        "modularitaet": nx.community.modularity(graph, gruppen, weight="weight"),
        "gruppen": gruppen,
    }


def community_tabelle(graph: nx.Graph, gruppen: list[set], top: int = 8) -> pd.DataFrame:
    """Pro Community: Grösse, stärkste Knoten, häufigstes Ressort."""
    zeilen = []
    for nummer, gruppe in enumerate(gruppen):
        staerke = sorted(
            ((graph.degree(k, weight="weight"), k) for k in gruppe), reverse=True
        )
        ressorts = Counter(graph.nodes[k].get("ressort", "unbekannt") for k in gruppe)
        zeilen.append(
            {
                "community": nummer,
                "groesse": len(gruppe),
                "ressort": ressorts.most_common(1)[0][0],
                "top": ", ".join(k for _, k in staerke[:top]),
            }
        )
    return pd.DataFrame(zeilen)


def assortativitaet(graph: nx.Graph, attribut: str = "ressort") -> float:
    """Kategorische Assortativität (Skript Kap. 10): > 0 = Gleiches verbindet sich."""
    return nx.attribute_assortativity_coefficient(graph, attribut)


def nullmodell_clustering(
    zuordnung: pd.DataFrame,
    spalte: str,
    *,
    wiederholungen: int = 5,
    min_anzahl: int = 1,
    seed: int = 42,
) -> pd.DataFrame:
    """Clustering der Projektion gegen ein Konfigurationsmodell (Skript Kap. 11).

    Die Zuordnung Artikel–Knoten wird zufällig neu verteilt: Jeder Artikel
    behält seine Anzahl Keywords, jedes Keyword seine Häufigkeit. Was das
    echte Netz darüber hinaus an Clustering zeigt, ist inhaltlich bedingt,
    nicht durch die Cliquen der Projektion.
    """
    rng = random.Random(seed)
    echt = projektion(zuordnung, spalte, min_anzahl=min_anzahl)
    zeilen = [{"netz": "echt", **_clustering_werte(echt)}]
    urls = zuordnung["url"].tolist()
    werte = zuordnung[spalte].tolist()
    for nummer in range(wiederholungen):
        gemischt = werte[:]
        rng.shuffle(gemischt)
        zufall = pd.DataFrame({"url": urls, spalte: gemischt})
        graph = projektion(zufall, spalte, min_anzahl=min_anzahl)
        zeilen.append({"netz": f"zufall_{nummer + 1}", **_clustering_werte(graph)})
    return pd.DataFrame(zeilen)


def assortativitaet_test(
    graph: nx.Graph, attribut: str = "ressort", *, permutationen: int = 200, seed: int = 42
) -> dict:
    """Permutationstest der kategorischen Assortativität (Skript Kap. 11.3).

    Die Attributwerte werden zufällig auf die Knoten verteilt; die Struktur
    bleibt. p = Anteil der Permutationen mit mindestens so hoher
    Assortativität wie beobachtet.
    """
    rng = random.Random(seed)
    beobachtet = nx.attribute_assortativity_coefficient(graph, attribut)
    knoten = list(graph)
    werte = [graph.nodes[k].get(attribut) for k in knoten]
    kopie = graph.copy()
    null = []
    for _ in range(permutationen):
        rng.shuffle(werte)
        nx.set_node_attributes(kopie, dict(zip(knoten, werte)), attribut)
        null.append(nx.attribute_assortativity_coefficient(kopie, attribut))
    return {
        "beobachtet": beobachtet,
        "null_mittel": sum(null) / len(null),
        "null_max": max(null),
        "p_wert": (1 + sum(w >= beobachtet for w in null)) / (1 + len(null)),
        "null_verteilung": null,
    }


def stichprobe_pro_jahr(artikel: pd.DataFrame, n: int | None = None, seed: int = 42) -> pd.DataFrame:
    """Gleich viele Artikel pro Jahr (ohne Ticker).

    Kennzahlen wie Dichte und Clustering hängen von der Netzgrösse ab; für
    einen fairen Jahresvergleich brauchen alle Jahre dieselbe Artikelzahl.
    Ohne `n` gilt die Grösse des kleinsten Jahres.
    """
    basis = artikel[~artikel["ticker"]]
    n = n or int(basis["jahr"].value_counts().min())
    indizes = [
        gruppe.sample(min(n, len(gruppe)), random_state=seed).index
        for _, gruppe in basis.groupby("jahr")
    ]
    return basis.loc[[i for index in indizes for i in index]].reset_index(drop=True)


def link_prediction(
    alt: nx.Graph, neu: nx.Graph, *, max_paare: int = 20000, seed: int = 42
) -> pd.DataFrame:
    """Sagt neue Kanten von `alt` nach `neu` voraus (Skript Kap. 12).

    Nur Knoten, die in beiden Netzen vorkommen. Positive Paare: in `neu`
    verbunden, in `alt` nicht. Negative Paare: in keinem der beiden
    verbunden, zufällig gezogen, gleich viele wie positive.
    Bewertet mit AUC (Wahrscheinlichkeit, dass ein positives Paar höher
    bewertet wird als ein negatives) und Precision@k (k = Anzahl positive).
    """
    rng = random.Random(seed)
    knoten = sorted(set(alt) & set(neu))
    basis = alt.subgraph(knoten)
    positiv = [
        (a, b) for a, b in neu.subgraph(knoten).edges() if not basis.has_edge(a, b)
    ]
    rng.shuffle(positiv)
    positiv = positiv[: max_paare // 2]
    negativ, gesehen = [], set()
    versuche = 0
    while len(negativ) < len(positiv) and versuche < 50 * len(positiv) + 1000:
        versuche += 1
        a, b = rng.sample(knoten, 2)
        paar = (a, b) if a < b else (b, a)
        if paar in gesehen or basis.has_edge(*paar) or neu.has_edge(*paar):
            continue
        gesehen.add(paar)
        negativ.append(paar)
    if not positiv or not negativ:
        return pd.DataFrame()
    paare = positiv + negativ
    ziel = pd.Series([1] * len(positiv) + [0] * len(negativ))
    verfahren = {
        "common_neighbors": [len(list(nx.common_neighbors(basis, a, b))) for a, b in paare],
        "jaccard": [s for *_, s in nx.jaccard_coefficient(basis, paare)],
        "adamic_adar": [s for *_, s in nx.adamic_adar_index(basis, paare)],
        "resource_allocation": [s for *_, s in nx.resource_allocation_index(basis, paare)],
        "preferential_attachment": [s for *_, s in nx.preferential_attachment(basis, paare)],
    }
    zeilen = []
    for name, werte in verfahren.items():
        werte = pd.Series(werte, dtype=float)
        rang = werte.rank()  # Bindungen bekommen den mittleren Rang
        n_pos, n_neg = len(positiv), len(negativ)
        auc = (rang[ziel == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
        # Erst mischen: Bei gleichem Score darf die Reihenfolge der Liste
        # (positive Paare zuerst) das Ergebnis nicht begünstigen.
        top = (
            werte.sample(frac=1, random_state=seed)
            .sort_values(ascending=False, kind="stable")
            .index[:n_pos]
        )
        zeilen.append(
            {
                "verfahren": name,
                "auc": auc,
                "precision_at_k": ziel[top].mean(),
                "positive": n_pos,
                "negative": n_neg,
            }
        )
    return pd.DataFrame(zeilen).sort_values("auc", ascending=False).reset_index(drop=True)


def _clustering_werte(graph: nx.Graph) -> dict:
    return {
        "kanten": graph.number_of_edges(),
        "dichte": nx.density(graph),
        "clustering": nx.average_clustering(graph),
        "clustering_gewichtet": nx.average_clustering(graph, weight="salton"),
    }


# --------------------------------------------------------------------------
# Export
# --------------------------------------------------------------------------


def exportieren(graph: nx.Graph, pfad: str | Path) -> list[Path]:
    """Schreibt `<pfad>.gexf` (für Gephi) und Knoten-/Kantenlisten als CSV."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    sauber = nx.Graph()
    for knoten, daten in graph.nodes(data=True):
        sauber.add_node(knoten, label=str(knoten), **_gexf_werte(daten))
    for a, b, daten in graph.edges(data=True):
        sauber.add_edge(a, b, **_gexf_werte(daten))
    dateien = [
        pfad.with_suffix(".gexf"),
        pfad.with_name(pfad.name + "_knoten.csv"),
        pfad.with_name(pfad.name + "_kanten.csv"),
    ]
    nx.write_gexf(sauber, dateien[0])
    knoten = pd.DataFrame.from_dict(dict(graph.nodes(data=True)), orient="index")
    knoten.index.name = "id"
    knoten.to_csv(dateien[1], encoding="utf-8")
    kanten = nx.to_pandas_edgelist(graph, source="quelle", target="ziel")
    kanten.to_csv(dateien[2], index=False, encoding="utf-8")
    return dateien


def _gexf_werte(daten: dict) -> dict:
    # GEXF kennt kein None, keine numpy-Typen und keine Mengen.
    sauber = {}
    for schluessel, wert in daten.items():
        if wert is None or (isinstance(wert, float) and math.isnan(wert)):
            continue
        if hasattr(wert, "item"):
            wert = wert.item()
        if isinstance(wert, (set, list, tuple)):
            wert = ", ".join(map(str, wert))
        sauber[schluessel] = wert
    return sauber
