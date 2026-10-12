import pandas as pd
import networkx as nx
from pyvis.network import Network
import json


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

# Helper function to convert Hex colors to RGB for transparency
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def get_most_connected_neighbor(G, node, valid_edges):
    """Find the neighbor with the strongest connection to this node"""
    max_weight = 0
    best_neighbor = None
    
    for edge in valid_edges:
        if edge[0] == node:
            weight = G[edge[0]][edge[1]]['weight']
            if weight > max_weight:
                max_weight = weight
                best_neighbor = edge[1]
        elif edge[1] == node:
            weight = G[edge[0]][edge[1]]['weight']
            if weight > max_weight:
                max_weight = weight
                best_neighbor = edge[0]
    
    return best_neighbor, max_weight

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


# ==========================================
# PASS 1: Find all valid nodes and valid edges
# ==========================================
valid_nodes = set()
valid_edges = []

for node in G.nodes():
    if node in EXCLUDE_INGREDIENTS: continue
    weight = G.nodes[node]['weight']
    if weight < MIN_APPEARANCES: continue
    valid_nodes.add(node)

for edge in G.edges():
    if edge[0] in EXCLUDE_INGREDIENTS or edge[1] in EXCLUDE_INGREDIENTS: continue
    if edge[0] in valid_nodes and edge[1] in valid_nodes:
        weight = G[edge[0]][edge[1]]['weight']
        if weight < MIN_CONNECTIONS: continue
        valid_edges.append(edge)

# ==========================================
# PASS 2: Only keep nodes that actually have connections!
# ==========================================
connected_nodes = set()
for edge in valid_edges:
    connected_nodes.add(edge[0])
    connected_nodes.add(edge[1])

# Add Nodes to Pyvis (Only the connected ones!)
for node in connected_nodes:
    weight = G.nodes[node]['weight']
    node_data = category_lookup.get(node, {'Category': 'Other'})
    category = node_data['Category']
    color = COLOR_PALETTE.get(category, '#00d2ff')
    
    size = 10 + (weight * 0.5) 
    title = f"{node} | {category} | Used in {weight} recipes"
    net.add_node(node, label=node, size=size, title=title, color=color)

max_weight = max([G[edge[0]][edge[1]]['weight'] for edge in valid_edges]) if valid_edges else MIN_CONNECTIONS
min_weight = MIN_CONNECTIONS

# Add Edges to Pyvis
for edge in valid_edges:
    weight = G[edge[0]][edge[1]]['weight']

    # Calculate opacity (alpha). 
    # Minimum is 0.25 (25% visible), Maximum is 0.95 (95% visible)
    if max_weight > min_weight:
        alpha = 0.2+0.8*((weight - min_weight) / (max_weight - min_weight))
    else:
        alpha = 0.25
    
    count1 = category_lookup.get(edge[0], {}).get('Count', 0)
    count2 = category_lookup.get(edge[1], {}).get('Count', 0)
    
    dominant_ing = edge[0] if count1 >= count2 else edge[1]
    dom_category = category_lookup.get(dominant_ing, {}).get('Category', 'Other')
    hex_color = COLOR_PALETTE.get(dom_category, '#555555')
    
    # Convert Hex to RGBA
    r, g, b = hex_to_rgb(hex_color)
    rgba_color = f"rgba({r}, {g}, {b}, {alpha:.2f})"
        
    net.add_edge(edge[0], edge[1], value=weight, color=rgba_color)

print('minimum apperances', MIN_APPEARANCES,'minimum connections',MIN_CONNECTIONS)

# ==========================================
# INJECT INFO PANEL & INTERACTIVE JAVASCRIPT
# ==========================================

# Pre-calculate the most connected neighbor for each node
node_connections = {}
for node in connected_nodes:
    best_neighbor, weight = get_most_connected_neighbor(G, node, valid_edges)
    node_connections[node] = {
        'best_neighbor': best_neighbor,
        'connection_strength': weight,
        'total_connections': sum(1 for e in valid_edges if e[0] == node or e[1] == node)
    }

# ==========================================
# INJECT INFO PANEL & INTERACTIVE JAVASCRIPT
# ==========================================

# Pre-calculate the most connected neighbor for each node
node_connections = {}
for node in connected_nodes:
    best_neighbor, weight = get_most_connected_neighbor(G, node, valid_edges)
    node_connections[node] = {
        'best_neighbor': best_neighbor,
        'connection_strength': weight,
        'total_connections': sum(1 for e in valid_edges if e[0] == node or e[1] == node)
    }

