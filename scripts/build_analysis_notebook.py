import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []

# Title & Metadata
cells.append(nbf.v4.new_markdown_cell("""# Soziale Netzwerkanalyse: 20 Minuten (2020–2024)
## Strukturelle Dynamik, redaktionelle Kollaboration, Link-Prediction und Diffusion im Schweizer Online-Journalismus

**Autoren:** Elias & Luca  
**Modul:** Soziale Netzwerke Analysieren (SAN / SNA), FHNW  
**Dozent:** Michael Henninger  

---

### Abstract & Überblick

Dieses Notebook enthält die vollständige empirische Soziale Netzwerkanalyse des Schweizer News-Portals *20 Minuten* für die fünf vollständigen Kalenderjahre 2020 bis 2024 (118'302 bereinigte Artikel, 781 Journalist:innen). Wir untersuchen **vier Pfeiler**:

1. **Pfeiler 1 (LE3, LE5, LE7): Redaktionelle Silobildung, Homophilie und Brokerage**  
   Bipartite Modellierung (Artikel-Autor) und Projektion auf ein gewichtetes Newman-Kollaborationsnetzwerk. Ressort-Homophilie über drei Nullmodelle steigender Strenge: Label-Permutation ($B=5'000$), gradtreues Maslov-Sneppen-Rewiring und **QAP** mit gemeinsamer Zeilen-/Spalten-Permutation. Brokerage in zwei Operationalisierungen, **Burts Constraint und Effective Size** sowie Betweenness-Zentralität, deren Ranglisten bewusst getrennt ausgewiesen werden. Kohäsion und strukturelle Robustheit über Cliquen, $k$-Core, Artikulationspunkte und Brücken. Interdisziplinäre Zusammenarbeit über die leakage-freie Leave-One-Out-Jensen-Shannon-Divergenz.

2. **Pfeiler 2 (LE4, LE6): Makro-Topologie und Krisen-Evolution 2020–2024**  
   Longitudinale semantische Kookkurrenz-Netzwerke auf einem fixierten 1'200-Wörter-Vokabular mit Mutual-$k$-NN-Sparsifizierung. Kennzahlen auf der Riesenkomponente, Freeman-Zentralisierung $C_D$ **und $C_B$**, Louvain-Modularität über zehn Seeds. Eine **Sensitivitätsanalyse über $k \in \{5, 10, 20\}$** prüft, welche Befunde vom Sparsifizierungsparameter abhängen, und legt offen, dass das Design $C_D$ konstruktionsbedingt deckelt. Hypothese 2 wird explizit gegen die Erwartung aus dem Meilenstein geprüft.

3. **Pfeiler 3 (LE8): Rolling Temporal Link-Prediction**  
   Vorhersage zukünftiger Kooperationen über drei rollende Zeithorizonte unter unbalancierten Realbedingungen (Average Precision, Precision@$k$ für $k \in \{20, 50, 100\}$, ROC-AUC), mit Bootstrap-Konfidenzintervall für den Vergleich von Triadenschliessung (Adamic-Adar) und Popularität (Preferential Attachment).

4. **Pfeiler 4 (LE9): Diffusion im Kollaborationsnetzwerk**  
   Independent-Cascade-Simulation über den gesamten Bereich der Übertragungswahrscheinlichkeit $p$, mit Vergleich dreier Startmengen-Strategien (Burt-Broker, Hubs, Zufall).

Nicht abgedeckt ist LE10 (Graphlets); der Ausblick benennt dies als nächsten Schritt.

**Reproduzierbarkeit.** Alle Kennzahlen entstehen aus `src/network_models.py`, dessen Kernfunktionen durch 17 Unit-Tests abgesichert sind (`python src/network_models.py`). Die Datenintegrität ist über `data/manifest.json` prüfbar (`python scripts/build_manifest.py --check`). Sämtliche Abbildungen sind durchnummeriert (Abb. 1 bis 14) und im Text referenziert.

---
"""))

# Chapter 1: Setup & Data Ingestion
cells.append(nbf.v4.new_markdown_cell("""## 1. Setup, Datenimport & Bipartite Netzwerkmodellierung (LE3)

Wir importieren die benötigten wissenschaftlichen Bibliotheken und laden den bereinigten Parquet-Datensatz (`data/20min_cleaned_post2020.parquet`).
Gemäss dem Modullehrplan modellieren wir zunächst das **Two-Mode-Netzwerk** (Bipartiter Graph zwischen Artikeln und menschlichen Journalist:innen) und leiten anschliessend die gewichtete **One-Mode-Projektion** nach Newman (2001) ab.
"""))

cells.append(nbf.v4.new_code_cell("""import os
import json
import itertools
import numpy as np
import pandas as pd
import networkx as nx
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.metrics import precision_recall_curve, roc_curve, auc, average_precision_score
from collections import defaultdict, Counter

from src.network_models import (
    build_bipartite_author_article,
    compute_author_ressort_profiles,
    compute_jsd,
    project_author_collaboration,
    extract_global_vocabulary,
    build_annual_keyword_graph,
    create_rolling_link_prediction_windows,
    compute_leave_one_out_jsd,
    export_graph_gexf,
    qap_correlation_test,
    edge_matrix_from_edge_attribute,
    edge_matrix_from_node_attribute,
    jsd_matrix_from_profiles,
    analyze_cohesion_and_connectivity,
    simulate_diffusion,
    weight_normalizer,
    compute_burt_structural_holes,
    degree_centralization,
    betweenness_centralization,
    max_possible_degree_centralization,
    draw_network,
    CANONICAL_RESSORTS
)

# Plotting Configuration
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 11
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['figure.dpi'] = 150
os.makedirs('out_plots', exist_ok=True)
os.makedirs('graphen', exist_ok=True)

# 1. Load Clean Dataset
df = pd.read_parquet('data/20min_cleaned_post2020.parquet')
print(f'Geladene Artikel: {len(df):,}')
print(f'Zeitraum: {df["datum"].min().strftime("%Y-%m-%d")} bis {df["datum"].max().strftime("%Y-%m-%d")}')
print(f'Multi-Autor-Artikel: {(df["author_count"] > 1).sum():,} ({(df["author_count"] > 1).mean():.1%})')
"""))

cells.append(nbf.v4.new_code_cell("""# Bipartites Netzwerk aufbauen (LE3)
# Das Two-Mode-Netzwerk umfasst ALLE Artikel mit mindestens einer Autorenschaft.
# Eine Beschränkung auf Mehrautoren-Artikel wäre ein gefilterter Teilgraph und
# würde die Anzahl der Autoren- und Artikelknoten unterschätzen.
multi_df = df[df['author_count'] > 1].copy()
B = build_bipartite_author_article(df)

n_authors = sum(1 for n, d in B.nodes(data=True) if d['bipartite'] == 0)
n_articles = sum(1 for n, d in B.nodes(data=True) if d['bipartite'] == 1)
print(f'Bipartiter Graph (alle Artikel mit Autorenschaft): {n_authors:,} Autoren-Knoten, {n_articles:,} Artikel-Knoten, {B.number_of_edges():,} Kanten')
print(f'Davon Mehrautoren-Artikel: {len(multi_df):,} ({len(multi_df) / max(n_articles, 1):.1%} der Artikelknoten)')

# One-Mode-Projektion nach Newman (2001)
# Kanten-Gewichtung: w_ij = sum_{k} 1 / (|U_k| - 1)
G_collab = project_author_collaboration(df, min_articles=2)
print(f'One-Mode Kollaborations-Graph (min. 2 Artikel): {G_collab.number_of_nodes():,} Autoren, {G_collab.number_of_edges():,} Kollaborationskanten')
print(f'Netzwerk-Dichte: {nx.density(G_collab):.4f}')
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Modellierung).** Das Two-Mode-Netzwerk verbindet 814
Journalist:innen mit 83'707 Artikeln. Die Newman-Projektion auf ein One-Mode-
Netzwerk reduziert dies auf 574 Autor:innen mit 2'754 Kollaborationskanten,
weil nur Personen mit mindestens zwei Artikeln aufgenommen werden und
Einzelautorenschaften keine Kante erzeugen.

Die Gewichtung nach Newman ist hier wesentlich: Ein Artikel mit zwei Autor:innen
erzeugt eine Kante vom Gewicht 1, ein Artikel mit fuenf Autor:innen dagegen
zehn Kanten vom Gewicht je 0.25. Ohne diese Normierung wuerden grosse
Redaktionsteams die Struktur dominieren, obwohl die einzelne Zweierbeziehung
darin schwaecher ist. Die Netzwerkdichte von rund 1.7% zeigt bereits hier: die
Redaktion ist kein dicht verwobenes Kollektiv, sondern ein duenn besetztes Netz
aus vielen kleinen Konstellationen. Alle weiteren Analysen in Kapitel 2 bauen
auf diesem projizierten Graphen auf.
"""))

# Chapter 2: Pillar 1
cells.append(nbf.v4.new_markdown_cell("""## 2. Pfeiler 1: Kollaborationsstruktur, Ressort-Homophilie & Brokerage (LE3, LE5, LE7)

### Theoretischer Hintergrund & Forschungsfragen
- **Homophilie (Newman, 2002):** Bevorzugen Journalist:innen Kooperationen innerhalb ihres eigenen Fachressorts gegenüber fachfremden Kolleg:innen?
- **Strukturelle Löcher & Brokerage (Burt, 1992, 2004):** Welche Akteure überbrücken strukturelle Löcher, also verbinden Gruppen, die untereinander nicht vernetzt sind (niedriger Burt-Constraint, hohe Effective Size)? Und sind das dieselben Personen, die auf vielen kürzesten Pfaden liegen (hohe Betweenness)?
- **Interdisziplinäre Kooperation:** Unterscheidet sich die mittlere Kanten-Jensen-Shannon-Divergenz (JSD) signifikant von einem gradtreuen Zufallsmodell, und erzielen ressortübergreifende Kooperationen mehr Leser-Shares?
"""))

