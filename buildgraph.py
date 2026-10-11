import pandas as pd
import networkx as nx
from pyvis.network import Network

print("Loading cleaned data...")
# Read the pristine data we just created
df = pd.read_csv('cleaned_recipes.csv')

# Load your new categorized file
print("Loading ingredient categories...")
df_categories = pd.read_csv('build_vis_categorized.csv')

# Create a fast lookup dictionary: {'salt': {'Count': 868, 'Category': 'Seasoning'}}
# We lowercase the index so it matches your cleaned ingredients perfectly
category_lookup = df_categories.set_index('Ingredient')[['Count', 'Category']].to_dict('index')
category_lookup = {k.lower(): v for k, v in category_lookup.items()}

# Define your color palette (Hex codes)
COLOR_PALETTE = {
    'Protein': '#ff4d4d',      # Red
    'Vegetable': '#4dff4d',    # Green
    'Seasoning': '#ffffff',    # White
    'Carb': '#ffd700',         # Gold/Yellow
    'Dairy': '#e6e6fa',        # Lavender/Light Purple
    'Fat/Oil': '#ffa500',      # Orange
    'Liquid': '#00bfff',       # Deep Sky Blue
    'Other': '#00d2ff'         # Default Cyan
}

G = nx.Graph()

print("Building the ingredient web...")
for index, row in df.iterrows():
    # The ingredients are already perfectly clean and separated by ' | '
    ingredients = str(row['ingredients']).split(' | ')
    
    # 1. Add Nodes (Ingredients) and count their frequency
    for ing in ingredients:
        if G.has_node(ing):
            G.nodes[ing]['weight'] += 1
        else:
            G.add_node(ing, weight=1)
            
    # 2. Add Edges (Connections) between ingredients in the same recipe
    for i in range(len(ingredients)):
        for j in range(i + 1, len(ingredients)):
            ing1 = ingredients[i]
            ing2 = ingredients[j]
            
            if G.has_edge(ing1, ing2):
                G[ing1][ing2]['weight'] += 1
            else:
                G.add_edge(ing1, ing2, weight=1)

print(f"Graph built! {G.number_of_nodes()} ingredients, {G.number_of_edges()} connections.")

# ==========================================
# TURN ON THE PHYSICS (Pyvis)
# ==========================================
print("Rendering interactive galaxy...")

# Dark space theme
net = Network(height='100vh', width='100%', bgcolor='#121212', font_color='white')

# ==========================================
# MASTER OPTIONS BLOCK
# ==========================================
options = """
{
    "edges": {
        "smooth": false
    },
    "physics": {
        "barnesHut": {
            "gravitationalConstant": -2000,
            "centralGravity": 0.3,
            "springLength": 1000,
            "springConstant": 0.04,
            "damping": 0.7,
            "avoidOverlap": 1
        },
        "stabilization": {
            "enabled": true,
            "iterations": 1000,
            "updateInterval": 25
        }
    }
}
"""
net.set_options(options)

# Only graph ingredients that appear in at least 5 recipes
MIN_APPEARANCES = 5 
MIN_CONNECTIONS = 4

# ==========================================
# THE EXCLUDE LIST
# ==========================================
# We hide these from the graph to prevent the "black hole" effect.
EXCLUDE_INGREDIENTS = {'salt', 'water'}
# ==========================================

valid_nodes = set()

# 1. ADD NODES (Colored by Category)
for node in G.nodes():
    if node in EXCLUDE_INGREDIENTS:
        continue
        
    weight = G.nodes[node]['weight']
    if weight < MIN_APPEARANCES:
        continue 
        
    # Look up the category and get the color
    node_data = category_lookup.get(node, {'Category': 'Other'})
    category = node_data['Category']
    color = COLOR_PALETTE.get(category, '#00d2ff') # Fallback to cyan if category is missing
    
    size = 10 + (weight * 0.5) 
    # Added category to the hover title!
    title = f"{node} | {category} | Used in {weight} recipes"
        
    net.add_node(node, label=node, size=size, title=title, color=color)
    valid_nodes.add(node) 

# 2. ADD EDGES (Colored by the Dominant Ingredient)
for edge in G.edges():
    if edge[0] in EXCLUDE_INGREDIENTS or edge[1] in EXCLUDE_INGREDIENTS:
        continue
        
    if edge[0] in valid_nodes and edge[1] in valid_nodes:
        weight = G[edge[0]][edge[1]]['weight']
        
        if weight < MIN_CONNECTIONS:
            continue
            
        # Find out which ingredient has the higher count
        count1 = category_lookup.get(edge[0], {}).get('Count', 0)
        count2 = category_lookup.get(edge[1], {}).get('Count', 0)
        
        # The "dominant" ingredient dictates the line color
        dominant_ing = edge[0] if count1 >= count2 else edge[1]
        dom_category = category_lookup.get(dominant_ing, {}).get('Category', 'Other')
        edge_color = COLOR_PALETTE.get(dom_category, '#555555')
            
        net.add_edge(edge[0], edge[1], value=weight, color=edge_color)


print('minimum apperances', MIN_APPEARANCES,'minimum connections',MIN_CONNECTIONS)

# Inject custom CSS to fix the ugly loading bar
net.html = net.html.replace(
    '<div id="loadingBar">', 
    '<style>#loadingBar {background-color: #2a2a2a !important; border-radius: 10px !important; padding: 5px !important; width: 300px !important; margin: auto !important; position: absolute !important; top: 20px !important; left: 50% !important; transform: translateX(-50%) !important;} #loadingBar .border {background-color: #00d2ff !important; border-radius: 5px !important;}</style><div id="loadingBar">'
)

net.show('index.html', notebook=False, local=True)

# Save it as a standalone HTML file
net.show('index.html', notebook=False, local=True)

print("SUCCESS! Open 'index.html' in your web browser to see your galaxy.")