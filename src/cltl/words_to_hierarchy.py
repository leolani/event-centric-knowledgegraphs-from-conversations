from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering
from scipy.cluster.hierarchy import linkage, to_tree
from sklearn.feature_extraction.text import TfidfVectorizer
import networkx as nx
import matplotlib.pyplot as plt
import re
import os

def normalize_phrase(p: str) -> str:
    return re.sub(r"\s+", " ", p.strip().lower())


def extract_keywords(phrases, top_k=2):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
    X = vectorizer.fit_transform(phrases)
    scores = X.mean(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    top_idx = scores.argsort()[::-1][:top_k]
    return ", ".join(terms[i] for i in top_idx)

def build_hybrid_tree(phrases, k=3, model_name="all-MiniLM-L6-v2"):
    phrases = list(dict.fromkeys(normalize_phrase(p) for p in phrases))

    model = SentenceTransformer(model_name)
    X = model.encode(phrases, normalize_embeddings=True)

    # Stage 1: Macro clustering
    macro_labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X)
    macro_groups = {}
    for phrase, label in zip(phrases, macro_labels):
        macro_groups.setdefault(int(label), []).append(phrase)

    G = nx.DiGraph()

    for macro_id, macro_phrases in macro_groups.items():
        # Use deterministic macro node ID
        macro_node = f"macro_{macro_id}"
        macro_label = extract_keywords(macro_phrases)
        if macro_node not in G:
            G.add_node(macro_node, label=f"{macro_label} ({len(macro_phrases)})", type="macro")

        if len(macro_phrases) == 1:
            # Single leaf
            leaf = macro_phrases[0]
            if leaf not in G:
                G.add_node(leaf, label=leaf, type="leaf")
            G.add_edge(macro_node, leaf)
            continue

        # Stage 2: Subtree inside each macro group
        sub_X = model.encode(macro_phrases, normalize_embeddings=True)
        Z = linkage(sub_X, method="ward")
        root, _ = to_tree(Z, rd=True)

        def collect_leaves(node):
            if node.is_leaf():
                return [macro_phrases[node.id]]
            return collect_leaves(node.left) + collect_leaves(node.right)

        def add_subtree(node, parent_id):
            if node.is_leaf():
                leaf = macro_phrases[node.id]
                if leaf not in G:
                    G.add_node(leaf, label=leaf, type="leaf")
                G.add_edge(parent_id, leaf)
            else:
                # Deterministic internal node ID
                leaf_phrases = collect_leaves(node)
                cluster_label = extract_keywords(leaf_phrases)
                #node_id = f"{parent_id}_cluster_{min(leaf_phrases)}_{max(leaf_phrases)}"
                node_id = cluster_label
                print('Node_id', node_id)
                if not node_id == parent_id:
                    G.add_node(node_id, label=cluster_label, type="cluster")
                    G.add_edge(parent_id, node_id)
                    print('Node_id not Parent_id')
                    print("parent", parent_id)
                    add_subtree(node.left, node_id)
                    add_subtree(node.right, node_id)
        add_subtree(root, macro_node)

    return G

def build_hybrid_tree_with_single_word_parents(phrases, k=3, model_name="all-MiniLM-L6-v2"):
    phrases = list(dict.fromkeys(normalize_phrase(p) for p in phrases))
    model = SentenceTransformer(model_name)
    X = model.encode(phrases, normalize_embeddings=True)

    # Macro clustering
    macro_labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X)
    macro_groups = {}
    for phrase, label in zip(phrases, macro_labels):
        macro_groups.setdefault(int(label), []).append(phrase)

    G = nx.DiGraph()
    cluster_counter = [0]

    for macro_id, macro_phrases in macro_groups.items():
        macro_node = f"macro_{macro_id}"
        macro_label = extract_keywords(macro_phrases)
        if macro_node not in G:
            G.add_node(macro_node, label=f"{macro_label} ({len(macro_phrases)})", type="macro")

        # Separate single-word vs multi-word phrases
        single_words = [p for p in macro_phrases if len(p.split()) == 1]
        multi_words = [p for p in macro_phrases if len(p.split()) > 1]

        # Add single-word phrases as direct children of macro node
        for sw in single_words:
            if sw not in G:
                G.add_node(sw, label=sw, type="leaf")
            G.add_edge(macro_node, sw)

        # Attach multi-word phrases to matching single-word parent if possible
        remaining_multi = []
        for mw in multi_words:
            matched = False
            for sw in single_words:
                if sw in mw:
                    G.add_node(mw, label=mw, type="leaf")
                    G.add_edge(sw, mw)
                    matched = True
                    break
            if not matched:
                remaining_multi.append(mw)

        # Build subtree for remaining multi-word phrases (if any)
        if remaining_multi:
            sub_X = model.encode(remaining_multi, normalize_embeddings=True)
            Z = linkage(sub_X, method="ward")
            root, _ = to_tree(Z, rd=True)

            def collect_leaves(node):
                if node.is_leaf():
                    return [remaining_multi[node.id]]
                return collect_leaves(node.left) + collect_leaves(node.right)

            def add_subtree(node, parent_id):
                if node.is_leaf():
                    leaf = remaining_multi[node.id]
                    if leaf not in G:
                        G.add_node(leaf, label=leaf, type="leaf")
                    G.add_edge(parent_id, leaf)
                    return

                leaf_phrases = collect_leaves(node)
                cluster_label = extract_keywords(leaf_phrases)

                cluster_counter[0] += 1
                node_id = f"{parent_id}_cluster_{cluster_counter[0]}"

                if node_id not in G:
                    G.add_node(node_id, label=cluster_label, type="cluster")
                    G.add_edge(parent_id, node_id)
                    add_subtree(node.left, node_id)
                    add_subtree(node.right, node_id)

            add_subtree(root, macro_node)

    return G