cells.append(nbf.v4.new_code_cell("""# 2.1 Zentralitätsmasse & Identifikation struktureller Broker (LE5)
deg_dict = dict(G_collab.degree())
bet_dict = nx.betweenness_centrality(G_collab, weight='distance')
close_dict = nx.closeness_centrality(G_collab, distance='distance')

for n in G_collab.nodes():
    G_collab.nodes[n]['degree'] = deg_dict[n]
    G_collab.nodes[n]['betweenness'] = bet_dict[n]
    G_collab.nodes[n]['closeness'] = close_dict[n]

author_metrics_df = pd.DataFrame([
    {
        'author': n,
        'degree': deg_dict[n],
        'betweenness': bet_dict[n],
        'closeness': close_dict[n],
        'articles': G_collab.nodes[n]['article_count'],
        'ressort': G_collab.nodes[n]['dominant_ressort'],
        'mean_likes': G_collab.nodes[n]['mean_likes'],
        'mean_shares': G_collab.nodes[n]['mean_shares'],
        'mean_comments': G_collab.nodes[n]['mean_comments']
    }
    for n in G_collab.nodes()
])

# Strukturelle Loecher nach Burt (LE5).
# Burt misst NICHT Betweenness, sondern wie stark die Kontakte einer Person
# untereinander vernetzt sind. Niedriger Constraint = die Person verbindet
# Gruppen, die sonst nicht miteinander reden.
burt = compute_burt_structural_holes(G_collab, weight='weight')
author_metrics_df['burt_constraint'] = author_metrics_df['author'].map(lambda a: burt[a]['constraint'])
author_metrics_df['effective_size'] = author_metrics_df['author'].map(lambda a: burt[a]['effective_size'])
author_metrics_df['efficiency'] = author_metrics_df['author'].map(lambda a: burt[a]['efficiency'])

# Nur Personen mit einem Mindestmass an Aktivitaet und Vernetzung, sonst
# dominieren Autor:innen mit zwei Artikeln und drei Kontakten die Rangliste.
MIN_DEGREE_BROKER = 5
MIN_ARTICLES_BROKER = 10
broker_pool = author_metrics_df[
    (author_metrics_df['degree'] >= MIN_DEGREE_BROKER) &
    (author_metrics_df['articles'] >= MIN_ARTICLES_BROKER)
].copy()
print(f'Broker-Grundgesamtheit: {len(broker_pool)} von {len(author_metrics_df)} Autor:innen '
      f'(mind. {MIN_DEGREE_BROKER} Kontakte und {MIN_ARTICLES_BROKER} Artikel)')

top_burt = broker_pool.sort_values('burt_constraint').head(10)
print('\\nTop 10 strukturelle Loecher nach Burt (niedrigster Constraint):')
print(top_burt[['author', 'ressort', 'degree', 'articles', 'burt_constraint',
                'effective_size', 'efficiency']].round(4).to_string(index=False))

top_between = broker_pool.sort_values('betweenness', ascending=False).head(10)
print('\\nTop 10 nach Betweenness-Zentralitaet (Vermittlung auf kuerzesten Pfaden):')
print(top_between[['author', 'ressort', 'degree', 'articles', 'betweenness',
                   'burt_constraint']].round(4).to_string(index=False))

overlap = set(top_burt['author']) & set(top_between['author'])
print(f'\\nSchnittmenge beider Ranglisten: {len(overlap)} Personen'
      + (f' ({", ".join(sorted(overlap))})' if overlap else ''))

# Abbildung 2: Burt-Constraint vs. Betweenness, zwei Broker-Begriffe im Vergleich
fig, axes = plt.subplots(1, 2, figsize=(15, 5.5))

top_ressorts = author_metrics_df['ressort'].value_counts().head(6).index
plot_df = broker_pool[broker_pool['ressort'].isin(top_ressorts)]

sns.scatterplot(
    data=plot_df, x='degree', y='betweenness', hue='ressort',
    palette='tab10', alpha=0.8, s=60, ax=axes[0]
)
for _, r in top_between.head(5).iterrows():
    axes[0].annotate(r['author'], (r['degree'], r['betweenness']),
                     xytext=(5, 5), textcoords='offset points',
                     fontsize=8, fontweight='bold')
axes[0].set_title('Betweenness: Vermittlung auf kuerzesten Pfaden')
axes[0].set_xlabel('Grad (Anzahl Koautor:innen)')
axes[0].set_ylabel('Betweenness-Zentralitaet')
axes[0].legend(title='Hauptressort', fontsize=8)

sc = axes[1].scatter(broker_pool['degree'], broker_pool['burt_constraint'],
                     c=broker_pool['effective_size'], cmap='viridis', s=55,
                     alpha=0.85, edgecolors='white', linewidths=0.4)
for _, r in top_burt.head(5).iterrows():
    axes[1].annotate(r['author'], (r['degree'], r['burt_constraint']),
                     xytext=(5, 5), textcoords='offset points',
                     fontsize=8, fontweight='bold')
axes[1].set_title('Burt: niedriger Constraint = ueberbrueckt strukturelle Loecher')
axes[1].set_xlabel('Grad (Anzahl Koautor:innen)')
axes[1].set_ylabel('Burt-Constraint (niedrig = Broker)')
fig.colorbar(sc, ax=axes[1], label='Effective Size')

plt.suptitle('Abbildung 1: Zwei Operationalisierungen redaktioneller Brokerage', y=1.02)
plt.tight_layout()
plt.savefig('out_plots/01_brokerage_burt_vs_betweenness.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 1, zwei Arten von Broker).** Die beiden Ranglisten
messen Verschiedenes und fallen entsprechend auseinander. **Betweenness** fragt,
wer auf vielen kuerzesten Wegen liegt. **Burts Constraint** fragt, wessen
Kontakte einander *nicht* kennen: ein niedriger Wert heisst, dass die Person
Gruppen verbindet, die sonst nichts miteinander zu tun haetten. Genau das ist
der Begriff des strukturellen Lochs, den der Meilenstein angekuendigt hat.

Die Burt-Rangliste wird von Personen mit hohem Grad und hoher Artikelzahl
angefuehrt, deren Effizienz nahe bei 1 liegt: nahezu jeder ihrer Kontakte
liefert ihnen Zugang zu einem eigenen Umfeld, ihre Koautor:innen ueberschneiden
sich also kaum. Redaktionell sind das die Personen mit dem breitesten
Informationszugang.

Die Betweenness-Rangliste enthaelt teilweise andere Namen, oft mit deutlich
geringerem Grad. Diese Personen sind nicht breit vernetzt, sitzen aber an einer
Engstelle. Fuer die Redaktion sind beide Rollen relevant, aber unterschiedlich:
Burt-Broker sind wertvoll fuer Ideenzufluss, Betweenness-Broker sind ein
Ausfallrisiko. Wie gross dieses Risiko ist, quantifiziert 2.6.
"""))

cells.append(nbf.v4.new_code_cell("""# 2.2 Test 1A: Departmental Homophilie via Node-Label-Permutation (LE7)
r_obs = nx.attribute_assortativity_coefficient(G_collab, 'dominant_ressort')
print(f'Beobachteter Assortativitätskoeffizient r = {r_obs:.4f}')

# Nullmodell: Permutiere dominant_ressort Labels auf fixer Topologie (B = 5000)
np.random.seed(42)
B_PERM = 5000
nodes = list(G_collab.nodes())
labels = [G_collab.nodes[n]['dominant_ressort'] for n in nodes]
perm_r = np.zeros(B_PERM)

G_perm = G_collab.copy()
for b in range(B_PERM):
    shuffled = np.random.permutation(labels)
    for i, n in enumerate(nodes):
        G_perm.nodes[n]['dominant_ressort'] = shuffled[i]
    perm_r[b] = nx.attribute_assortativity_coefficient(G_perm, 'dominant_ressort')

p_val_assort = (np.sum(perm_r >= r_obs) + 1) / (B_PERM + 1)
# Smallest p-value this permutation design can resolve
p_floor_assort = 1.0 / (B_PERM + 1)
p_txt_assort = (f'p < {p_floor_assort:.4f}' if p_val_assort <= p_floor_assort
                else f'p = {p_val_assort:.4f}')
print(f'Nullmodell (B={B_PERM}): Mean r_null = {perm_r.mean():.4f}, Std = {perm_r.std():.4f}')
print(f'Empirischer p-Wert: p = {p_val_assort:.5f}')

# Plot Permutation Distribution
plt.figure(figsize=(9, 5))
plt.hist(perm_r, bins=40, color='lightgray', edgecolor='black', alpha=0.7, density=True, label='Nullmodell (zufällige Ressortzuordnung)')
plt.axvline(r_obs, color='crimson', linestyle='--', linewidth=2.5, label=f'Beobachtetes r = {r_obs:.3f} ({p_txt_assort})')
plt.title(f'Hypothesentest 1A: Ressort-Homophilie (Newman r) vs. Permutations-Nullmodell (B={B_PERM})')
plt.xlabel('Assortativitätskoeffizient r')
plt.ylabel('Dichte')
plt.legend()
plt.tight_layout()
plt.savefig('out_plots/02_ressort_assortativity_permutation.png', dpi=300)
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 2, Ressort-Homophilie).** Der beobachtete
Assortativitaetskoeffizient von $r = 0.3630$ liegt weit ausserhalb der
Nullverteilung, die bei zufaelliger Ressortzuordnung um $-0.0062 \pm 0.0066$
streut. Der Abstand betraegt mehr als 50 Standardabweichungen, $p = 0.0002$ ist
der kleinste Wert, den 5'000 Permutationen aufloesen koennen.

Inhaltlich: Wer bei *20 Minuten* gemeinsam publiziert, tut das ganz
ueberwiegend innerhalb des eigenen Ressorts. Die Ressortgrenze ist damit keine
blosse Organigramm-Linie, sondern eine empirisch messbare Grenze der
tatsaechlichen Zusammenarbeit. $r = 0.36$ heisst zugleich, dass die Silos nicht
geschlossen sind: ein Wert nahe 1 waere vollstaendige Abschottung. Es gibt also
substanzielle ressortuebergreifende Zusammenarbeit, sie ist nur deutlich
seltener als ressortinterne. Abbildung 7 zeigt diese Silos unmittelbar: die Ressorts bilden im Layout
erkennbar eigene Farbinseln. Test 1C (2.4) prueft denselben Zusammenhang
dyadisch und mit einem strengeren Nullmodell.
"""))

cells.append(nbf.v4.new_code_cell("""# 2.3 Test 1B: Interdisziplinäre Kanten-JSD vs. Gradtreues Nullmodell (Maslov-Sneppen Rewiring)
obs_edge_jsd = [d['jsd'] for _, _, d in G_collab.edges(data=True)]
mean_jsd_obs = np.mean(obs_edge_jsd)
print(f'Beobachtete mittlere Kanten-JSD: {mean_jsd_obs:.4f}')

# Gradtreues Rewiring (Double-Edge-Swap)
np.random.seed(42)
B_REWIRE = 500
rewired_mean_jsd = np.zeros(B_REWIRE)

G_rewire = G_collab.copy()
for b in range(B_REWIRE):
    nx.double_edge_swap(G_rewire, nswap=G_rewire.number_of_edges(),
                        max_tries=G_rewire.number_of_edges() * 5, seed=b)
    jsd_vals = [
        compute_jsd(G_rewire.nodes[u]['ressort_distribution'], G_rewire.nodes[v]['ressort_distribution'])
        for u, v in G_rewire.edges()
    ]
    rewired_mean_jsd[b] = np.mean(jsd_vals)

p_val_jsd = (np.sum(rewired_mean_jsd <= mean_jsd_obs) + 1) / (B_REWIRE + 1)
p_floor_jsd = 1.0 / (B_REWIRE + 1)
p_txt_jsd = (f'p < {p_floor_jsd:.4f}' if p_val_jsd <= p_floor_jsd
             else f'p = {p_val_jsd:.4f}')
print(f'Gradtreues Nullmodell (Maslov-Sneppen): Mean JSD_null = {rewired_mean_jsd.mean():.4f}')
print(f'Empirischer p-Wert (geringere JSD als bei zufälligem Matching): p = {p_val_jsd:.5f}')

plt.figure(figsize=(9, 5))
plt.hist(rewired_mean_jsd, bins=30, color='skyblue', edgecolor='black', alpha=0.7, density=True, label='Gradtreues Nullmodell (Rewired Edges)')
plt.axvline(mean_jsd_obs, color='darkblue', linestyle='--', linewidth=2.5, label=f'Beobachtete Mean JSD = {mean_jsd_obs:.3f} ({p_txt_jsd})')
plt.title('Hypothesentest 1B: Interdisziplinäre Kanten-Divergenz (JSD) vs. Maslov-Sneppen Nullmodell')
plt.xlabel('Mittlere Jensen-Shannon-Divergenz (JSD)')
plt.ylabel('Dichte')
plt.legend()
plt.tight_layout()
plt.savefig('out_plots/03_edge_jsd_null_comparison.png', dpi=300)
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 3, Divergenz gegen ein gradtreues Nullmodell).**
Die mittlere Ressort-Divergenz entlang bestehender Kanten betraegt $0.3371$. Im
gradtreuen Nullmodell, das die Gradsequenz exakt erhaelt und nur die
Verknuepfung neu wuerfelt, liegt sie bei $0.6258$, also fast doppelt so hoch
($p = 0.0020$, die Aufloesungsgrenze bei 500 Rewirings).

Das ist der schaerfere der beiden Homophilie-Tests. Test 1A haette auch dann ein
Ergebnis geliefert, wenn hochaktive Autor:innen einfach mehr Kanten haben. Hier
bleibt die Gradsequenz unveraendert, der Unterschied kann also nicht aus der
Aktivitaetsverteilung stammen. Journalist:innen waehlen ihre Koautor:innen
gezielt nach thematischer Naehe, nicht bloss nach Verfuegbarkeit.

Die verbleibende Divergenz von $0.34$ ist dabei nicht null: es existiert ein
messbarer Anteil bewusst interdisziplinaerer Zusammenarbeit. Ob sich dieser
auch in der Leserresonanz niederschlaegt, prueft 2.5.
"""))

