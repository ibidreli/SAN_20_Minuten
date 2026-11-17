"""Wiederverwendbare Grafiken für die Notebooks (matplotlib).

`stil()` einmal zu Beginn aufrufen: Danach sehen alle Grafiken gleich aus
(Schrift, Raster, keine Rahmen oben/rechts). Ressorts haben in allen
Grafiken und Netzzeichnungen dieselbe Farbe (`RESSORT_FARBEN`).
"""

import math
from collections import Counter

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import networkx as nx
import pandas as pd
from matplotlib.lines import Line2D

PALETTE = list(plt.get_cmap("tab10").colors) + list(plt.get_cmap("Set2").colors)
BLAU = "#3b6ea8"
GRAU = "#c8c8c8"
DUNKELGRAU = "#555555"
AKZENT = "#d62728"

RESSORT_FARBEN = {
    "Regionen": "#3fae49",
    "Ausland": "#e5413b",
    "Schweiz": "#f08c1e",
    "Sport": "#8e44ad",
    "People": "#2f7fd0",
    "Wirtschaft": "#8b5a2b",
    "Lifestyle": "#e0529c",
    "Wissen": "#c9a227",
    "Community": "#14b8b0",
    "Digital": "#1b3f73",
    "Coronavirus": "#5b5b5b",
    "andere": GRAU,
}
TYP_FARBEN = {"THEMA": "#3b6ea8", "LOC": "#3fae49", "PER": "#e5413b", "ORG": "#f08c1e", "MISC": "#8e44ad"}


def stil() -> None:
    """Einheitlicher Stil für alle Notebook-Grafiken."""
    plt.rcParams.update({
        "figure.figsize": (10, 4),
        "figure.dpi": 110,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "bold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.labelsize": 10,
        "axes.labelcolor": DUNKELGRAU,
        "axes.edgecolor": "#999999",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "axes.axisbelow": True,
        "grid.color": "#e6e6e6",
        "grid.linewidth": 0.8,
        "xtick.color": DUNKELGRAU,
        "ytick.color": DUNKELGRAU,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "axes.prop_cycle": plt.cycler(color=PALETTE),
    })


def tausender(ax, achse: str = "y") -> None:
    """Achsenbeschriftung mit Tausendertrennzeichen (12'000)."""
    formatierer = mticker.FuncFormatter(lambda x, _: f"{x:,.0f}".replace(",", "'"))
    (ax.yaxis if achse == "y" else ax.xaxis).set_major_formatter(formatierer)


def prozent(ax, achse: str = "y", basis: float = 1.0) -> None:
    """Achse als Prozent beschriften (basis=1: Werte sind Anteile)."""
    (ax.yaxis if achse == "y" else ax.xaxis).set_major_formatter(mticker.PercentFormatter(basis, decimals=0))


def kategorie_farben(werte, max_kategorien: int = 10) -> dict:
    """Häufigste Kategorien -> Farbe, Rest -> grau. Ressorts mit fester Farbe."""
    haeufig = [k for k, _ in Counter(werte).most_common(max_kategorien)]
    if haeufig and all(k in RESSORT_FARBEN for k in haeufig):
        return {k: RESSORT_FARBEN[k] for k in haeufig}
    if haeufig and all(k in TYP_FARBEN for k in haeufig):
        return {k: TYP_FARBEN[k] for k in haeufig}
    return {k: PALETTE[i % len(PALETTE)] for i, k in enumerate(haeufig)}


