import pandas as pd
import networkx as nx
from pyvis.network import Network

print("Loading cleaned data...")
# Read the pristine data we just created
df = pd.read_csv('cleaned_recipes.csv')

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

# The "gravity" physics engine
net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=100, spring_strength=0.05, damping=0.09)

# Only graph ingredients that appear in at least 10 recipes
# (You can change this to 15 or 20 if your browser struggles)
MIN_APPEARANCES = 10 

valid_nodes = set()

for node in G.nodes():
    weight = G.nodes[node]['weight']
    
    if weight < MIN_APPEARANCES:
        continue 
        
    # Scale the bubble size based on popularity
    size = 10 + (weight * 0.5) 
    net.add_node(node, label=node, size=size, title=f"Used in {weight} recipes", color='#00d2ff')
    valid_nodes.add(node) 

MIN_CONNECTIONS = 100

# Draw the connecting lines
for edge in G.edges():
    if edge[0] in valid_nodes and edge[1] in valid_nodes:
        weight = G[edge[0]][edge[1]]['weight']
        # Thicker lines for ingredients that frequently appear together
        net.add_edge(edge[0], edge[1], value=weight, color='#555555')

        # THE FIX: Skip weak connections
        if weight < MIN_CONNECTIONS:
            continue
            
        net.add_edge(edge[0], edge[1], value=weight, color='#555555')        

# Save it as a standalone HTML file
net.show('index.html', notebook=False, local=True)

print("SUCCESS! Open 'index.html' in your web browser to see your galaxy.")