cells.append(nbf.v4.new_code_cell("""# 2.4 Test 1C: QAP - Dyadischer Hypothesentest auf Kantenmatrizen (LE7, Skript Kap. 11)
# Tests 1A und 1B permutieren Knotenlabels bzw. die Topologie. Der QAP-Test
# arbeitet dagegen direkt auf zwei Kantenmatrizen und permutiert Knotenlabels
# GEMEINSAM auf Zeilen und Spalten. Nur so bleibt die netzwerkinterne
# Abhaengigkeitsstruktur erhalten, die eine gewoehnliche Korrelation verletzt.

# Analyse auf der Giant Connected Component, da Matrizen ueber isolierte Knoten
# nur Nullzeilen beitragen wuerden.
gcc_nodes_collab = sorted(max(nx.connected_components(G_collab), key=len))
G_gcc_collab = G_collab.subgraph(gcc_nodes_collab).copy()
qap_node_order = sorted(G_gcc_collab.nodes())
print(f'QAP-Grundlage: GCC mit {len(qap_node_order)} Autor:innen, {G_gcc_collab.number_of_edges()} Kanten')

# Matrix A: Kollaborationsstaerke (Newman-Gewicht)
M_weight = edge_matrix_from_edge_attribute(G_gcc_collab, qap_node_order, 'weight')
# Matrix B: gleiches dominantes Ressort? (Knotenattribut auf Kanten projiziert
# -> gemischter monadisch-dyadischer Hypothesentest gemaess LE7)
M_same_ressort = edge_matrix_from_node_attribute(G_gcc_collab, qap_node_order, 'dominant_ressort')
# Matrix C: Ressort-Divergenz ueber ALLE Dyaden, nicht nur ueber Kanten.
# Eine reine Kanten-Matrix waere fuer nicht benachbarte Paare null und die
# Korrelation wuerde teilweise blosse Kanten-Kopraesenz messen statt des
# inhaltlichen Zusammenhangs.
M_jsd = jsd_matrix_from_profiles(G_gcc_collab, qap_node_order)

B_QAP = 2000

# H1: Kollaborationen sind staerker zwischen Personen desselben Ressorts
qap_weight_ressort = qap_correlation_test(M_weight, M_same_ressort, n_perm=B_QAP, seed=42)
print(f\"\\nQAP 1: Kollaborationsgewicht ~ gleiches Ressort\")
print(f\"  r = {qap_weight_ressort['r_observed']:.4f}, p = {qap_weight_ressort['p_value']:.5f} \"
      f\"(Nullverteilung: {qap_weight_ressort['null_mean']:.4f} +/- {qap_weight_ressort['null_std']:.4f})\")

# H2: Je staerker die Kollaboration, desto aehnlicher die Ressort-Profile
# Erwartung bei Homophilie: negative Korrelation (starke Kollaboration bei
# geringer Profil-Divergenz). Daher zweiseitig getestet.
qap_weight_jsd = qap_correlation_test(M_weight, M_jsd, n_perm=B_QAP, seed=42, alternative='two-sided')
print(f\"\\nQAP 2: Kollaborationsgewicht ~ Ressort-Divergenz (JSD)\")
print(f\"  r = {qap_weight_jsd['r_observed']:.4f}, p = {qap_weight_jsd['p_value']:.5f} \"
      f\"(Nullverteilung: {qap_weight_jsd['null_mean']:.4f} +/- {qap_weight_jsd['null_std']:.4f})\")

# Visualisierung der QAP-Nullverteilung
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
for ax, res, lbl in [
    (axes[0], qap_weight_ressort, 'Kollaborationsgewicht ~ gleiches Ressort'),
    (axes[1], qap_weight_jsd, 'Kollaborationsgewicht ~ JSD')
]:
    p_floor = 1.0 / (res['n_perm'] + 1)
    p_txt = f\"p < {p_floor:.4f}\" if res['p_value'] <= p_floor else f\"p = {res['p_value']:.4f}\"
    ax.hist(res['null_distribution'], bins=40, color='lightgray', edgecolor='black',
            alpha=0.75, density=True, label=f\"QAP-Nullmodell (B={res['n_perm']})\")
    ax.axvline(res['r_observed'], color='crimson', linestyle='--', linewidth=2.5,
               label=f\"Beobachtet r = {res['r_observed']:.3f} ({p_txt})\")
    ax.set_title(lbl, fontsize=11)
    ax.set_xlabel('Korrelationskoeffizient r')
    ax.set_ylabel('Dichte')
    ax.legend(fontsize=8)
plt.suptitle('Test 1C: QAP mit gemeinsamer Zeilen-/Spalten-Permutation der Knotenlabels', y=1.03)
plt.tight_layout()
plt.savefig('out_plots/04_qap_null_distributions.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell('''**Interpretation (Abbildung 4, Test 1C: QAP).** Der QAP-Test bestaetigt die Ressort-Homophilie
aus Test 1A auf dyadischer Ebene und mit einem strengeren Nullmodell: die
gemeinsame Permutation von Zeilen und Spalten erhaelt die Netzwerkstruktur, so
dass die Signifikanz nicht aus der blossen Autokorrelation der Adjazenzmatrix
stammt. Fuer die Redaktion bedeutet das: Kollaborationen entstehen nicht
zufaellig ueber Ressortgrenzen hinweg, sondern folgen der redaktionellen
Ressortstruktur. Der zweite Test prueft die Gegenrichtung, naemlich ob starke
Kollaborationen mit inhaltlich aehnlicheren Profilen einhergehen.'''))

cells.append(nbf.v4.new_code_cell("""# 2.5 Sekundäre Assoziationsanalyse: Leave-One-Out JSD vs. Leser-Shares (OLS)
# Die JSD für Artikel k wird aus Autorenprofilen berechnet, aus denen Artikel k
# zuvor entfernt wurde. Ohne diesen Schritt ist der Artikel in seinem eigenen
# Prädiktor enthalten (Leakage).
author_profiles = compute_author_ressort_profiles(df)
loo_jsd_by_article = compute_leave_one_out_jsd(df, author_profiles)
print(f'Leave-One-Out JSD berechnet für {len(loo_jsd_by_article)} Mehrautoren-Artikel')

multi_art_records = []
n_skipped = 0
for _, row in multi_df.iterrows():
    auths = [a for a in row['authors_clean'] if a in author_profiles]
    if len(auths) < 2:
        continue

    # Artikel, bei denen ein Koautor nach Entfernung kein Profil mehr hat,
    # sind hier nicht definiert und werden ausgeschlossen.
    mean_jsd = loo_jsd_by_article.get(row['article_id'])
    if mean_jsd is None:
        n_skipped += 1
        continue

    multi_art_records.append({
        'article_id': row['article_id'],
        'year': str(row['year']),
        'ressort': row['ressort'],
        'team_size': len(auths),
        'mean_jsd': mean_jsd,
        'shares': row['shares'],
        'log_shares': np.log1p(row['shares']),
        'log_comments': np.log1p(row['kommentare']),
        'likes': row['likes']
    })

print(f'Ausgeschlossen (Koautor ohne verbleibende Artikel): {n_skipped}')
art_reg_df = pd.DataFrame(multi_art_records)

# OLS Regression mit Kontrollvariablen für Jahr, Ressort und Teamgrösse
# Fehlende Shares sind seit der Bereinigung NaN statt 0. statsmodels entfernt
# solche Zeilen still, deshalb wird der Verlust hier explizit ausgewiesen.
n_before = len(art_reg_df)
reg_cols = ['log_shares', 'mean_jsd', 'team_size', 'year', 'ressort']
art_reg_clean = art_reg_df.dropna(subset=reg_cols)
n_dropped = n_before - len(art_reg_clean)

model = smf.ols('log_shares ~ mean_jsd + team_size + C(year) + C(ressort)',
                data=art_reg_clean).fit(cov_type='HC3')

print('OLS-Regressionsergebnisse (Abhängige Variable: log(1 + shares)):')
print(f'  Beobachtungen N          : {int(model.nobs):,} von {n_before:,} '
      f'({n_dropped:,} wegen fehlender Werte ausgeschlossen)')
print(f'  R-squared                : {model.rsquared:.4f}')
print(f'  Adj. R-squared           : {model.rsquared_adj:.4f}')
print(f'  F-Statistik (HC3), p     : {model.fvalue:.2f}, p = {model.f_pvalue:.3g}')
print(f'  Koeffizient mean_jsd     : {model.params["mean_jsd"]:.4f} '
      f'(p = {model.pvalues["mean_jsd"]:.4f}, 95%-KI '
      f'[{model.conf_int().loc["mean_jsd", 0]:.4f}, {model.conf_int().loc["mean_jsd", 1]:.4f}])')
print()
print(model.summary().tables[1])

# Visualisierung
plt.figure(figsize=(9, 5))
sns.regplot(
    data=art_reg_clean.sample(min(2000, len(art_reg_clean)), random_state=42),
    x='mean_jsd', y='log_shares',
    scatter_kws={'alpha': 0.2, 'color': 'gray', 's': 20},
    line_kws={'color': 'crimson', 'linewidth': 2}
)
plt.title('Sekundäre Assoziation: Interdisziplinäre Kanten-Divergenz (JSD) vs. log(1 + Shares)')
plt.xlabel('Team-Mittelwert der Leave-One-Out Jensen-Shannon-Divergenz (JSD)')
plt.ylabel('log(1 + Shares)')
plt.tight_layout()
plt.savefig('out_plots/05_jsd_shares_regression.png', dpi=300)
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 5, thematische Breite und Leserresonanz).** Das
Modell erklaert 35.5% der Varianz von $\log(1 + \text{Shares})$ ($N = 6'887$,
adj. $R^2 = 0.353$), bei Kontrolle von Jahr, Ressort und Teamgroesse.

Der Koeffizient von `mean_jsd` ist mit $0.61$ positiv und klar signifikant
($p < 0.001$, 95%-KI $[0.45, 0.76]$). Artikel, deren Autor:innen aus
thematisch *unterschiedlichen* Ecken der Redaktion kommen, werden also im Mittel
haeufiger geteilt. Da die JSD leave-one-out berechnet ist, stammt dieser
Zusammenhang nicht aus dem Artikel selbst.

Zwei Einschraenkungen sind wichtig. Erstens ist das eine Assoziation, keine
Kausalitaet: interdisziplinaere Teams werden womoeglich gerade fuer die
groesseren, aufwendigeren Geschichten zusammengestellt, und diese werden
ohnehin mehr geteilt. Zweitens sind Shares ein Momentwert zum Scraping-
Zeitpunkt. Der Befund ergaenzt 2.3 jedoch sinnvoll: ressortuebergreifende
Zusammenarbeit ist selten, aber wenn sie stattfindet, erreicht sie mehr
Leser:innen.
"""))

# Chapter 3: Pillar 2
cells.append(nbf.v4.new_code_cell("""# 2.6 Kohaesion & strukturelle Robustheit: Cliquen, k-Core, Cut-Vertices (LE4/LE6, Kap. 5.2 & 9)
coh = analyze_cohesion_and_connectivity(G_collab, top_k=10)

print('=== KOMPONENTENSTRUKTUR ===')
print(f"Komponenten insgesamt: {coh['n_components']}")
print(f"Giant Component: {coh['gcc_nodes']} Knoten ({coh['gcc_share']:.1%} aller Autor:innen), {coh['gcc_edges']} Kanten")
print(f"Isolierte Autor:innen (nie im Team publiziert): {coh['n_isolates']}")

print('\\n=== KOHAESIVE SUBGRUPPEN ===')
print(f"Maximale Cliquen: {coh['n_maximal_cliques']:,}")
print(f"Cliquenzahl (groesste vollstaendig verbundene Gruppe): {coh['clique_number']}")
print(f"Mitglieder der groessten Clique: {', '.join(coh['largest_clique_members'])}")
print(f"Hoechste k-Core-Zahl: {coh['max_core_number']} (Main Core: {coh['main_core_size']} Autor:innen)")

print('\\n=== STRUKTURELLE ROBUSTHEIT (auf der Giant Component) ===')
print(f"Knoten-Konnektivitaet: {coh['node_connectivity']}")
print(f"Kanten-Konnektivitaet: {coh['edge_connectivity']}")
print(f"Artikulationspunkte (Cut-Vertices): {coh['n_articulation_points']}")
print(f"Bruecken (Bridges): {coh['n_bridges']}")

cut_df = pd.DataFrame(coh['top_cut_vertices'])
print('\\nKritischste Autor:innen (Entfernung spaltet die meisten Knoten ab):')
print(cut_df[['node', 'ressort', 'degree', 'components_after_removal', 'nodes_split_off']].to_string(index=False))

core_counts = Counter(coh['core_numbers'].values())
fig, axes = plt.subplots(1, 2, figsize=(14, 4.5))
ks = sorted(core_counts)
axes[0].bar(ks, [core_counts[k] for k in ks], color='steelblue', edgecolor='black')
axes[0].set_title(f"k-Core-Verteilung der Giant Component (max. k = {coh['max_core_number']})")
axes[0].set_xlabel('k-Core-Zahl'); axes[0].set_ylabel('Anzahl Autor:innen')

cs = sorted(coh['clique_size_distribution'])
axes[1].bar(cs, [coh['clique_size_distribution'][s] for s in cs], color='darkseagreen', edgecolor='black')
axes[1].set_title(f"Groessenverteilung der {coh['n_maximal_cliques']:,} maximalen Cliquen")
axes[1].set_xlabel('Cliquengroesse'); axes[1].set_ylabel('Anzahl Cliquen')
axes[1].set_yscale('log')
plt.suptitle('Kohaesion und Robustheit des Autoren-Kollaborationsnetzwerks', y=1.03)
plt.tight_layout()
plt.savefig('out_plots/06_cohesion_kcore_cliques.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 6 und 8, Kohaesion und Robustheit).** Die Zahlen beschreiben eine
Redaktion mit einem dichten Kern und einer breiten Peripherie: ein grosser Teil
der Autor:innen publiziert nie im Team und bleibt isoliert, waehrend der
verbundene Kern einen hohen k-Core aufweist, also eine Gruppe, in der jede
Person mit vielen anderen derselben Gruppe zusammenarbeitet.

Redaktionell relevanter ist die Robustheit. Die Knoten-Konnektivitaet der Giant
Component betraegt 1. Es genuegt also der Ausfall einer einzigen Person, um den
verbundenen Teil der Redaktion in mehrere Teile zu zerlegen. Die oben
gelisteten Artikulationspunkte sind damit keine blosse Graph-Eigenschaft,
sondern konkrete Schluesselpersonen: faellt eine von ihnen aus, etwa durch
Kuendigung oder laengere Abwesenheit, bricht die Zusammenarbeit zwischen ganzen
Teilgruppen ab. Das ergaenzt die Brokerage-Analyse aus 2.1. Dort ging es darum,
wer Informationen vermittelt, hier darum, wessen Wegfall die Struktur
zerreisst."""))

cells.append(nbf.v4.new_code_cell("""# 2.7 Visualisierung des Kollaborationsnetzwerks (Kriterium 4)
# Zwei Perspektiven auf denselben Graphen: die Ressort-Homophilie sichtbar
# gemacht, und die strukturell kritischen Knoten hervorgehoben.
os.makedirs('out_plots', exist_ok=True)

btw_gcc = nx.betweenness_centrality(G_gcc_collab, weight='distance', normalized=True)

draw_network(
    G_gcc_collab,
    'out_plots/07_author_network_ressort.png',
    color_by='dominant_ressort',
    size_by=btw_gcc,
    label_top_n=8,
    title=f'Autoren-Kollaborationsnetzwerk (Giant Component, {G_gcc_collab.number_of_nodes()} Autor:innen)\\n'
          f'Farbe = dominantes Ressort, Groesse = Betweenness-Zentralitaet',
    legend_title='Dominantes Ressort'
)

core_num = coh['core_numbers']
critical = [d['node'] for d in coh['top_cut_vertices']]
draw_network(
    G_gcc_collab,
    'out_plots/08_author_network_connectivity.png',
    size_by={n: core_num.get(n, 0) for n in G_gcc_collab.nodes()},
    highlight_nodes=critical,
    label_nodes=critical[:6],
    node_size_range=(8, 190),
    edge_alpha=0.22,
    title=f"Strukturelle Robustheit: Groesse = k-Core-Zahl, rot umrandet und beschriftet = kritischste Artikulationspunkte\\n"
          f"Knoten-Konnektivitaet der Giant Component = {coh['node_connectivity']}, "
          f"{coh['n_articulation_points']} Artikulationspunkte, {coh['n_bridges']} Bruecken"
)

# Inline anzeigen, damit die Abbildungen im Notebook selbst sichtbar sind und
# nicht nur als Datei auf der Platte liegen.
from IPython.display import Image, display
print('Abbildung 7: Kollaborationsnetzwerk nach dominantem Ressort')
display(Image('out_plots/07_author_network_ressort.png', width=1000))
print('Abbildung 8: Strukturelle Robustheit und Artikulationspunkte')
display(Image('out_plots/08_author_network_connectivity.png', width=1000))
"""))

cells.append(nbf.v4.new_markdown_cell("""## 3. Pfeiler 2: Makro-Topologie & Krisen-Evolution der Berichterstattung 2020–2024 (LE4, LE6)

### Methodik & Hypothesenprüfung
- **Einheitliches Vokabular:** Top 1'200 bereinigte Substantive über den gesamten Zeitraum 2020–2024 garantieren identische Knotenmengen.
- **Topologische Sparsifizierung:** Gegenseitige k-Nächste-Nachbarn (Mutual $k$-NN, $k=10$). Die Sensitivitätsprüfung über $k \in \{5, 10, 20\}$ erfolgt in Abschnitt 3.2, die Konsequenzen für Hypothese 2 in 3.4.
- **Riesenzusammenhangskomponente (Giant Component):** Alle Pfadlängen und Zentralisierungen werden auf der GCC berechnet (Distanztransformation $d = 1/w$).
- **Louvain Modularity ($Q$):** Stabilitätstest über 10 Zufalls-Seeds pro Jahr.
"""))

cells.append(nbf.v4.new_code_cell("""# 3.1 Longitudinale Makro-Metriken der Keyword-Netzwerke 2020-2024 (LE6)
import community as community_louvain

vocab = extract_global_vocabulary(df, top_n=1200)
years = [2020, 2021, 2022, 2023, 2024]
annual_metrics = []

for yr in years:
    df_yr = df[df['year'] == yr]
    G_yr = build_annual_keyword_graph(df_yr, vocab, k=10)
    
    # Giant Connected Component
    gcc_nodes = max(nx.connected_components(G_yr), key=len)
    G_gcc = G_yr.subgraph(gcc_nodes).copy()
    
    # Global Metrics
    n_nodes = G_yr.number_of_nodes()
    gcc_ratio = len(G_gcc) / n_nodes
    avg_deg = np.mean([d for _, d in G_yr.degree()])
    
    # Normalized Freeman Degree Centralization
    degs = np.array([d for _, d in G_yr.degree()])
    max_d = degs.max()
    c_d = np.sum(max_d - degs) / ((n_nodes - 1) * (n_nodes - 2))
    
    # Clustering & Path Length on GCC
    avg_clustering = nx.average_clustering(G_gcc, weight='weight')
    avg_path_length = nx.average_shortest_path_length(G_gcc, weight='distance')
    
    # Betweenness-Zentralisierung C_B (im Meilenstein zugesagt, zuvor fehlend)
    c_b = betweenness_centralization(G_gcc, weight='distance')

    # Louvain Modularity over 10 seeds
    q_seeds = []
    partitions = []
    for seed in range(10):
        part = community_louvain.best_partition(G_yr, weight='weight', random_state=seed)
        q_seeds.append(community_louvain.modularity(part, G_yr, weight='weight'))
        partitions.append(part)

    # Metriken, die das Design tatsaechlich variieren LAESST.
    # C_D und Q sind durch die Mutual-k-NN-Sparsifizierung stark eingeschnuert
    # (siehe Sensitivitaetsanalyse unten). Der Anteil der groessten Community
    # und die Entropie der Community-Groessen sind es nicht: sie messen, wie
    # stark sich die Berichterstattung auf einen Themenblock konzentriert.
    ref_part = partitions[0]
    sizes = np.array(list(Counter(ref_part.values()).values()), dtype=float)
    shares = sizes / sizes.sum()
    largest_community_share = float(shares.max())
    community_entropy = float(-np.sum(shares * np.log(shares)))
    n_communities = int(len(sizes))

    annual_metrics.append({
        'year': yr,
        'articles': len(df_yr),
        'nodes': n_nodes,
        'edges': G_yr.number_of_edges(),
        'gcc_ratio': gcc_ratio,
        'avg_degree': avg_deg,
        'degree_centralization': c_d,
        'betweenness_centralization': c_b,
        'avg_clustering': avg_clustering,
        'avg_path_length': avg_path_length,
        'modularity_mean': np.mean(q_seeds),
        'modularity_std': np.std(q_seeds),
        'n_communities': n_communities,
        'largest_community_share': largest_community_share,
        'community_entropy': community_entropy
    })

macro_df = pd.DataFrame(annual_metrics)
print('Makro-Topologische Entwicklung 2020-2024:')
print(macro_df.round(4).to_string())

# Wie viel Spielraum laesst das Design ueberhaupt?
C_D_BOUND = max_possible_degree_centralization(1200, 10)
print(f'\\nStrukturelle Obergrenze von C_D bei n=1200 und Grad-Cap k=10: {C_D_BOUND:.4f}')
print(f'Beobachteter Bereich von C_D: {macro_df["degree_centralization"].min():.4f} '
      f'bis {macro_df["degree_centralization"].max():.4f} '
      f'({macro_df["degree_centralization"].max() / C_D_BOUND:.1%} der Obergrenze)')
print(f'Beobachteter Bereich von Q:   {macro_df["modularity_mean"].min():.4f} '
      f'bis {macro_df["modularity_mean"].max():.4f}')
print(f'Beobachteter Bereich des groessten Community-Anteils: '
      f'{macro_df["largest_community_share"].min():.4f} bis {macro_df["largest_community_share"].max():.4f}')

# Multi-panel Trajectory Plot
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Degree Centralization
axes[0, 0].plot(macro_df['year'], macro_df['degree_centralization'], marker='o', color='crimson', linewidth=2.5)
axes[0, 0].set_title('Normalisierte Degree Centralization C_D')
axes[0, 0].set_xlabel('Jahr')
axes[0, 0].set_ylabel('C_D')

# 2. Modularity Q
axes[0, 1].errorbar(macro_df['year'], macro_df['modularity_mean'], yerr=macro_df['modularity_std'], marker='s', color='navy', linewidth=2.5, capsize=4)
axes[0, 1].set_title('Louvain Modularity Q (Mean ± Std, 10 Seeds)')
axes[0, 1].set_xlabel('Jahr')
axes[0, 1].set_ylabel('Modularität Q')

# 3. Average Path Length
axes[1, 0].plot(macro_df['year'], macro_df['avg_path_length'], marker='^', color='forestgreen', linewidth=2.5)
axes[1, 0].set_title('Charakteristische Pfadlänge L (GCC)')
axes[1, 0].set_xlabel('Jahr')
axes[1, 0].set_ylabel('Mittlere Distanz')

# 4. Giant Component Ratio
axes[1, 1].plot(macro_df['year'], macro_df['gcc_ratio'], marker='D', color='purple', linewidth=2.5)
axes[1, 1].set_title('Anteil der Riesenzusammenhangskomponente (GCC)')
axes[1, 1].set_xlabel('Jahr')
axes[1, 1].set_ylabel('|V_GCC| / |V|')

plt.suptitle('Pfeiler 2: Longitudinale Netzwerktopologie des News-Agendas 2020–2024', y=1.02, fontsize=15)
plt.tight_layout()
plt.savefig('out_plots/09_temporal_metrics_trajectories.png', dpi=300)
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 9 und Tabelle 3.1, makro-topologische Entwicklung).** Ueber alle
fuenf Jahre bleibt die Struktur des Themennetzwerks bemerkenswert konstant: die
Riesenkomponente umfasst durchgehend 98.7% bis 99.5% der 1'200 Begriffe, der
mittlere Grad liegt zwischen 6.34 und 6.59, die Modularitaet zwischen 0.772 und
0.790. Die Berichterstattung ist also in jedem Jahr aehnlich stark
ausdifferenziert, unabhaengig davon, welche Themen dominieren.

Das ist zunaechst ein Konstanzbefund, kein Wandelbefund: *was* berichtet wird,
aendert sich (siehe 3.3 und 3.5), *wie* sich die Themen strukturell zueinander
verhalten, kaum. Wie viel dieser Konstanz allerdings auf das Messverfahren
zurueckgeht, klaert die Sensitivitaetsanalyse in 3.2; die Konsequenz fuer
Hypothese 2 folgt in 3.4.
"""))

cells.append(nbf.v4.new_code_cell("""# 3.2 Sensitivitaetsanalyse der Sparsifizierung: k in {5, 10, 20} (LE6)
# Die Methodik sagt eine Pruefung ueber mehrere k zu. Sie zeigt zugleich, wie
# stark der gewaehlte Grad-Cap die Kennzahlen von vornherein einschnuert.
sens_rows = []
for k_val in [5, 10, 20]:
    bound_k = max_possible_degree_centralization(1200, k_val)
    for yr in years:
        G_k = build_annual_keyword_graph(df[df['year'] == yr], vocab, k=k_val)
        gcc_k = G_k.subgraph(sorted(max(nx.connected_components(G_k), key=len))).copy()
        part_k = community_louvain.best_partition(G_k, weight='weight', random_state=0)
        sizes_k = np.array(list(Counter(part_k.values()).values()), dtype=float)
        sens_rows.append({
            'k': k_val,
            'year': yr,
            'edges': G_k.number_of_edges(),
            'avg_degree': float(np.mean([d for _, d in G_k.degree()])),
            'C_D': degree_centralization(G_k),
            'C_D_max_moeglich': bound_k,
            'C_D_Ausschoepfung': degree_centralization(G_k) / bound_k,
            # C_B traegt in 3.4 die Aussage zu Hypothese 2 und muss daher
            # ueber k mitgeprueft werden, nicht nur bei k = 10.
            'C_B': betweenness_centralization(gcc_k, weight='distance'),
            'Q': community_louvain.modularity(part_k, G_k, weight='weight'),
            'groesste_community': float(sizes_k.max() / sizes_k.sum())
        })

sens_df = pd.DataFrame(sens_rows)
print('Sensitivitaetsanalyse ueber k (Mutual k-NN):')
print(sens_df.round(4).to_string(index=False))

print('\\nMittelwerte je k:')
print(sens_df.groupby('k')[['edges', 'avg_degree', 'C_D', 'C_D_max_moeglich',
                            'C_B', 'Q', 'groesste_community']].mean().round(4).to_string())

# Robustheit der Jahres-Extrema ueber k: das ist die eigentliche Frage der
# Sensitivitaetsanalyse, nicht das absolute Niveau.
print('\\nRobustheit der Jahres-Extrema ueber k:')
for col, want_year, mode in [('C_D', 2020, 'max'), ('C_B', 2020, 'max'),
                             ('Q', 2020, 'min'), ('groesste_community', 2020, 'max')]:
    years_hit = []
    for k_val in [5, 10, 20]:
        sub = sens_df[sens_df['k'] == k_val].set_index('year')[col]
        years_hit.append(int(sub.idxmax() if mode == 'max' else sub.idxmin()))
    stable = len(set(years_hit)) == 1
    consistent = all(y == want_year for y in years_hit)
    print(f'  {col:<20} {mode}-Jahr bei k=5/10/20: {years_hit}  '
          f'-> {"stabil" if stable else "instabil"}'
          f'{", entspricht der Erwartung 2020" if consistent else ""}')

fig, axes = plt.subplots(1, 4, figsize=(19, 4.3))
for k_val, marker in zip([5, 10, 20], ['o', 's', '^']):
    sub = sens_df[sens_df['k'] == k_val]
    axes[0].plot(sub['year'], sub['C_D'], marker=marker, label=f'k = {k_val}')
    axes[1].plot(sub['year'], sub['C_B'], marker=marker, label=f'k = {k_val}')
    axes[2].plot(sub['year'], sub['Q'], marker=marker, label=f'k = {k_val}')
    axes[3].plot(sub['year'], sub['groesste_community'], marker=marker, label=f'k = {k_val}')
axes[0].set_title('Degree-Zentralisierung $C_D$'); axes[0].set_ylabel('$C_D$')
axes[1].set_title('Betweenness-Zentralisierung $C_B$'); axes[1].set_ylabel('$C_B$')
axes[2].set_title('Louvain-Modularitaet $Q$'); axes[2].set_ylabel('$Q$')
axes[3].set_title('Anteil der groessten Community'); axes[3].set_ylabel('Anteil')
for ax in axes:
    ax.set_xlabel('Jahr'); ax.legend(fontsize=8); ax.set_xticks(years)
plt.suptitle('Abbildung 10: Sensitivitaet der Makro-Kennzahlen gegenueber dem Sparsifizierungsparameter k', y=1.04)
plt.tight_layout()
plt.savefig('out_plots/10_sensitivity_k.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 10, Sensitivitaet und Grenzen des Designs).**

Die Sensitivitaetsanalyse beantwortet zwei Fragen.

*Wie stabil sind die Befunde?* Die absoluten Niveaus haengen erwartungsgemaess
stark an $k$: von $k=5$ zu $k=20$ steigt die mittlere Kantenzahl von rund 1'654
auf 8'735, $Q$ faellt von 0.908 auf 0.656, $C_D$ steigt von 0.0019 auf 0.0045.
Entscheidend ist deshalb nicht das Niveau, sondern ob die *Jahres-Extrema*
ueber $k$ gleich bleiben. Die Auswertung zeigt ein klares Muster:

- **$Q$ hat sein Minimum bei allen drei $k$-Werten im Jahr 2020**
  (0.8952 bei $k=5$, 0.7702 bei $k=10$, 0.6427 bei $k=20$). Das ist ein
  robuster Befund und stuetzt genau die Richtung, die der Meilenstein fuer die
  Modularitaet vorhergesagt hat.
- **$C_D$ hat sein Maximum bei allen drei $k$-Werten 2021**, also stabil, aber
  nicht im vorhergesagten Jahr.
- **$C_B$ ist nicht robust:** das Maximum liegt bei $k=5$ und $k=10$ in 2020,
  bei $k=20$ dagegen in 2023. Die Betweenness-Zentralisierung taugt damit
  nicht als tragende Evidenz, obwohl sie die groesste relative Spannweite hat.
- Der Anteil der groessten Community ist ebenfalls instabil (2022 / 2023 / 2021).

*Wie viel Spielraum laesst das Design?* Die Spalte `C_D_max_moeglich` zeigt,
dass die Mutual-$k$-NN-Sparsifizierung den Knotengrad bei $k$ deckelt und damit
auch $C_D$ nach oben begrenzt: bei $n = 1200$ liegt die Obergrenze fuer $k=5$
bei $0.0042$, fuer $k=10$ bei $0.0083$, fuer $k=20$ bei $0.0167$. Ausgeschoepft
werden davon nur 26% bis 46%. $C_D$ kann in diesem Design also gar nicht stark
variieren, unabhaengig davon, was in der Berichterstattung passiert.

*Hinweis zur Vergleichbarkeit mit 3.1:* Dort wird $Q$ als Mittel ueber zehn
Louvain-Seeds ausgewiesen (2020: 0.7720), hier aus Laufzeitgruenden als
Einzellauf mit festem Seed 0 (2020: 0.7702). Die Differenz von 0.002 liegt
innerhalb der in 3.1 berichteten Streuung von $\\pm 0.0014$ und ist kein
Widerspruch.

Die Konsequenz fuer Hypothese 2 wird in 3.4 diskutiert.
"""))

cells.append(nbf.v4.new_code_cell("""# 3.3 Thematische Louvain-Clusterung: 2020 (Covid-Peak) vs. 2024 (Normalisierung)
G_2020 = build_annual_keyword_graph(df[df['year'] == 2020], vocab, k=10)
G_2024 = build_annual_keyword_graph(df[df['year'] == 2024], vocab, k=10)

part_2020 = community_louvain.best_partition(G_2020, weight='weight', random_state=42)
part_2024 = community_louvain.best_partition(G_2024, weight='weight', random_state=42)

def get_top_cluster_terms(G, part, top_k_clusters=5, terms_per_cluster=6):
    cluster_nodes = defaultdict(list)
    for node, c_id in part.items():
        cluster_nodes[c_id].append(node)
    
    sorted_clusters = sorted(cluster_nodes.items(), key=lambda x: len(x[1]), reverse=True)[:top_k_clusters]
    out = []
    for c_id, nodes in sorted_clusters:
        sub_G = G.subgraph(nodes)
        top_terms = sorted(sub_G.degree(weight='weight'), key=lambda x: x[1], reverse=True)[:terms_per_cluster]
        term_str = ', '.join([t[0] for t in top_terms])
        out.append({'cluster_id': c_id, 'size': len(nodes), 'top_terms': term_str})
    return pd.DataFrame(out)

print('=== TOP LOUVAIN THEMEN-CLUSTER 2020 (Krisenjahr) ===')
print(get_top_cluster_terms(G_2020, part_2020).to_string())
print('')
print('=== TOP LOUVAIN THEMEN-CLUSTER 2024 (Normalisierung) ===')
print(get_top_cluster_terms(G_2024, part_2024).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abschnitt 3.3, Louvain-Cluster 2020 gegenueber 2024).** Der qualitative
Vergleich zeigt die thematische Umschichtung unmittelbar. 2020 bildet sich ein
grosser Cluster um `berset, corona, massnahmen, impfstoff, bundesrat`, also der
Pandemie-Komplex mit seiner politischen Steuerung. 2024 existiert dieser Cluster
nicht mehr. An seine Stelle treten Finanzthemen (`credit, ubs, milliarden`) und
der US-Wahlkampf (`trump, biden, harris, kamala`).

Bemerkenswert ist, was ueber beide Jahre stabil bleibt: Kriminalitaet und
Justiz, internationale Konflikte und Unterhaltung tauchen in beiden Jahren als
eigenstaendige Cluster auf. Die Struktur der Berichterstattung besteht also aus
einem stabilen Grundgeruest wiederkehrender Ressortthemen und einem
wechselnden Aktualitaetsblock, der 2020 von der Pandemie und 2024 von
Wirtschaft und Wahlkampf besetzt wird. Genau diese Trennung erklaert, warum die
globalen Kennzahlen in 3.1 so konstant sind, obwohl sich die Inhalte
grundlegend geaendert haben.
"""))

cells.append(nbf.v4.new_code_cell("""# 3.4 Hypothese 2: Pruefung gegen die Erwartung aus dem Meilenstein
# Erwartung laut Meilenstein: 2020 maximale Zentralisierung und minimale
# Modularitaet, danach sukzessive Dezentralisierung und staerkere modulare
# Ausdifferenzierung.
h2 = macro_df.set_index('year')

def _rank_statement(series, label, want_year, want='max'):
    best = series.idxmax() if want == 'max' else series.idxmin()
    hit = (best == want_year)
    print(f'  {label:<34} {want}: {best}  (erwartet {want_year})  -> '
          f'{"bestaetigt" if hit else "NICHT bestaetigt"}')
    return hit

print('Erwartung fuer 2020 (Krisenjahr):')
r1 = _rank_statement(h2['degree_centralization'], 'C_D maximal', 2020, 'max')
r2 = _rank_statement(h2['betweenness_centralization'], 'C_B maximal', 2020, 'max')
r3 = _rank_statement(h2['modularity_mean'], 'Modularitaet Q minimal', 2020, 'min')
r4 = _rank_statement(h2['largest_community_share'], 'groesste Community maximal', 2020, 'max')
r5 = _rank_statement(h2['community_entropy'], 'Community-Entropie minimal', 2020, 'min')

print('\\nSpannweite relativ zum Wertebereich:')
for col, lbl in [('degree_centralization', 'C_D'),
                 ('betweenness_centralization', 'C_B'),
                 ('modularity_mean', 'Q'),
                 ('largest_community_share', 'groesste Community'),
                 ('community_entropy', 'Community-Entropie')]:
    rng = h2[col].max() - h2[col].min()
    print(f'  {lbl:<22} min={h2[col].min():.4f}  max={h2[col].max():.4f}  Spannweite={rng:.4f}  '
          f'relativ={rng / h2[col].mean():.2%}')

print(f'\\nC_D schoepft maximal {h2["degree_centralization"].max() / C_D_BOUND:.1%} '
      f'der bei k=10 ueberhaupt moeglichen Zentralisierung aus.')

# Covid-Cluster-Masse: Anteil der Terme in Communities mit Pandemie-Vokabular
covid_terms = {'corona', 'coronavirus', 'covid', 'pandemie', 'impfung', 'impfstoff',
               'lockdown', 'massnahmen', 'virus', 'quarantaene', 'maske', 'booster'}
# Direktes Mass statt Cluster-Zugehoerigkeit: Anteil des gesamten Kantengewichts,
# das an Pandemie-Begriffen haengt. Ein Cluster-Anteil waere zu grob, weil ein
# einzelner Covid-Term eine ganze unverwandte Community mitzaehlen wuerde.
covid_mass = []
for yr in years:
    G_yr_c = build_annual_keyword_graph(df[df['year'] == yr], vocab, k=10)
    total_w = sum(d['weight'] for _, _, d in G_yr_c.edges(data=True))
    present = [n for n in G_yr_c.nodes() if n.lower() in covid_terms]
    covid_w = sum(d['weight'] for u, v, d in G_yr_c.edges(data=True)
                  if u.lower() in covid_terms or v.lower() in covid_terms)
    # Anteil der Artikel des Jahres, die mindestens einen Pandemie-Begriff tragen
    df_y = df[df['year'] == yr]
    art_share = float(np.mean([bool(covid_terms & {x.lower() for x in terms})
                               for terms in df_y['clean_terms_list']]))
    covid_mass.append({
        'year': yr,
        'covid_terme_im_vokabular': len(present),
        'anteil_kantengewicht': covid_w / total_w if total_w else 0.0,
        'anteil_artikel': art_share
    })
covid_df = pd.DataFrame(covid_mass)
print('\\nPraesenz des Pandemie-Vokabulars im Themennetzwerk:')
print(covid_df.round(4).to_string(index=False))
print(f"\\nRueckgang des Artikel-Anteils 2020 -> 2024: "
      f"{covid_df.iloc[0]['anteil_artikel']:.2%} auf {covid_df.iloc[-1]['anteil_artikel']:.2%} "
      f"(Faktor {covid_df.iloc[0]['anteil_artikel'] / max(covid_df.iloc[-1]['anteil_artikel'], 1e-9):.1f})")
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Hypothese 2: die Modularitaets-Haelfte ist robust bestaetigt, die Zentralisierungs-Haelfte nicht).**

Der Meilenstein erwartete fuer 2020 *maximale Zentralisierung und minimale
Modularitaet*. Nach der Sensitivitaetspruefung in 3.2 laesst sich das trennen:

**Bestaetigt und robust:** Die Modularitaet $Q$ hat ihr Minimum bei *allen drei*
getesteten $k$-Werten im Jahr 2020. Im Pandemiejahr war das Themennetzwerk also
tatsaechlich am schlechtesten in eigenstaendige Cluster zerlegbar, genau wie
vorhergesagt, und dieser Befund haengt nicht am Sparsifizierungsparameter. Das
ist die inhaltlich zentrale Bestaetigung: verschiedenste Themenfelder liefen im
Pandemie-Komplex zusammen.

**Nicht bestaetigt:** Die Degree-Zentralisierung $C_D$ erreicht ihr Maximum
stabil 2021, nicht 2020. Die Betweenness-Zentralisierung $C_B$ liegt bei
$k=5$ und $k=10$ zwar in 2020, bei $k=20$ jedoch in 2023, ist also **nicht
robust** und trägt die Aussage nicht. Damit bleibt die Zentralisierungs-Haelfte
der Hypothese unbelegt.

**Warum die Zentralisierungsmasse hier wenig leisten koennen.** Die
Mutual-$k$-NN-Sparsifizierung deckelt jeden Knotengrad bei $k = 10$ und
begrenzt $C_D$ bei $n = 1200$ rechnerisch auf rund $0.0083$; ausgeschoepft
werden davon 36.6%. Die relative Spannweite von $C_D$ ueber fuenf Jahre
betraegt 7.1%, jene von $Q$ 2.2%. Ein Mass, das konstruktionsbedingt kaum
variieren kann, taugt nur eingeschraenkt als Test einer Hypothese ueber
Variation. Die Sparsifizierung war notwendig, um Jahre mit unterschiedlicher
Artikelzahl vergleichbar zu machen; sie erkauft diese Vergleichbarkeit mit dem
Verlust genau jener Varianz, auf die die Zentralisierungs-Haelfte von
Hypothese 2 zielte.

**Wo der Pandemie-Effekt unmittelbar sichtbar wird.** Nicht in den globalen
Topologiemassen, sondern in der Praesenz des Vokabulars selbst: 19.45% aller
Artikel des Jahres 2020 tragen Pandemie-Begriffe, 2024 sind es 1.21%, ein
Rueckgang um den Faktor 16. Der Anteil des Kantengewichts an diesen Begriffen
faellt von 2.00% auf 1.34%. Zusammen mit dem robusten $Q$-Minimum ergibt das
ein konsistentes Bild: 2020 war thematisch stark konzentriert und strukturell
schlecht separierbar.

**Konsequenz fuer eine Fortfuehrung.** Fuer Zentralisierungsvergleiche ueber
Zeit waere ein Schwellenwert-Graph ohne Grad-Cap noetig, dessen Dichte pro Jahr
separat kontrolliert wird. Rueckblickend war die Zentralisierungs-Haelfte von
Hypothese 2 gegenueber dem gewaehlten Sparsifizierungsverfahren nicht
trennscharf formuliert. Das ist der wichtigste methodische Befund dieses
Pfeilers.
"""))

cells.append(nbf.v4.new_code_cell("""# 3.5 Visualisierung der semantischen Keyword-Netzwerke 2020 vs. 2024
# Farbe = Louvain-Cluster, Groesse = gewichteter Grad. Der visuelle Vergleich
# macht die thematische Umschichtung zwischen Krisen- und Normaljahr sichtbar.
for G_kw, part_kw, jahr in [(G_2020, part_2020, 2020), (G_2024, part_2024, 2024)]:
    G_plot = G_kw.copy()
    nx.set_node_attributes(G_plot, {n: f'Cluster {part_kw[n]}' for n in G_plot.nodes()}, 'cluster')
    deg_w = dict(G_plot.degree(weight='weight'))
    # Nur die groessten Cluster einfaerben, der Rest bleibt als 'Uebrige' zusammengefasst
    top_clusters = [f'Cluster {c}' for c, _ in Counter(part_kw.values()).most_common(10)]
    for n in G_plot.nodes():
        if G_plot.nodes[n]['cluster'] not in top_clusters:
            G_plot.nodes[n]['cluster'] = 'Uebrige'
    draw_network(
        G_plot,
        f'out_plots/{11 if jahr == 2020 else 12}_keyword_network_{jahr}.png',
        color_by='cluster',
        size_by=deg_w,
        label_top_n=12,
        title=f'Semantisches Keyword-Kookkurrenz-Netzwerk {jahr} '
              f'({G_plot.number_of_nodes()} Begriffe, {G_plot.number_of_edges()} Kanten)\\n'
              f'Farbe = Louvain-Cluster, Groesse = gewichteter Grad',
        legend_title='Louvain-Cluster',
        edge_alpha=0.10
    )
    fig_no = 11 if jahr == 2020 else 12
    print(f'Abbildung {fig_no}: Semantisches Keyword-Netzwerk {jahr}')
    display(Image(f'out_plots/{fig_no}_keyword_network_{jahr}.png', width=1000))
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildungen 11 und 12, semantische Netzwerke).** Der Vergleich der beiden Jahre
zeigt die thematische Umschichtung der Berichterstattung unmittelbar: 2020 bildet
sich ein grosser, dicht verbundener Pandemie-Cluster, der 2024 vollstaendig
verschwunden ist und durch Finanz- und Wahlkampfthemen ersetzt wurde. Da beide
Netzwerke ueber ein fixiertes globales Vokabular und dieselbe Mutual-k-NN-
Sparsifizierung gebildet wurden, ist der Unterschied nicht auf abweichende
Netzwerkdichten oder Artikelzahlen zurueckzufuehren, sondern auf tatsaechlich
veraenderte Kookkurrenzmuster."""))

cells.append(nbf.v4.new_code_cell("""# 3.6 Export der Graphen nach GEXF für Gephi
# export_graph_gexf konvertiert numpy-Attribute (u.a. ressort_distribution) in
# GEXF-zulässige Skalare. nx.write_gexf allein scheitert an diesen Attributen.
import os
os.makedirs('graphen', exist_ok=True)

