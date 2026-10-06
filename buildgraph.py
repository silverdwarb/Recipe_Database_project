import pandas as pd
import networkx as nx
from pyvis.network import Network
import re

print("Loading data...")
df = pd.read_csv('cookwell_recipes.csv')

G = nx.Graph()

print("Building the ingredient web...")
for index, row in df.iterrows():
    ingredients_str = str(row['Ingredients'])
    ingredients = ingredients_str.split(' | ')
    
    cleaned_ingredients = []
    for ing in ingredients:
        # Remove numbers, extra punctuation, and lowercase
        clean = re.sub(r'\d+', '', ing).strip().lower().rstrip(',')
        # Remove common filler words that ruin the graph
        if clean and len(clean) > 2 and clean not in ['optional', 'serving', 'garnish', 'water']: 
            cleaned_ingredients.append(clean)
            
    cleaned_ingredients = list(set(cleaned_ingredients))
    
    for ing in cleaned_ingredients:
        if G.has_node(ing):
            G.nodes[ing]['weight'] += 1
        else:
            G.add_node(ing, weight=1)
            
    for i in range(len(cleaned_ingredients)):
        for j in range(i + 1, len(cleaned_ingredients)):
            ing1 = cleaned_ingredients[i]
            ing2 = cleaned_ingredients[j]
            if G.has_edge(ing1, ing2):
                G[ing1][ing2]['weight'] += 1
            else:
                G.add_edge(ing1, ing2, weight=1)

print(f"Graph built! {G.number_of_nodes()} ingredients, {G.number_of_edges()} connections.")

# ==========================================
# TURN ON THE PHYSICS (Pyvis)
# ==========================================
print("Rendering interactive galaxy...")

net = Network(height='100vh', width='100%', bgcolor='#121212', font_color='white')

# Adjusted physics for better stability
net.barnes_hut(gravity=-2000, central_gravity=0.3, spring_length=100, spring_strength=0.05, damping=0.09)

# FIX 2: Only add nodes that appear in AT LEAST 3 recipes
MIN_APPEARANCES = 10

valid_nodes = set()

for node in G.nodes():
    weight = G.nodes[node]['weight']
    
    if weight < MIN_APPEARANCES:
        continue 
        
    size = 10 + (weight * 2) 
    net.add_node(node, label=node, size=size, title=f"Used in {weight} recipes", color='#00d2ff')
    
    # Add the node name to our valid list
    valid_nodes.add(node) 

# Add edges, but only if BOTH ingredients are in our valid list
for edge in G.edges():
    weight = G[edge[0]][edge[1]]['weight']
    
    # FIX: Check our set instead of using net.has_node()
    if edge[0] in valid_nodes and edge[1] in valid_nodes:
        net.add_edge(edge[0], edge[1], value=weight, color='#555555')

# local=True forces pyvis to save the JS library inside the HTML file!
net.show('index.html', notebook=False, local=True)

print("SUCCESS! Open 'index.html' in your web browser.")