# Words to Hierarchy (words_to_hierarchy.py)

This module provides functionality for creating hierarchical tree structures from lists of phrases using
semantic similarity and clustering techniques.

## Dependencies

- sentence_transformers
- sklearn
- scipy
- networkx
- matplotlib
- re
- os

## Main Features

### Core Functions

#### normalize_phrase(p: str) -> str
Normalizes a given phrase by converting to lowercase, stripping whitespace, and standardizing spacing.

#### extract_keywords(phrases, top_k=2)
Extracts the most significant keywords from a collection of phrases using TF-IDF vectorization.
- `phrases`: List of input phrases
- `top_k`: Number of top keywords to extract (default: 2)
- Returns: Comma-separated string of top keywords

#### build_hybrid_tree(phrases, k=3, model_name="all-MiniLM-L6-v2")
Builds a hierarchical tree structure from phrases using a two-stage clustering approach:
1. Macro clustering to group similar phrases
2. Subtree creation within each macro group
- `phrases`: List of input phrases
- `k`: Number of macro clusters (default: 3)
- `model_name`: Name of the sentence transformer model (default: "all-MiniLM-L6-v2")
- Returns: NetworkX DiGraph representing the hierarchy

#### build_hybrid_tree_with_single_word_parents(phrases, k=3, model_name="all-MiniLM-L6-v2")
Similar to build_hybrid_tree but with special handling for single-word phrases:
- Single-word phrases become direct children of macro nodes
- Multi-word phrases are attached to matching single-word parents when possible
- Remaining multi-word phrases form their own subtree

### Utility Functions

#### get_roots(G)
Returns list of root nodes (nodes with no incoming edges) in the graph.

#### extract_subtree_with_depth(G, root, max_depth=2)
Extracts a subtree from the graph starting at the given root up to specified depth.

#### get_tree_depth(G, root)
Calculates the maximum depth of the tree from the root to any leaf.

#### draw_tree(G, output_dir, name)
Visualizes the tree structure using matplotlib and saves it as a PNG file:
- Creates a directional graph layout
- Adds labels for nodes
- Saves the visualization to the specified output directory

## Usage Example
```
python
phrases = [
    "neural network",
    "deep learning model",
    "support vector machine",
    "convolutional neural network",
    "credit card fraud",
    "bank transaction fraud",
    "insurance fraud detection"
]

# Create output directory
output_dir = "output"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Build and visualize the tree
G = build_hybrid_tree(phrases, k=3)
draw_tree(G, output_dir, "test")

# Generate subtree visualizations for each root
roots = get_roots(G)
for root in roots:
    subtree = extract_subtree_with_depth(G, root, max_depth=0)
    label = subtree.nodes[root].get("label")
    draw_tree(subtree, output_dir, label)
    
```
## Output

The script generates:
1. A main tree visualization showing the complete hierarchy
2. Individual visualizations for each macro cluster
3. PNG files saved in the specified output directory

## Notes

- Uses sentence transformers for semantic similarity
- Employs agglomerative clustering for grouping similar phrases
- Generates both macro-level categories and detailed subtrees
- Supports visualization of complex hierarchical relationships
```