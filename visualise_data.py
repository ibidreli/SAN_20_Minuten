'''import pandas as pd
import matplotlib.pyplot as plt

# Daten laden
df = pd.read_csv("20min_metadaten_keywords.csv", usecols=["datum"], parse_dates=["datum"])

# Monat extrahieren (Jahr + Monat)
df["monat"] = df["datum"].dt.to_period("M").dt.to_timestamp()

# Artikel pro Monat zählen
artikel_pro_monat = df["monat"].value_counts().sort_index()

# Plot
plt.figure(figsize=(12, 6))
plt.plot(artikel_pro_monat.index, artikel_pro_monat.values, linewidth=2)
plt.xlabel("Monat")
plt.ylabel("Anzahl Artikel")
plt.title("Artikel pro Monat")
plt.grid(True)
plt.tight_layout()
plt.show()


# Leere oder fehlende Ressorts ausfiltern
ressort_counts = df["ressort"].dropna().value_counts()

plt.figure(figsize=(10, 6))
ressort_counts.plot(kind="bar")
plt.title("Artikelanzahl pro Ressort")
plt.xlabel("Ressort")
plt.ylabel("Anzahl Artikel")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()


import pandas as pd
import matplotlib.pyplot as plt

# === Datei laden ===
# Gib hier den richtigen Pfad zu deiner CSV-Datei an!
pfad = "20min_metadaten_keywords.csv"  # z. B. "C:/Users/elias/Desktop/artikel.csv"
df = pd.read_csv(pfad, usecols=["datum", "ressort"], parse_dates=["datum"])

# === Daten vorbereiten ===
df = df.dropna(subset=["datum", "ressort"])
df["monat"] = df["datum"].dt.to_period("M").dt.to_timestamp()

# === Artikel pro Monat & Ressort zählen ===
pivot_df = df.pivot_table(index="monat", columns="ressort", aggfunc="size", fill_value=0)

# === Gestapeltes Flächendiagramm ===
plt.figure(figsize=(14, 6))
pivot_df.plot.area(linewidth=0, figsize=(14, 6))
plt.title("Artikel pro Monat nach Ressort (gestapelt)")
plt.xlabel("Monat")
plt.ylabel("Anzahl Artikel")
plt.legend(title="Ressort", loc="upper left")
plt.grid(True)
plt.tight_layout()
plt.show()


import pandas as pd
from collections import Counter
import re

# CSV laden – nur die Spalte "keywords"
df = pd.read_csv("20min_metadaten_keywords.csv", usecols=["keywords"])

# Leere Einträge rausfiltern
df = df.dropna(subset=["keywords"])

# Zähler initialisieren
keyword_counter = Counter()

# Alle Keywords durchgehen
i = 0
for eintrag in df["keywords"]:
    i += 1
    if i % 10:
        print(i)
    # Nur Begriffe extrahieren (ohne Gewicht), z.B. "Wort (0.123)" → "Wort"
    begriffe = re.findall(r'([^\(,]+?)\s*\(\d+\.\d+\)', eintrag)
    keyword_counter.update([wort.strip() for wort in begriffe])

# Top 20 häufigste Keywords
top_keywords = keyword_counter.most_common(50)

# Ausgabe
print("Top 20 Keywords:")
for keyword, anzahl in top_keywords:
    print(f"{keyword}: {anzahl}")
'''
import pandas as pd
import networkx as nx
from pyvis.network import Network
import ast
import re
from collections import defaultdict
from tqdm import tqdm

# === 1. CSV-Datei laden ===
df = pd.read_csv("20min_metadaten_keywords.csv", usecols=["keywords"])

# === 2. Keywords extrahieren ===
def parse_keywords(entry):
    if pd.isna(entry): return []
    try:
        # Nur Begriffe extrahieren – Gewicht ignorieren
        return [kw.strip() for kw in re.findall(r'([^,]+?)\s*\(\d+\.\d+\)', entry)]
    except:
        return []

df["keywords_clean"] = df["keywords"].map(parse_keywords)

# === 3. Keyword-zu-Artikel-Mapping aufbauen ===
keyword_to_articles = defaultdict(set)
for idx, keywords in df["keywords_clean"].items():
    for kw in keywords:
        keyword_to_articles[kw].add(idx)

# === 4. Keywords filtern (z. B. nur die Top 1000 nach Häufigkeit) ===
from collections import Counter

# Zähle die Artikel pro Keyword
keyword_counts = Counter()
for kw, arts in keyword_to_articles.items():
    keyword_counts[kw] = len(arts)

# Top 1000 Keywords auswählen
filtered_keywords = set([kw for kw, _ in keyword_counts.most_common(80000)])
print(f"➡️ Behaltene Keywords (Top 1000): {len(filtered_keywords)}")

# === 5. Kanten berechnen (beidseitige Relevanz = unerwiderte Liebe) ===
G = nx.Graph()
keywords = list(filtered_keywords)

for i in tqdm(range(len(keywords))):
    kw1 = keywords[i]
    set1 = keyword_to_articles[kw1]
    for j in range(i + 1, len(keywords)):
        kw2 = keywords[j]
        set2 = keyword_to_articles[kw2]
        common = set1 & set2
        if not common:
            continue
        rel1 = len(common) / len(set1)
        rel2 = len(common) / len(set2)
        gewicht = rel1 + rel2
        if gewicht >= 0.01:
            G.add_edge(kw1, kw2, weight=gewicht)

# === 6. Debug: Anzahl Knoten und Kanten ===
print(f"🔎 Anzahl Knoten: {G.number_of_nodes()}, Kanten: {G.number_of_edges()}")

# === 7. Visualisierung mit pyvis (nur Top 1000 Keywords) ===
# Top 1000 Keywords nach Anzahl Artikel bestimmen
from collections import Counter

# Zähle die Artikel pro Keyword
keyword_counts = Counter()
for kw, arts in keyword_to_articles.items():
    keyword_counts[kw] = len(arts)

# Top 1000 Keywords auswählen
selected_keywords = set([kw for kw, _ in keyword_counts.most_common(80000)])

# Subgraph mit nur diesen Keywords
G_sub = G.subgraph(selected_keywords).copy()

# Setze das Attribut 'label' für alle Knoten explizit auf den Knotennamen (Keyword)
for node in G_sub.nodes():
    G_sub.nodes[node]['label'] = node

print(f"🔎 Subgraph: {G_sub.number_of_nodes()} Knoten, {G_sub.number_of_edges()} Kanten")

net = Network(height="900px", width="100%", bgcolor="#222", font_color="white")
net.from_nx(G_sub)
net.repulsion(node_distance=200, spring_length=200)
net.write_html("keyword_network.html")

# === Export für Gephi (GEXF) ===
nx.write_gexf(G_sub, "keyword_network.gexf")
print("✅ Netzwerk als GEXF-Datei für Gephi exportiert: keyword_network.gexf")