exports = [
    (G_collab, 'graphen/author_collaboration_2020_2024.gexf'),
    (G_2020, 'graphen/keyword_network_2020.gexf'),
    (G_2024, 'graphen/keyword_network_2024.gexf')
]
for G_exp, path in exports:
    export_graph_gexf(G_exp, path)
    print(f'{path}: {G_exp.number_of_nodes():,} Knoten, {G_exp.number_of_edges():,} Kanten')
"""))

# Chapter 4: Pillar 3
cells.append(nbf.v4.new_markdown_cell("""## 4. Pfeiler 3: Rolling Temporal Link-Prediction im Koautorenschafts-Netzwerk (LE8)

### Methodisches Design (Liben-Nowell & Kleinberg, 2007)
Um eine realistische Evaluation zu gewährleisten, evaluieren wir über **sämtliche unverbundenen Kandidatenpaare** aktiver Journalist:innen über drei rollende Zeithorizonte:
- **Fenster 1:** Training 2020–2021 $\\to$ Evaluation neuer Kanten 2022
- **Fenster 2:** Training 2020–2022 $\\to$ Evaluation neuer Kanten 2023
- **Fenster 3:** Training 2020–2023 $\\to$ Evaluation neuer Kanten 2024

### Evaluierte Prädiktionsalgorithmen
1. **Common Neighbors (CN):** $\\text{score}(u, v) = |\\Gamma(u) \\cap \\Gamma(v)|$
2. **Jaccard Coefficient (JC):** $\\text{score}(u, v) = \\frac{|\\Gamma(u) \\cap \\Gamma(v)|}{|\\Gamma(u) \\cup \\Gamma(v)|}$
3. **Adamic-Adar Index (AA):** $\\text{score}(u, v) = \\sum_{z \\in \\Gamma(u) \\cap \\Gamma(v)} \\frac{1}{\\log |\\Gamma(z)|}$
4. **Preferential Attachment (PA):** $\\text{score}(u, v) = |\\Gamma(u)| \\cdot |\\Gamma(v)|$
5. **Random Baseline:** Gleichverteilte Zufallsbewertung
"""))

cells.append(nbf.v4.new_code_cell("""# Link Prediction Engine
def evaluate_link_prediction(split):
    G_train = split['G_train']
    pos_edges = set(split['positive_edges'])
    neg_edges = set(split['negative_edges'])
    # sorted, not set order: list(set) varies per process and would change the
    # random baseline, the Precision@k tie-break and the bootstrap resampling
    all_pairs = sorted(pos_edges | neg_edges)
    
    y_true = np.array([1 if p in pos_edges else 0 for p in all_pairs])
    
    # 1. Common Neighbors
    cn_scores = np.array([len(list(nx.common_neighbors(G_train, u, v))) if G_train.has_node(u) and G_train.has_node(v) else 0 for u, v in all_pairs])
    
    # 2. Jaccard Coefficient
    jc_preds = nx.jaccard_coefficient(G_train, all_pairs)
    jc_scores = np.round(np.array([p[2] for p in jc_preds]), 10)
    
    # 3. Adamic-Adar Index
    aa_preds = nx.adamic_adar_index(G_train, all_pairs)
    # Adamic-Adar summiert 1/log(deg) ueber nx.common_neighbors, das eine Menge
    # zurueckgibt. Die Summationsreihenfolge folgt damit der Hash-Ordnung und die
    # letzten Bits unterscheiden sich zwischen Prozessen, was Gleichstaende
    # unterschiedlich aufloest. Runden auf 10 Nachkommastellen entfernt dieses
    # Rauschen, ohne die Rangfolge zu beruehren.
    aa_scores = np.round(np.array([p[2] for p in aa_preds]), 10)
    
    # 4. Preferential Attachment
    pa_preds = nx.preferential_attachment(G_train, all_pairs)
    pa_scores = np.round(np.array([p[2] for p in pa_preds]), 10)
    
    # 5. Random Baseline
    np.random.seed(42)
    rand_scores = np.random.rand(len(all_pairs))
    
    algorithms = {
        'Adamic-Adar': aa_scores,
        'Common Neighbors': cn_scores,
        'Jaccard Coefficient': jc_scores,
        'Preferential Attachment': pa_scores,
        'Random Baseline': rand_scores
    }
    
    res = {}
    for name, scores in algorithms.items():
        pr_auc = average_precision_score(y_true, scores)
        fpr, tpr, _ = roc_curve(y_true, scores)
        roc_auc = auc(fpr, tpr)
        
        # Precision@k. CN und JC erzeugen grosse Gruppen identischer Scores;
        # argsort würde diese nach Array-Position auflösen, was das Ergebnis von
        # der Zeilenreihenfolge abhängig macht. Deterministischer, unverzerrter
        # Tie-Break über einen fest geseedeten Zufallsschlüssel.
        tie_rng = np.random.default_rng(42)
        tie_key = tie_rng.random(len(scores))
        k_indices = np.lexsort((tie_key, -np.asarray(scores, dtype=float)))
        p_at_20 = y_true[k_indices[:20]].mean()
        p_at_50 = y_true[k_indices[:50]].mean()
        p_at_100 = y_true[k_indices[:100]].mean()
        
        res[name] = {
            'PR-AUC (Avg Precision)': pr_auc,
            'ROC-AUC': roc_auc,
            'Precision@20': p_at_20,
            'Precision@50': p_at_50,
            'Precision@100': p_at_100,
            'scores': scores
        }
        
    return res, y_true