# Convert the Python dictionary to a JSON string so JavaScript can read it safely
connections_json = json.dumps(node_connections)

# Use standard triple quotes (NO 'f' at the start) so Python ignores the JavaScript curly braces!
info_panel_html = """
<div id="infoPanel" style="
    position: fixed;
    top: 80px;
    left: 20px;
    background: rgba(30, 30, 30, 0.95);
    border: 2px solid #00d2ff;
    border-radius: 12px;
    padding: 20px;
    width: 280px;
    color: white;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 14px;
    box-shadow: 0 4px 20px rgba(0, 210, 255, 0.3);
    z-index: 9999;
    backdrop-filter: blur(10px);
">
    <h3 style="margin: 0 0 15px 0; color: #00d2ff; font-size: 18px; border-bottom: 1px solid #444; padding-bottom: 10px;">
        📊 Ingredient Network
    </h3>
    <div id="panelContent" style="line-height: 1.6;">
        <p style="color: #aaa; font-style: italic; margin: 0;">
            Hover over a node to see ingredient details and connections
        </p>
    </div>
</div>

<script>
function updatePanel(nodeId) {
    var panelContent = document.getElementById('panelContent');
    
    if (!nodeId) {
        panelContent.innerHTML = '<p style="color: #aaa; font-style: italic; margin: 0;">Hover over a node to see ingredient details and connections</p>';
        return;
    }
    
    var nodeData = window.nodeConnections[nodeId] || {};
    var bestNeighbor = nodeData.best_neighbor || 'N/A';
    var connStrength = nodeData.connection_strength || 0;
    var totalConns = nodeData.total_connections || 0;
    
    var networkObj = window.network;
    var nodesArray = networkObj ? networkObj.body.nodes : {};
    var node = nodesArray[nodeId];
    
    var category = 'Unknown';
    var count = 0;
    
    if (node && node.options && node.options.title) {
        var titleParts = node.options.title.split(' | ');
        if (titleParts.length >= 2) {
            category = titleParts[1].trim();
        }
        if (titleParts.length >= 3) {
            count = titleParts[2].replace('Used in ', '').replace(' recipes', '');
        }
    }
    
    // Notice the ${} syntax here! This is JavaScript template literals.
    panelContent.innerHTML = `
        <div style="margin-bottom: 15px;">
            <div style="color: #00d2ff; font-size: 20px; font-weight: bold; margin-bottom: 5px;">
                ${nodeId}
            </div>
            <div style="color: #888; font-size: 12px; text-transform: uppercase; letter-spacing: 1px;">
                ${category}
            </div>
        </div>
        
        <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
            <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">Appears In</div>
            <div style="color: #fff; font-size: 16px; font-weight: bold;">${count} recipes</div>
        </div>
        
        <div style="background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
            <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">Total Connections</div>
            <div style="color: #fff; font-size: 16px; font-weight: bold;">${totalConns} ingredients</div>
        </div>
        
        <div style="background: rgba(0, 210, 255, 0.1); padding: 12px; border-radius: 8px; border-left: 3px solid #00d2ff;">
            <div style="color: #666; font-size: 11px; text-transform: uppercase; margin-bottom: 5px;">Strongest Connection</div>
            <div style="color: #00d2ff; font-size: 16px; font-weight: bold;">${bestNeighbor}</div>
            <div style="color: #888; font-size: 12px; margin-top: 5px;">Co-occur in ${connStrength} recipes</div>
        </div>
    `;
}

// Inject the Python dictionary as a JSON object
window.nodeConnections = """ + connections_json + """;

updatePanel(null);

setTimeout(function() {
    if (window.network) {
        window.network.on("hoverNode", function(params) {
            updatePanel(params.node);
        });
        window.network.on("blurNode", function(params) {
            updatePanel(null);
        });
    }
}, 1000);
</script>
"""

# Inject the panel into the HTML right before the body closes
net.html = net.html.replace('</body>', info_panel_html + '</body>')

# Fix the ugly loading bar
net.html = net.html.replace(
    '<div id="loadingBar">', 
    '<style>#loadingBar {background-color: #2a2a2a !important; border-radius: 10px !important; padding: 5px !important; width: 300px !important; margin: auto !important; position: absolute !important; top: 20px !important; left: 50% !important; transform: translateX(-50%) !important; z-index: 10000;} #loadingBar .border {background-color: #00d2ff !important; border-radius: 5px !important;}</style><div id="loadingBar">'
)

net.show('index.html', notebook=False, local=True)
print("SUCCESS! Open 'index.html' in your web browser to see your galaxy with the interactive info panel!")