def netz_zeichnen(
    graph: nx.Graph,
    *,
    ax=None,
    top: int = 120,
    farbe: str | None = "community",
    beschriftung: int = 25,
    titel: str = "",
    seed: int = 42,
    max_kategorien: int = 10,
    hervorheben: str | None = None,
    legende_titel: str | None = None,
    namen: dict | None = None,
):
    """Zeichnet die `top` stärksten Knoten (gewichteter Grad).

    Knotengrösse = Stärke, Farbe = kategorisches Attribut, Kantenbreite =
    Gewicht. Beschriftet werden die `beschriftung` stärksten Knoten.
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(11, 8.5))
    ax.set_axis_off()
    if graph.number_of_edges() == 0:
        ax.set_title(f"{titel} (keine Kanten)")
        return ax
    staerke = dict(graph.degree(weight="weight"))
    knoten = sorted(staerke, key=staerke.get, reverse=True)[:top]
    sub = graph.subgraph(knoten)
    # Nur die grösste zusammenhängende Gruppe zeichnen: abgetrennte
    # Kleinteile würden das Layout auseinanderziehen und den Kern stauchen.
    if not nx.is_connected(sub):
        sub = sub.subgraph(max(nx.connected_components(sub), key=len))
    # Layout mit logarithmierten Gewichten: sonst ziehen wenige sehr starke
    # Kanten alles auf einen Punkt zusammen.
    layout = nx.Graph()
    layout.add_nodes_from(sub)
    layout.add_edges_from((a, b, {"w": 1 + math.log1p(d.get("weight", 1))}) for a, b, d in sub.edges(data=True))
    pos = nx.spring_layout(layout, weight="w", seed=seed, k=3 / max(len(sub), 1) ** 0.5, iterations=200)
    max_s = max(staerke[k] for k in sub) or 1
    groessen = [25 + 800 * staerke[k] / max_s for k in sub]
    if farbe:
        werte = {k: sub.nodes[k].get(farbe, "unbekannt") for k in sub}
        farben = kategorie_farben(werte.values(), max_kategorien)
        knotenfarben = [farben.get(werte[k], GRAU) for k in sub]
    else:
        farben, knotenfarben = {}, [BLAU] * len(sub)
    gewichte = [d.get("weight", 1) for *_, d in sub.edges(data=True)]
    max_w = max(gewichte) if gewichte else 1
    nx.draw_networkx_edges(
        sub, pos, ax=ax, width=[0.2 + 2.5 * w / max_w for w in gewichte], alpha=0.18, edge_color="#777777"
    )
    nx.draw_networkx_nodes(
        sub, pos, ax=ax, node_size=groessen, node_color=knotenfarben, linewidths=0.6, edgecolors="white", alpha=0.95
    )
    beschriftet = sorted(sub, key=staerke.get, reverse=True)[:beschriftung]
    if hervorheben and hervorheben in sub and hervorheben not in beschriftet:
        beschriftet.append(hervorheben)
    nx.draw_networkx_labels(
        sub, pos, labels={k: k for k in beschriftet}, ax=ax, font_size=8,
        bbox={"facecolor": "white", "alpha": 0.7, "edgecolor": "none", "pad": 0.4},
    )
    if hervorheben and hervorheben in sub:
        nx.draw_networkx_nodes(
            sub, pos, nodelist=[hervorheben], ax=ax, node_color=AKZENT,
            node_size=[25 + 800 * staerke[hervorheben] / max_s],
        )
    if farben:
        legende = [
            Line2D([0], [0], marker="o", color="w", markerfacecolor=f, markersize=8,
                   label=str((namen or {}).get(k, k)))
            for k, f in farben.items()
        ]
        if any(werte[k] not in farben for k in sub):
            legende.append(
                Line2D([0], [0], marker="o", color="w", markerfacecolor=GRAU, markersize=8, label="übrige")
            )
        ax.legend(handles=legende, title=legende_titel or farbe, loc="upper left", bbox_to_anchor=(1, 1))
    ax.set_title(titel or "Stärkste Knoten")
    return ax


def balken(
    serie: pd.Series,
    *,
    ax=None,
    titel: str = "",
    xlabel: str = "",
    farbe=None,
    referenz=None,
    referenz_label: str | None = None,
    werte: bool = True,
    fmt: str = "{:,.0f}",
):
    """Horizontales Balkendiagramm, grösster Wert oben.

    `werte` schreibt die Zahl ans Balkenende, `referenz` zieht eine
    gestrichelte Vergleichslinie (z. B. Median aller Artikel).
    """
    if ax is None:
        _, ax = plt.subplots(figsize=(8, max(2.5, 0.32 * len(serie) + 0.8)))
    reihe = serie.iloc[::-1]
    if isinstance(farbe, dict):
        farbe = [farbe.get(k, GRAU) for k in reihe.index]
    ax.barh([str(i) for i in reihe.index], reihe.values, color=farbe or BLAU, height=0.7)
    ax.grid(axis="y", visible=False)
    ax.tick_params(axis="y", length=0)
    if werte:
        maximum = max(reihe.max(), 1e-9)
        for i, wert in enumerate(reihe.values):
            if pd.notna(wert):
                ax.text(wert + maximum * 0.01, i, fmt.format(wert).replace(",", "'"), va="center",
                        fontsize=8, color=DUNKELGRAU)
        ax.set_xlim(0, maximum * 1.12)
    if referenz is not None:
        ax.axvline(referenz, color=AKZENT, linestyle="--", linewidth=1, label=referenz_label)
        if referenz_label:
            ax.legend(loc="lower right")
    ax.set(title=titel, xlabel=xlabel, ylabel="")
    return ax


def permutation_zeichnen(test: dict, *, ax=None, titel: str = "", xlabel: str = "Assortativität"):
    """Nullverteilung als Histogramm, beobachteter Wert als rote Linie."""
    if ax is None:
        _, ax = plt.subplots(figsize=(8, 3.5))
    ax.hist(test["null_verteilung"], bins=30, color=GRAU, label="Ressorts zufällig verteilt")
    ax.axvline(test["beobachtet"], color=AKZENT, linewidth=2, label=f"beobachtet: {test['beobachtet']:.2f}")
    ax.set(title=titel or "Permutationstest", xlabel=xlabel, ylabel="Anzahl Permutationen")
    ax.legend(loc="upper center")
    return ax


def heatmap(tabelle: pd.DataFrame, *, ax=None, titel: str = "", fmt: str = "{:.2f}", cmap: str = "Blues",
            farbbalken: bool = False, schrift: int = 8, drehung: int | None = None):
    """Tabelle als Heatmap mit Zahlen in den Zellen (fmt="" = ohne Zahlen)."""
    if ax is None:
        _, ax = plt.subplots(figsize=(1.5 + 0.7 * tabelle.shape[1], 1 + 0.4 * tabelle.shape[0]))
    werte = tabelle.astype(float).to_numpy()
    bild = ax.imshow(werte, cmap=cmap, aspect="auto")
    ax.grid(False)
    if drehung is None:
        drehung = 45 if max(len(str(c)) for c in tabelle.columns) > 4 and tabelle.shape[1] > 6 else 0
    ax.set_xticks(range(tabelle.shape[1]), [str(c) for c in tabelle.columns], rotation=drehung,
                  ha="right" if drehung else "center")
    ax.set_yticks(range(tabelle.shape[0]), [str(i) for i in tabelle.index])
    ax.tick_params(length=0)
    for seite in ax.spines.values():
        seite.set_visible(False)
    grenze = (pd.Series(werte.ravel()).max() or 1) * 0.6
    if fmt:
        for i in range(tabelle.shape[0]):
            for j in range(tabelle.shape[1]):
                if pd.notna(werte[i, j]):
                    ax.text(j, i, fmt.format(werte[i, j]).replace(",", "'"), ha="center", va="center", fontsize=schrift,
                            color="white" if werte[i, j] > grenze else "black")
    if farbbalken:
        ax.figure.colorbar(bild, ax=ax, shrink=0.8)
    ax.set_title(titel)
    return ax


def streu_beschriftet(df: pd.DataFrame, x: str, y: str, *, ax=None, beschriftung: int = 15,
                      titel: str = "", log: bool = False, farbe=None, xlabel: str | None = None,
                      ylabel: str | None = None):
    """Streudiagramm; die Punkte mit den höchsten x+y-Rängen werden beschriftet."""
    if ax is None:
        _, ax = plt.subplots(figsize=(9, 6))
    ax.scatter(df[x], df[y], s=16, alpha=0.55, color=farbe or BLAU, edgecolors="none")
    if log:
        ax.set_xscale("log")
        ax.set_yscale("log")
    rang = df[x].rank(pct=True) + df[y].rank(pct=True)
    for name in rang.nlargest(beschriftung).index:
        ax.annotate(str(name), (df.at[name, x], df.at[name, y]), fontsize=7.5,
                    xytext=(3, 3), textcoords="offset points", color="#333333")
    ax.set(title=titel, xlabel=xlabel or x, ylabel=ylabel or y)
    return ax