splits = create_rolling_link_prediction_windows(df)
all_results = {}

for s in splits:
    lbl = s['label']
    print(f'Evaluating {lbl} (Pos: {len(s["positive_edges"])}, Neg: {len(s["negative_edges"])}, Base Rate: {len(s["positive_edges"])/(len(s["positive_edges"])+len(s["negative_edges"])):.2%})...')
    res, y_true = evaluate_link_prediction(s)
    all_results[lbl] = (res, y_true)
    
    summary_df = pd.DataFrame([
        {
            'Algorithm': alg,
            'PR-AUC': metrics['PR-AUC (Avg Precision)'],
            'Precision@20': metrics['Precision@20'],
            'Precision@50': metrics['Precision@50'],
            'Precision@100': metrics['Precision@100'],
            'ROC-AUC': metrics['ROC-AUC']
        }
        for alg, metrics in res.items()
    ]).sort_values('PR-AUC', ascending=False)
    print(f'Ergebnisse für {lbl}:')
    print(summary_df.round(4).to_string())
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Ergebnisse der drei Zeitfenster).** Ueber alle drei Fenster
schlagen die nachbarschaftsbasierten Heuristiken die Zufallsbasislinie um ein
Vielfaches. Auffaellig ist die Entwicklung der Basisrate: sie steigt von 1.64%
im ersten auf 5.39% im letzten Fenster, weil mit laengerem Trainingszeitraum
mehr Autor:innen ueberhaupt als Kandidatenpaare in Frage kommen und die
Redaktion in den spaeteren Jahren staerker in Teams arbeitet.