def get_roots(G):
    return [n for n in G.nodes() if G.in_degree(n) == 0]

def extract_subtree_with_depth(G, root, max_depth=2):
    nodes = {root}
    frontier = [(root, 0)]

    while frontier:
        node, depth = frontier.pop()
        if depth >= max_depth and max_depth > 0:
            continue
        for child in G.successors(node):
            nodes.add(child)
            frontier.append((child, depth + 1))

    return G.subgraph(nodes).copy()

def get_tree_depth(G, root):
    # max distance from root to any leaf
    leaves = [n for n in nx.descendants(G, root) if G.out_degree(n) == 0]
    if not leaves:
        return 0
    lengths = [nx.shortest_path_length(G, root, leaf) for leaf in leaves]
    return max(lengths)


def draw_tree(G, output_dir, name):
    pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    labels = nx.get_node_attributes(G, "label")

    plt.figure(figsize=(18, 14))
    plt.figure(figsize=(100, 80))
    nx.draw(G, pos, with_labels=False, node_size=400)

    for node, (x, y) in pos.items():
        plt.text(
            x +1 ,
            y + 2,  # shift downward in display units
            labels.get(node, ""),
            rotation = 42,
            fontsize=12,
            ha="center",
            va="top"  # align text top to the shifted position
        )

    plt.axis("off")
  #  nx.draw_networkx_labels(G, pos, labels, font_size=9)
    plt.title("Hybrid Macro Categories + Subtrees")
   # plt.tight_layout()
    file = name+".png"
    path = os.path.join(output_dir, file)
    plt.savefig(path, format="png", bbox_inches="tight")
   # plt.show()
   plt.close()
#
# def render_subgraph_to_svg(G, path):
#     pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
#     labels = nx.get_node_attributes(G, "label")
#
#     plt.figure(figsize=(18, 14))
#     nx.draw(G, pos, with_labels=False, node_size=2000)
#
#     for node, (x, y) in pos.items():
#         plt.text(x, y, labels.get(node, ""), fontsize=9, ha="center", va="center")
#
#     plt.axis("off")
#     plt.tight_layout()
#     plt.savefig(path, format="png", bbox_inches="tight")
#     plt.close()
#
#
# def paginate_subtree_by_depth(G, root, max_depth=3):
#     pages = []
#     current_nodes = {root}
#     frontier = [(root, 0)]
#
#     while frontier:
#         node, depth = frontier.pop(0)
#         if depth < max_depth:
#             for child in G.successors(node):
#                 current_nodes.add(child)
#                 frontier.append((child, depth + 1))
#
#     pages.append(G.subgraph(current_nodes).copy())
#     return pages
#
#
# def paginate_subtree_by_size(G, root, max_nodes=100):
#     nodes = list(nx.descendants(G, root) | {root})
#     pages = []
#
#     for i in range(0, len(nodes), max_nodes):
#         chunk = nodes[i:i + max_nodes]
#         pages.append(G.subgraph(chunk).copy())
#
#     return pages
#
#
# def export_forest_to_html(G, output_dir="forest_html", max_nodes=100):
#     os.makedirs(output_dir, exist_ok=True)
#
#     roots = [n for n in G.nodes() if G.in_degree(n) == 0]
#     index_links = []
#
#     for i, root in enumerate(roots, 1):
#         label = G.nodes[root].get("label", root)
#         pages = paginate_subtree_by_size(G, root, max_nodes=max_nodes)
#
#         for j, subG in enumerate(pages, 1):
#             svg_path = os.path.join(output_dir, f"tree_{i}_page_{j}.svg")
#             html_path = os.path.join(output_dir, f"tree_{i}_page_{j}.html")
#
#             render_subgraph_to_svg(subG, svg_path)
#             svg_to_html(svg_path, html_path, title=f"{label} (page {j})")
#
#             index_links.append((label, f"tree_{i}_page_{j}.html"))
#
#     # Index page
#     index_html = "<h1>Hierarchy Browser</h1><ul>"
#     for label, link in index_links:
#         index_html += f'<li><a href="{link}">{label}</a></li>'
#     index_html += "</ul>"
#
#     with open(os.path.join(output_dir, "index.html"), "w") as f:
#         f.write(index_html)


if __name__ == "__main__":
    phrases = [
        "neural network",
        "deep learning model",
        "support vector machine",
        "convolutional neural network",
        "credit card fraud",
        "bank transaction fraud",
        "insurance fraud detection",
        "cyber security attack",
        "malware detection",
        "ransomware attack",
        "electric vehicle",
        "autonomous driving system",
        "fuel efficient car"
    ]

    output_dir = "/Users/piek/Desktop/Diabetes/code/event-centric-knowledgegraphs-from-conversations/output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    G = build_hybrid_tree(phrases, k=3)
    draw_tree(G, output_dir, "test")

    roots = get_roots(G)
    for root in roots:
        subtree = extract_subtree_with_depth(G, root, max_depth=0)
        label = subtree.nodes[root].get("label")
        draw_tree(subtree, output_dir, label)