Die absoluten Guetewerte folgen dieser Basisrate allerdings nicht monoton: die
PR-AUC von Adamic-Adar liegt bei 0.1034, faellt im mittleren Fenster auf 0.0865
und steigt im letzten auf 0.1939. Das ist kein reiner Modellgewinn, sondern
teilweise ein Effekt der guenstigeren Basisrate, weshalb der Vergleich immer
gegen die Zufallsbasislinie desselben Fensters zu lesen ist. Die Rangfolge der
Verfahren ist nicht ueber alle Fenster identisch: im ersten Fenster liegt
Jaccard mit 0.1060 knapp vor Adamic-Adar mit 0.1034, in den beiden folgenden
Fenstern liegt Adamic-Adar vorn. Die statistische Absicherung erfolgt im
Anschluss.
"""))

cells.append(nbf.v4.new_code_cell("""# Plot: Precision-Recall & ROC-Kurven für das finale Fenster (2020-23 -> 2024)
final_split_label = '2020-23 -> 2024'
res_final, y_true_final = all_results[final_split_label]

fig, axes = plt.subplots(1, 2, figsize=(15, 6))

# Precision-Recall Curve
for alg, m in res_final.items():
    p, r, _ = precision_recall_curve(y_true_final, m['scores'])
    axes[0].plot(r, p, linewidth=2, label=f"{alg} (PR-AUC = {m['PR-AUC (Avg Precision)']:.3f})")

axes[0].axhline(y_true_final.mean(), color='gray', linestyle=':', label=f'Baseline ({y_true_final.mean():.1%})')
axes[0].set_title(f'Precision-Recall Kurve ({final_split_label})')
axes[0].set_xlabel('Recall')
axes[0].set_ylabel('Precision')
axes[0].legend(loc='upper right')

# ROC Curve
for alg, m in res_final.items():
    fpr, tpr, _ = roc_curve(y_true_final, m['scores'])
    axes[1].plot(fpr, tpr, linewidth=2, label=f"{alg} (ROC-AUC = {m['ROC-AUC']:.3f})")

axes[1].plot([0, 1], [0, 1], color='gray', linestyle=':')
axes[1].set_title(f'ROC Kurve ({final_split_label})')
axes[1].set_xlabel('False Positive Rate')
axes[1].set_ylabel('True Positive Rate')
axes[1].legend(loc='lower right')

plt.suptitle('Pfeiler 3: Leistungsvergleich der Link-Prediction-Heuristiken (LE8)', y=1.02, fontsize=15)
plt.tight_layout()
plt.savefig('out_plots/13_link_prediction_curves.png', dpi=300)
plt.show()

# Bootstrap-Konfidenzintervall: Adamic-Adar vs. Preferential Attachment
np.random.seed(42)
B_BOOT = 1000
aa_sc = res_final['Adamic-Adar']['scores']
pa_sc = res_final['Preferential Attachment']['scores']
diffs = np.zeros(B_BOOT)
n_samples = len(y_true_final)

for b in range(B_BOOT):
    idx = np.random.randint(0, n_samples, n_samples)
    ap_aa = average_precision_score(y_true_final[idx], aa_sc[idx])
    ap_pa = average_precision_score(y_true_final[idx], pa_sc[idx])
    diffs[b] = ap_aa - ap_pa

ci_low, ci_high = np.percentile(diffs, [2.5, 97.5])
print(f'Bootstrap 95%-Konfidenzintervall für Differenz [PR-AUC(AA) - PR-AUC(PA)]: [{ci_low:.4f}, {ci_high:.4f}]')

# Der Befund wird aus dem Intervall abgeleitet, nicht vorweggenommen.
if ci_low > 0:
    print('Ergebnis: Adamic-Adar übertrifft Preferential Attachment signifikant (0 liegt unterhalb des 95%-CI).')
elif ci_high < 0:
    print('Ergebnis: Preferential Attachment übertrifft Adamic-Adar signifikant (0 liegt oberhalb des 95%-CI).')
else:
    print('Ergebnis: Kein signifikanter Unterschied zwischen Adamic-Adar und Preferential Attachment (0 liegt im 95%-CI).')

# Bester Algorithmus nach PR-AUC, statt einer fest verdrahteten Annahme
best_algo = max(
    ((n, r['PR-AUC (Avg Precision)']) for n, r in res_final.items()),
    key=lambda x: x[1]
)
print(f'Bester Algorithmus im finalen Fenster nach PR-AUC: {best_algo[0]} ({best_algo[1]:.4f})')
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 13, Link-Prediction).** Alle vier Heuristiken
schlagen die Zufallsbasislinie deutlich, und der Abstand waechst ueber die drei
Zeitfenster: im letzten Fenster erreicht Adamic-Adar eine PR-AUC von $0.1939$
gegenueber $0.0635$ fuer Zufall, also mehr als das Dreifache, bei einer
Basisrate von nur 5.39%.

Inhaltlich beantwortet das die Frage aus dem Meilenstein: Neue Kooperationen in
der Redaktion entstehen **ueber gemeinsame Dritte**, nicht ueber blosse
Prominenz. Adamic-Adar und Common Neighbors, die beide auf gemeinsame
Nachbarn setzen, liegen vorn; Preferential Attachment, das allein auf hohe Grade
setzt, faellt klar ab. Das Bootstrap-Konfidenzintervall der Differenz
$[0.0387, 0.0811]$ schliesst die Null aus. Praktisch heisst das: Wer neue
Zusammenarbeit anstossen will, sollte an bestehenden Teamkonstellationen
ansetzen und nicht bei den produktivsten Einzelpersonen.

Zwei Einschraenkungen. Erstens ist $\text{Precision@20} = 0.55$ im letzten
Fenster zwar hoch, faellt bei $k = 100$ aber auf $0.37$: die Vorhersage
funktioniert fuer die naheliegendsten Paare gut und wird danach schnell
schwaecher. Zweitens variiert die Rangfolge zwischen den Fenstern; im ersten
Fenster liegt Jaccard knapp vor Adamic-Adar. Robust ist die Aussage
"gemeinsame Nachbarn schlagen Prominenz", nicht die Wahl eines einzelnen
Algorithmus.
"""))

# Chapter 5: Synthesis & Evidence Map
cells.append(nbf.v4.new_markdown_cell("""## 5. Pfeiler 4: Diffusion im Kollaborationsnetzwerk (LE9)

**Frage.** Sind die in 2.1 identifizierten strukturellen Broker tatsaechlich die
wirksamsten Multiplikatoren, wenn sich etwas ueber Koautorenschaften ausbreitet,
etwa eine Recherchemethode, ein neues Format oder eine Quelle?

**Modell.** Independent Cascade auf $G_{collab}$: jede neu aktivierte Person hat
genau einen Versuch, jede noch inaktive Koautorin zu aktivieren, mit
Wahrscheinlichkeit $p$, skaliert am Newman-Kollaborationsgewicht. Verglichen
werden drei Startmengen gleicher Groesse: die Burt-Broker (niedrigster
Constraint), die Personen mit hoechstem Grad, und eine zufaellige Auswahl."""))

cells.append(nbf.v4.new_code_cell("""# 5.1 Independent Cascade: Startmengen-Strategien ueber den gesamten p-Bereich (LE9)
# p ist so normiert, dass es die Uebertragungswahrscheinlichkeit ueber eine
# Kollaboration MITTLERER Staerke ist (Median-Gewicht). Eine Normierung am
# Maximalgewicht waere irrefuehrend: der staerkste Autorenpaar-Wert liegt bei
# rund 103, der Median bei 1.0, wodurch die typische Kante etwa 50-fach unter
# dem nominellen p landen wuerde.
SEED_SET_SIZE = 10
N_SIM = 200
P_GRID = [0.02, 0.05, 0.1, 0.2, 0.5]

w_scale = weight_normalizer(G_collab, 'weight')
w_all = np.array([d['weight'] for _, _, d in G_collab.edges(data=True)])
print(f'Kantengewichte: Median {np.median(w_all):.2f}, Mittel {w_all.mean():.2f}, '
      f'Maximum {w_all.max():.2f}')
print(f'Normierungsgroesse (Median) = {w_scale:.2f}: p gilt fuer eine Kante mittlerer Staerke.\\n')

burt_seeds = list(top_burt['author'].head(SEED_SET_SIZE))
hub_seeds = list(broker_pool.sort_values('degree', ascending=False)['author'].head(SEED_SET_SIZE))
# Die Zufallsbasislinie muss aus derselben Grundgesamtheit gezogen werden wie
# die beiden gezielten Strategien. Eine Ziehung ueber alle 574 Knoten wuerde im
# Mittel rund 3.7 isolierte Autor:innen enthalten, die konstruktionsbedingt
# nichts verbreiten koennen - der Vorsprung waere dann teilweise ein
# Komponenten-Artefakt statt ein Effekt der Auswahlstrategie.
rng_seed = np.random.default_rng(42)
random_pool = list(broker_pool['author'])
random_seeds = list(rng_seed.choice(random_pool, size=SEED_SET_SIZE, replace=False))
gcc_collab_nodes = max(nx.connected_components(G_collab), key=len)
naive_seeds = list(np.random.default_rng(7).choice(list(G_collab.nodes()),
                                                   size=SEED_SET_SIZE, replace=False))
print(f'Zufallsbasislinie aus der Broker-Grundgesamtheit ({len(random_pool)} Personen, '
      f'Grad >= 5 und >= 10 Artikel), nicht aus allen {G_collab.number_of_nodes()} Knoten.')
print(f'Zum Vergleich wird zusaetzlich eine naive Ziehung ueber alle Knoten '
      f'ausgewiesen; davon liegen {sum(1 for s in naive_seeds if s not in gcc_collab_nodes)} '
      f'von {SEED_SET_SIZE} ausserhalb der Riesenkomponente.')

strategies = {
    'Burt-Broker': burt_seeds,
    'Hubs (max. Grad)': hub_seeds,
    'Zufallsauswahl (vergleichbare Grundgesamtheit)': random_seeds,
    'Zufallsauswahl (naiv, alle Knoten)': naive_seeds
}

sweep_rows = []
curves_at_ref = {}
for p_val in P_GRID:
    for name, seeds in strategies.items():
        r = simulate_diffusion(G_collab, seeds, p=p_val, n_sim=N_SIM,
                               weight='weight', seed=42)
        sweep_rows.append({
            'p': p_val, 'Strategie': name,
            'Mittlere Reichweite': r['mean_reach'], 'Std': r['std_reach'],
            'Anteil des Netzwerks': r['mean_reach_share']
        })
        if p_val == 0.05:
            curves_at_ref[name] = r['mean_curve']

sweep_df = pd.DataFrame(sweep_rows)
pivot = sweep_df.pivot(index='p', columns='Strategie', values='Mittlere Reichweite')
print(f'Mittlere Reichweite je Strategie und p ({N_SIM} Simulationen, '
      f'Startmenge {SEED_SET_SIZE}, n={G_collab.number_of_nodes()}):')
print(pivot.round(1).to_string())

print('\\nSiegerstrategie je p:')
for p_val in P_GRID:
    sub = sweep_df[sweep_df['p'] == p_val].sort_values('Mittlere Reichweite', ascending=False)
    lead = sub.iloc[0]['Mittlere Reichweite'] - sub.iloc[-1]['Mittlere Reichweite']
    print(f'  p = {p_val:<5} {sub.iloc[0]["Strategie"]:<18} '
          f'({sub.iloc[0]["Mittlere Reichweite"]:.1f} Personen, '
          f'Vorsprung auf die letzte Strategie: {lead:.1f})')

gcc_size = max(len(c) for c in nx.connected_components(G_collab))
print(f'\\nGroesse der Giant Component: {gcc_size} von {G_collab.number_of_nodes()} '
      f'({gcc_size / G_collab.number_of_nodes():.1%})')

fig, axes = plt.subplots(1, 2, figsize=(14, 4.8))
for name in strategies:
    sub = sweep_df[sweep_df['Strategie'] == name]
    axes[0].plot(sub['p'], sub['Mittlere Reichweite'], marker='o', label=name)
axes[0].axhline(gcc_size, color='gray', linestyle=':', label=f'Giant Component ({gcc_size})')
axes[0].set_xscale('log')
axes[0].set_title('Reichweite ueber den p-Bereich')
axes[0].set_xlabel('Uebertragungswahrscheinlichkeit p (Median-Kante)')
axes[0].set_ylabel('Erreichte Personen')
axes[0].legend(fontsize=8)

for name, curve in curves_at_ref.items():
    axes[1].plot(range(len(curve)), curve, marker='o', markersize=3, label=name)
axes[1].set_title('Diffusionsverlauf bei p = 0.05')
axes[1].set_xlabel('Schritt'); axes[1].set_ylabel('Kumuliert aktivierte Personen')
axes[1].legend(fontsize=8)

plt.suptitle('Abbildung 14: Informationsdiffusion im Kollaborationsnetzwerk, Startmengen-Strategien ueber p', y=1.03)
plt.tight_layout()
plt.savefig('out_plots/14_diffusion_seed_strategies.png', dpi=300, bbox_inches='tight')
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""**Interpretation (Abbildung 14, Diffusion).** Das Ergebnis ist ein
Negativbefund, und zwar ein belastbarer: **die Wahl der Startmenge spielt in
diesem Netzwerk kaum eine Rolle.**

Bei $p = 0.02$ erreichen die Hubs im Mittel 89.0 Personen, die Burt-Broker
88.4 und eine Zufallsauswahl aus derselben Grundgesamtheit 87.3. Der Vorsprung
der gezielten Auswahl liegt damit unter 2%, und die Spannweite ueber alle vier
Varianten betraegt weniger als 2% des Mittelwerts. Auch bei groesserem $p$
bleiben die Unterschiede in dieser Groessenordnung, waehrend alle Strategien
gegen die Groesse der Riesenkomponente konvergieren.

**Warum die naive Zufallsauswahl bei hohem $p$ sogar vorn liegt.** Sie zieht
ihre Startknoten aus allen Autor:innen, also auch aus den kleinen Komponenten
ausserhalb des Hauptnetzes. Sobald die Uebertragung leicht genug ist, saettigt
jede Strategie die Riesenkomponente ohnehin; zusaetzliche Startpunkte in
separaten Komponenten bringen dann noch ein paar Personen extra. Das ist ein
Komponenten-Effekt, kein Strategie-Effekt, und genau deshalb wird die
vergleichbare Zufallsbasislinie aus derselben Grundgesamtheit wie Broker und
Hubs gezogen und die naive Ziehung nur zusaetzlich ausgewiesen.

**Redaktionelle Lesart.** Wer eine Neuerung in dieser Redaktion verbreiten
will, gewinnt durch die Auswahl der Startpersonen nichts. Was
zaehlt, ist die Struktur selbst: rund ein Drittel der Autor:innen ist ueber
Koautorenschaften ueberhaupt nicht erreichbar (2.6), und die Riesenkomponente
bildet eine harte Obergrenze fuer jede Kaskade. Verbreitung muss hier
organisiert werden, sie ergibt sich nicht aus geschickter Auswahl.

**Einschraenkung und Methodengeschichte.** Das Independent-Cascade-Modell ist
eine Simulation mit gesetztem $p$, kein gemessener Prozess. Belastbar ist die
Aussage, dass die Strategien nahe beieinander liegen, sowie die
Saettigungsgrenze bei der Riesenkomponente. Zwei fruehere Staende dieser
Analyse kamen zu anderen Schluessen, beide aus methodischen Gruenden: zuerst
war $p$ am Maximalgewicht statt am Median normiert, wodurch jede Kaskade
erstickte und faelschlich "Hubs schlagen Broker" herauskam; danach wurde die
Zufallsbasislinie ueber alle Knoten gezogen, waehrend Broker und Hubs aus einer
aktivitaetsgefilterten Grundgesamtheit stammten, was den Brokern einen
scheinbaren Vorsprung vom Faktor 2.5 verschaffte. Erst der Vergleich gleicher
Grundgesamtheiten zeigt, dass real kein Vorsprung besteht. Siehe Lessons
Learned.
"""))

cells.append(nbf.v4.new_markdown_cell("""## 6. Gesamtsynthese, Evidence Map & Akademische Deklarationen

### 6.1 Evidence Map (Zuordnung zu den Bewertungskriterien)

| Kriterium | Gewicht | Umsetzung im Projekt | Fundstelle |
| :--- | :---: | :--- | :--- |
| **1. Explorative Datenanalyse & Quelldaten-Validierung** | 1 | Stratifizierte Live-Validierung ($n=60$) gegen 20min.ch mit 100% Erreichbarkeit, 100% Titel- und 98.3% Datumsübereinstimmung. Systematische Fehlwert-Analyse: 41.4% der Kommentarwerte fehlen und werden als `NaN` geführt statt als 0. Token-basierte Entitäts-Resolution entfernt 133 institutionelle Knoten (Agenturen, Desks). | `src/00_eda.qmd`, `src/01_cleaning.qmd`, `data/ground_truth_validation.md`, `src/clean_dataset.py` |
| **2. Vielfalt der Netzwerk-Analysen** | 2 | Two-Mode-Modellierung und Newman-Projektion (LE3), Louvain-Communities, Cliquen und k-Core (LE4), Zentralität und strukturelle Löcher nach Burt (LE5), Zentralisierung $C_D$ und $C_B$, Metriken und Connectivity (LE6), drei Hypothesentests inkl. QAP (LE7), rollierende Link-Prediction (LE8), Independent-Cascade-Diffusion (LE9). Zwei komplementäre Netzwerke plus Sensitivitätsanalyse über $k$. | Kapitel 2 bis 5 |
| **3. Nachvollziehbarkeit & korrekte Metriken** | 2 | Drei Nullmodelle unterschiedlicher Strenge: Label-Permutation, gradtreues Maslov-Sneppen-Rewiring, QAP mit gemeinsamer Zeilen-/Spalten-Permutation. Leakage-freie Leave-One-Out-JSD, OLS mit $N$, $R^2$ und ausgewiesenen Fallausschlüssen, unbalancierte Link-Prediction mit Bootstrap-CI. Jede Analyse wird auf den Anwendungsfall bezogen interpretiert; die Grenzen des Designs werden in 3.2 und 3.4 offengelegt. 17 Unit-Tests. | 2.2 bis 2.6, 3.2, 3.4, Kap. 4 und 5; `python src/network_models.py` |
| **4. Anschaulichkeit der Resultate** | 1 | 14 durchnummerierte 300-DPI-Abbildungen (Abb. 1 bis 14), davon vier Netzwerk-Renderings, alle inline im Notebook sichtbar und in der Interpretation namentlich referenziert, sowie drei `.gexf`-Exporte für Gephi. | `out_plots/`, `graphen/` |
| **5. Ausblick** | 1 | Methodische Erweiterungen und explizit benannte, bewusst nicht abgedeckte Lernergebnisse. | 5.2 |

---

### 6.2 Ausblick

**Nicht abgedeckte Lernergebnisse.** Eine im Skript behandelte Analysefamilie wurde bewusst nicht umgesetzt und bildet den natürlichen nächsten Schritt:

1. **Graphlets (Kap. 14).** Graphlet-Degree-Vektoren würden erlauben, Journalist:innen nicht nach ihrem Ressort, sondern nach ihrer strukturellen Rolle zu gruppieren. Damit liesse sich prüfen, ob es wiederkehrende Kollaborationsmuster gibt, die quer zur formalen Ressortgliederung liegen.

**Inhaltliche Erweiterungen.**

2. **Gerichtete und multirelationale Modellierung.** Die aktuelle Kollaborationskante ist ungerichtet. Mit der Autorenreihenfolge in der Byline (Erst- vs. Zweitautorschaft) liesse sich eine gerichtete Senioritätsrelation modellieren und mit dem semantischen Netzwerk zu einem multirelationalen Graphen kombinieren.
3. **Semantische Einbettungen.** Node2Vec- oder GNN-Einbettungen kombiniert mit deutschsprachigen Transformer-Vektoren würden inhaltliche Nähe feiner erfassen als die aktuelle Ressort-Verteilung.
4. **Dynamische Hypergraphen.** Redaktionsteams umfassen oft mehr als zwei Personen. Eine Hypergraph-Modellierung würde den Informationsverlust der paarweisen Projektion vermeiden.

**Was noch zu überarbeiten wäre.** Die Interaktionswerte (Likes, Shares, Kommentare) sind Momentaufnahmen zum Scraping-Zeitpunkt und driften gegenüber der Live-Plattform. Für belastbare Aussagen über Reichweite müssten sie zu mehreren Zeitpunkten erhoben werden. Ebenso fehlt bislang eine Auflösung von Namensvarianten derselben Person (etwa mit und ohne Zweitnamen).

---

### 6.3 Lessons Learned

1. **Entitäts-Resolution entscheidet über die Validität des ganzen Netzwerks.** Eine Filterung über exakte Zeichenkettenvergleiche reichte nicht aus. Zusammengesetzte Bylines wie `SDA fss`, `Rat Dpa` oder `Agence France-Presse` gelangten als vermeintliche Journalist:innen in den Graphen. `Agence France-Presse` mit 214 Artikeln lag sogar in der grössten Clique und blähte damit Kohäsions- und Zentralitätsmasse auf. Erst eine token-basierte Klassifikation entfernte 133 institutionelle Knoten. **Lehre:** Knoten-Identität ist keine Nebensache der Datenbereinigung, sondern bestimmt jedes nachgelagerte Mass.

2. **Fehlende Werte dürfen nicht zu Nullen werden.** 41.4% der Kommentarwerte fehlen, weil die Kommentarfunktion deaktiviert oder nicht erfasst war. Als 0 kodiert hätten sie „kein Interesse“ statt „keine Messung“ bedeutet und die Regression systematisch verzerrt.

3. **Nullmodelle müssen zur Datenstruktur passen.** In der Link-Prediction landeten Trainingskanten in der Negativmenge, weil Kantentupel unsortiert verglichen wurden. Beim QAP-Test korrelierten zunächst zwei Matrizen, die beide für nicht benachbarte Paare null sind, wodurch teilweise blosse Kanten-Kopräsenz gemessen wurde. Nach Korrektur auf eine über alle Dyaden definierte JSD-Matrix kehrte sich das Vorzeichen von $+0.148$ auf $-0.140$ um, was der Homophilie-Hypothese entspricht. **Lehre:** Ein plausibel aussehendes Ergebnis ist kein Korrektheitsnachweis. Beide Fehler wurden erst durch systematisches Code-Review und Unit-Tests sichtbar.

4. **Dichte-Vergleiche über Zeit sind ohne Normierung wertlos.** Der direkte Vergleich von Netzwerkdichten über Jahre mit unterschiedlicher Artikelzahl führt in die Irre. Ein fixiertes globales Vokabular, Mutual-$k$-NN-Sparsifizierung und normierte Zentralisierung waren notwendig, um überhaupt vergleichbare Topologien zu erhalten.

5. **Eine Hypothese muss zum Messinstrument passen.** Hypothese 2 sagte für 2020 maximale Zentralisierung voraus. Erst bei der Auswertung wurde klar, dass die gewählte Mutual-$k$-NN-Sparsifizierung $C_D$ konstruktionsbedingt deckelt und damit kaum Varianz zulässt (3.2, 3.4). Die Hypothese war also gegenüber dem eigenen Design nicht trennscharf. Die Lehre ist, die Bandbreite eines Masses unter dem geplanten Verfahren *vor* der Hypothesenformulierung zu prüfen.

6. **Ein zweites Augenpaar findet, was man selbst nicht sieht.** Ein systematisches Review deckte auf, dass eine Methodikzusage (Sensitivitätsprüfung über $k$) im Text stand, aber nie ausgeführt wurde, und dass die als „Burt“ bezeichnete Kennzahl gar keine Burt-Grösse war, sondern ein Verhältnis aus Betweenness und Grad. Beides ist jetzt implementiert bzw. korrigiert. **Lehre:** Formulierungen im Bericht müssen gegen den ausgeführten Code geprüft werden, nicht gegen die Absicht.

7. **Normierungen sind Annahmen und müssen als solche geprüft werden.** In der ersten Fassung der Diffusionssimulation wurde die Übertragungswahrscheinlichkeit am **Maximalgewicht** normiert. Da das stärkste Autorenpaar ein Gewicht von 103 hat, der Median aber 1.0, lag die effektive Wahrscheinlichkeit an einer typischen Kante rund 50-fach unter dem angegebenen $p$; 94.7% aller Kanten blieben unter 0.01. Jede Kaskade erstickte dadurch von selbst, und der scheinbare Befund „Hubs schlagen Broker“ war ein Artefakt. Nach Normierung am Median und einem Sweep über $p$ zeigt sich das Gegenteil: bei kleinem $p$ gewinnen die Broker deutlich, bei grossem $p$ wird die Startmenge irrelevant. Dieselbe Fehlerklasse trat zuvor beim QAP-Test auf, wo eine über alle Dyaden statt nur über Kanten definierte Matrix das Vorzeichen umkehrte. **Lehre:** Eine Normierung, die niemand hinterfragt, produziert plausibel aussehende Zahlen. Für jede Skalierung ist zu prüfen, was der Parameter am *typischen* Datenpunkt bedeutet, nicht am extremsten.

8. **Eine Baseline muss aus derselben Grundgesamtheit stammen wie die getesteten Strategien.** Nach der Korrektur der Normierung schien die Diffusion über Burt-Broker das 2.5-fache einer Zufallsauswahl zu erreichen. Auch das war ein Artefakt: die Broker- und Hub-Startmengen stammten aus einer aktivitätsgefilterten Grundgesamtheit (Grad $\geq 5$, $\geq 10$ Artikel), die Zufallsauswahl dagegen aus allen Knoten, von denen rund ein Drittel isoliert ist und konstruktionsbedingt nichts verbreiten kann. Bei gleicher Grundgesamtheit schrumpft der Vorsprung auf unter 2%. **Lehre:** Zwei Korrekturen in derselben Analyse hintereinander sind ein Warnsignal. Wer eine Kennzahl repariert, sollte im selben Schritt prüfen, ob der Vergleich, in dem sie steht, überhaupt fair ist.

9. **Ein fixierter Seed garantiert noch keine Reproduzierbarkeit.** Zwei aufeinanderfolgende Läufe desselben Notebooks auf identischen Daten lieferten unterschiedliche Zahlen, obwohl überall `seed=42` gesetzt war. Ursache war die Iteration über **Mengen**: Python-Sets werden in Hash-Reihenfolge durchlaufen, und diese hängt von `PYTHONHASHSEED` ab, das pro Prozess variiert. Betroffen waren die Kandidatenreihenfolge der Link-Prediction (und damit Zufallsbasislinie, Precision@k-Tie-Break und Bootstrap-KI), die Startmengen-Iteration der Diffusion, die Knotenreihenfolge jedes aus einer Menge gebildeten Teilgraphen sowie, über die Summationsreihenfolge, die letzten Bits des Adamic-Adar-Scores. Zusätzlich war das Maslov-Sneppen-Rewiring ungeseedet, weil networkx dafür das `random`-Modul und nicht NumPy verwendet. Nach Sortierung aller Mengen-Iterationen, expliziter Seed-Übergabe und Rundung der Scores sind zwei Läufe byte-identisch. **Lehre:** Reproduzierbarkeit ist zu *prüfen*, nicht anzunehmen. Der Test ist billig: zweimal laufen lassen und die Ausgaben vergleichen.

10. **Was wir künftig anders machen würden.** Unit-Tests für die Graphkonstruktion von Anfang an statt nachträglich, und ein Manifest mit Hashes für Roh- **und** abgeleitete Daten ab dem ersten Tag, damit Reproduzierbarkeit nicht rekonstruiert werden muss.

---

### 6.4 KI-Deklaration (AI-Use Disclosure)

> **HINWEIS: Dieser Abschnitt ist noch unvollständig.** Die Projektbeschreibung verlangt neben der Deklaration ausdrücklich die **Angabe der Prompts**. Die vollständige Prompt-Dokumentation ist in `TODO.md` als blockierender Punkt erfasst und muss vor der Abgabe in `docs/KI-Deklaration.md` ergänzt und hier verlinkt werden.

In Übereinstimmung mit den Richtlinien zur wissenschaftlichen Redlichkeit deklarieren wir:

- Für Code-Erstellung, Refactoring und Code-Review wurden generative KI-Werkzeuge eingesetzt (Antigravity/Codex sowie Claude Code).
- Themenwahl, Hypothesenbildung, Modellierungsentscheidungen und die Interpretation der Resultate liegen bei den Studierenden (Elias und Luca).
- Ein systematisches Code-Review deckte mehrere methodische Fehler in KI-generiertem Code auf (Datenleck in der Link-Prediction, fehlerhafte Leave-One-Out-Berechnung, unbedingt ausgegebene Signifikanzaussagen). Diese wurden korrigiert und sind durch Unit-Tests abgesichert. Die Befunde und ihre Behebung sind in `README.md` dokumentiert.
- **Ausstehend:** vollständige Prompt-Protokolle beider Werkzeuge.
"""))

nb.cells = cells

with open('src/02_analyse.ipynb', 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f'Successfully generated src/02_analyse.ipynb with {len(nb.cells)} cells!')
