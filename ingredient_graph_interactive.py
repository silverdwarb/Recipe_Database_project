import html
import json
from pathlib import Path

import networkx as nx
import pandas as pd
from pyvis.network import Network


# ---------------------------------------------------------------------------
# 1. Load the already-cleaned recipe data and ingredient categories
# ---------------------------------------------------------------------------
print("Loading cleaned data...")
df = pd.read_csv("cleaned_recipes.csv")

print("Loading ingredient categories...")
df_categories = pd.read_csv("build_vis_categorized.csv")

if "ingredients" not in df.columns:
    raise ValueError(
        "cleaned_recipes.csv must contain an 'ingredients' column. "
        f"Columns found: {list(df.columns)}"
    )

required_category_columns = {"Ingredient", "Count", "Category"}
missing_category_columns = required_category_columns.difference(df_categories.columns)
if missing_category_columns:
    raise ValueError(
        "build_vis_categorized.csv is missing these columns: "
        f"{sorted(missing_category_columns)}. "
        f"Columns found: {list(df_categories.columns)}"
    )

# Use lowercase lookup keys so capitalization differences don't break category
# matching. Ingredient labels in the graph itself are left as they appear in
# the cleaned recipe file.
category_lookup = {}
for _, row in df_categories.iterrows():
    ingredient = str(row["Ingredient"]).strip()
    if not ingredient or ingredient.lower() == "nan":
        continue

    category_value = row["Category"]
    if pd.isna(category_value) or not str(category_value).strip():
        category_value = "Other"
    else:
        category_value = str(category_value).strip()

    count_value = pd.to_numeric(row["Count"], errors="coerce")
    category_lookup[ingredient.lower()] = {
        "Count": 0 if pd.isna(count_value) else float(count_value),
        "Category": category_value,
    }

COLOR_PALETTE = {
    "Protein": "#ff4d4d",      # Red
    "Vegetable": "#4dff4d",    # Green
    "Seasoning": "#ffffff",    # White
    "Carb": "#ffd700",         # Gold/yellow
    "Dairy": "#e6e6fa",        # Lavender
    "Fat/Oil": "#ffa500",      # Orange
    "Liquid": "#00bfff",       # Deep sky blue
    "Other": "#00d2ff",        # Cyan fallback
}


def get_category(ingredient):
    """Return an ingredient category, defaulting to Other."""
    return category_lookup.get(ingredient.strip().lower(), {}).get("Category", "Other")


def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


# ---------------------------------------------------------------------------
# 2. Build an ingredient co-occurrence graph
#    Node weight = number of recipes containing that ingredient.
#    Edge weight = number of recipes containing both ingredients.
# ---------------------------------------------------------------------------
G = nx.Graph()
print("Building the ingredient web...")

for _, row in df.iterrows():
    raw_ingredients = row["ingredients"]
    if pd.isna(raw_ingredients):
        continue

    # The input is already cleaned and pipe-separated. Strip whitespace and
    # deduplicate within each recipe so a repeated ingredient doesn't inflate
    # a recipe's node/edge counts.
    ingredients = str(row['ingredients']).split(' | ')


    for ingredient in ingredients:
        if G.has_node(ingredient):
            G.nodes[ingredient]["weight"] += 1
        else:
            G.add_node(ingredient, weight=1)

    for i in range(len(ingredients)):
        for j in range(i + 1, len(ingredients)):
            ingredient_a = ingredients[i]
            ingredient_b = ingredients[j]
            if G.has_edge(ingredient_a, ingredient_b):
                G[ingredient_a][ingredient_b]["weight"] += 1
            else:
                G.add_edge(ingredient_a, ingredient_b, weight=1)

print(
    f"Graph built! {G.number_of_nodes()} ingredients, "
    f"{G.number_of_edges()} connections."
)


# ---------------------------------------------------------------------------
# 3. Filter the graph using your original thresholds and exclusion list
# ---------------------------------------------------------------------------
MIN_APPEARANCES = 5
MIN_CONNECTIONS = 4
EXCLUDE_INGREDIENTS = {"salt", "water"}

valid_nodes = {
    node
    for node, data in G.nodes(data=True)
    if node.strip().lower() not in EXCLUDE_INGREDIENTS
    and data["weight"] >= MIN_APPEARANCES
}

valid_edges = [
    (a, b)
    for a, b, data in G.edges(data=True)
    if a in valid_nodes
    and b in valid_nodes
    and data["weight"] >= MIN_CONNECTIONS
]

connected_nodes = set()
for a, b in valid_edges:
    connected_nodes.add(a)
    connected_nodes.add(b)

node_categories = {node: get_category(node) for node in connected_nodes}

print(
    "Minimum appearances:", MIN_APPEARANCES,
    "| Minimum connections:", MIN_CONNECTIONS,
    "| Displayed nodes:", len(connected_nodes),
    "| Displayed edges:", len(valid_edges),
)


# ---------------------------------------------------------------------------
# 4. Calculate information for the sidebar, including ranked neighbors
# ---------------------------------------------------------------------------
node_info = {}

# Build adjacency lists from the exact set of edges rendered in the graph.
adjacency = {node: [] for node in connected_nodes}
for a, b in valid_edges:
    weight = int(G[a][b]["weight"])
    adjacency[a].append(
        {
            "name": b,
            "weight": weight,
            "category": node_categories[b],
            "recipe_count": int(G.nodes[b]["weight"]),
        }
    )
    adjacency[b].append(
        {
            "name": a,
            "weight": weight,
            "category": node_categories[a],
            "recipe_count": int(G.nodes[a]["weight"]),
        }
    )

for node in connected_nodes:
    # Highest co-occurrence count first; alphabetic ingredient name breaks ties.
    neighbors = sorted(
        adjacency[node], key=lambda item: (-item["weight"], item["name"].lower())
    )
    node_info[node] = {
        "name": node,
        "category": node_categories[node],
        "recipe_count": int(G.nodes[node]["weight"]),
        "total_connections": len(neighbors),
        "neighbors": neighbors,
    }


# ---------------------------------------------------------------------------
# 5. Create the PyVis network
# ---------------------------------------------------------------------------
net = Network(
    height="100vh",
    width="100%",
    bgcolor="#121212",
    font_color="white",
    directed=False,
)

options = """
{
  "edges": {
    "smooth": false,
    "font": {"color": "#dddddd"}
  },
  "interaction": {
    "hover": true,
    "navigationButtons": false,
    "keyboard": true
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

for node in connected_nodes:
    count = int(G.nodes[node]["weight"])
    category = node_categories[node]
    color = COLOR_PALETTE.get(category, COLOR_PALETTE["Other"])
    size = 10 + (count * 0.5)
    title = f"{node} | {category} | Used in {count} recipes"
    net.add_node(
        node,
        label=node,
        size=size,
        title=title,
        color=color,
        font={"color": "#ffffff", "size": 14},
    )

max_edge_weight = max(
    (int(G[a][b]["weight"]) for a, b in valid_edges),
    default=MIN_CONNECTIONS,
)
min_edge_weight = MIN_CONNECTIONS

for a, b in valid_edges:
    weight = int(G[a][b]["weight"])

    if max_edge_weight > min_edge_weight:
        alpha = 0.2 + 0.8 * (
            (weight - min_edge_weight) / (max_edge_weight - min_edge_weight)
        )
    else:
        alpha = 0.25

    count_a = category_lookup.get(a.strip().lower(), {}).get("Count", 0)
    count_b = category_lookup.get(b.strip().lower(), {}).get("Count", 0)
    dominant_ingredient = a if count_a >= count_b else b
    dominant_category = node_categories.get(dominant_ingredient, "Other")
    red, green, blue = hex_to_rgb(
        COLOR_PALETTE.get(dominant_category, COLOR_PALETTE["Other"])
    )
    rgba_color = f"rgba({red}, {green}, {blue}, {alpha:.2f})"

    net.add_edge(
        a,
        b,
        value=weight,
        color=rgba_color,
        title=f"Co-occurs in {weight} recipes",
    )


# ---------------------------------------------------------------------------
# 6. Build the category filter controls
# ---------------------------------------------------------------------------
active_categories = sorted(set(node_categories.values()))
filter_rows = []
for index, category in enumerate(active_categories):
    safe_category = html.escape(category, quote=True)
    swatch_color = COLOR_PALETTE.get(category, COLOR_PALETTE["Other"])
    filter_rows.append(
        '<label class="category-row">'
        f'<input type="checkbox" class="category-filter" '
        f'data-category="{safe_category}" checked>'
        f'<span class="category-swatch" style="background:{swatch_color};"></span>'
        f'<span>{html.escape(category)}</span>'
        "</label>"
    )

filter_rows_html = "\n".join(filter_rows)
node_info_json = json.dumps(node_info, ensure_ascii=False).replace("</", "<\\/")
node_categories_json = json.dumps(node_categories, ensure_ascii=False).replace("</", "<\\/")


# ---------------------------------------------------------------------------
# 7. Add sidebar and filter behavior to the generated HTML
# ---------------------------------------------------------------------------
ui_html_template = r"""
<style>
  #categoryPanel, #infoPanel {
    position: fixed;
    z-index: 9999;
    box-sizing: border-box;
    color: #f2f2f2;
    background: rgba(25, 25, 25, 0.96);
    border: 1px solid #3c3c3c;
    border-radius: 12px;
    padding: 16px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    font-size: 13px;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.45);
    backdrop-filter: blur(10px);
  }
  #categoryPanel {
    top: 20px;
    left: 20px;
    width: 225px;
    max-height: 78vh;
    overflow-y: auto;
  }
  #infoPanel {
    top: 20px;
    right: 20px;
    width: 340px;
    max-width: calc(100vw - 40px);
    max-height: 88vh;
    overflow-y: auto;
    border-color: #00aeca;
  }
  .panel-heading {
    margin: 0 0 12px 0;
    padding-bottom: 9px;
    color: #00d2ff;
    font-size: 17px;
    border-bottom: 1px solid #444;
  }
  .panel-subtext { color: #aaa; line-height: 1.45; margin: 0 0 12px 0; }
  .category-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin: 9px 0;
    cursor: pointer;
    user-select: none;
  }
  .category-row input { accent-color: #00d2ff; cursor: pointer; }
  .category-swatch {
    display: inline-block;
    width: 11px;
    height: 11px;
    border: 1px solid rgba(255,255,255,.55);
    border-radius: 3px;
    flex: 0 0 11px;
  }
  .filter-actions { display: flex; gap: 7px; margin-top: 12px; }
  .ui-button {
    border: 1px solid #4d4d4d;
    border-radius: 6px;
    background: #303030;
    color: #eee;
    padding: 6px 9px;
    cursor: pointer;
    font-size: 12px;
  }
  .ui-button:hover { background: #414141; }
  .ingredient-name { color: #00d2ff; font-size: 20px; font-weight: 700; overflow-wrap: anywhere; }
  .ingredient-category { color: #999; font-size: 11px; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }
  .stat-card { background: rgba(255,255,255,.055); padding: 10px; border-radius: 8px; margin: 12px 0; }
  .stat-label { color: #999; font-size: 10px; text-transform: uppercase; letter-spacing: .6px; margin-bottom: 4px; }
  .stat-value { color: #fff; font-size: 15px; font-weight: 650; }
  .neighbor-header { color: #00d2ff; font-weight: 650; margin: 16px 0 8px; }
  .neighbor-list { display: flex; flex-direction: column; gap: 6px; }
  .neighbor-row {
    width: 100%; box-sizing: border-box; display: flex; justify-content: space-between;
    align-items: center; gap: 8px; text-align: left; padding: 8px 9px;
    border: 1px solid #393939; border-radius: 7px; background: #222;
    color: #eee; cursor: pointer;
  }
  .neighbor-row:hover { border-color: #00aeca; background: #2b2b2b; }
  .neighbor-left { min-width: 0; overflow-wrap: anywhere; }
  .neighbor-category { display: block; color: #999; font-size: 10px; margin-top: 2px; }
  .neighbor-weight { flex: 0 0 auto; text-align: right; color: #00d2ff; font-size: 12px; font-weight: 650; }
  .empty-message { color: #aaa; font-style: italic; line-height: 1.5; }
  @media (max-width: 850px) {
    #categoryPanel { top: 10px; left: 10px; width: 190px; max-height: 42vh; }
    #infoPanel { top: auto; bottom: 10px; right: 10px; width: min(340px, calc(100vw - 220px)); max-height: 55vh; }
  }
  @media (max-width: 560px) {
    #categoryPanel { top: 8px; left: 8px; width: 165px; max-height: 38vh; padding: 10px; }
    #infoPanel { right: 8px; bottom: 8px; width: calc(100vw - 190px); max-width: none; max-height: 58vh; padding: 10px; }
    .ingredient-name { font-size: 16px; }
  }
</style>

<div id="categoryPanel">
  <h3 class="panel-heading">Filter categories</h3>
  <p class="panel-subtext">Uncheck a category to hide its nodes and all connections touching them.</p>
  <div id="categoryFilters">
    __FILTER_ROWS__
  </div>
  <div class="filter-actions">
    <button type="button" class="ui-button" id="selectAllCategories">Select all</button>
    <button type="button" class="ui-button" id="clearAllCategories">Clear all</button>
  </div>
</div>

<div id="infoPanel">
  <h3 class="panel-heading">Ingredient details</h3>
  <div id="panelContent">
    <p class="empty-message">Hover over an ingredient to preview it. Click an ingredient to keep its details here.</p>
  </div>
</div>

<script>
(function () {
  const nodeInfo = __NODE_INFO__;
  const nodeCategories = __NODE_CATEGORIES__;
  let selectedNodeId = null; // Set by clicking a graph node; remains pinned.
  let hoveredNodeId = null;  // Preview only while no node is pinned.
  let visibleCategories = new Set(
    Array.from(document.querySelectorAll('.category-filter')).map(el => el.dataset.category)
  );

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[character]);
    });
  }

  function showEmptyPanel() {
    document.getElementById('panelContent').innerHTML =
      '<p class="empty-message">Hover over an ingredient to preview it. Click an ingredient to keep its details here. Click the graph background to unpin the selection.</p>';
  }

  function renderPanel(nodeId) {
    const content = document.getElementById('panelContent');
    if (!nodeId || !nodeInfo[nodeId]) {
      showEmptyPanel();
      return;
    }

    const item = nodeInfo[nodeId];
    const visibleNeighbors = item.neighbors.filter(neighbor => visibleCategories.has(neighbor.category));
    const neighborsHtml = visibleNeighbors.map((neighbor, index) => `
      <button type="button" class="neighbor-row" data-neighbor="${escapeHtml(neighbor.name)}">
        <span class="neighbor-left">
          <span>${index + 1}. ${escapeHtml(neighbor.name)}</span>
          <span class="neighbor-category">${escapeHtml(neighbor.category)}</span>
        </span>
        <span class="neighbor-weight">${neighbor.weight}<br><span style="font-size:9px;font-weight:400;color:#999">recipes</span></span>
      </button>
    `).join('');

    content.innerHTML = `
      <div>
        <div class="ingredient-name">${escapeHtml(item.name)}</div>
        <div class="ingredient-category">${escapeHtml(item.category)}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Appears in</div>
        <div class="stat-value">${item.recipe_count} recipes</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">Visible connections</div>
        <div class="stat-value">${visibleNeighbors.length} of ${item.total_connections} ingredients</div>
      </div>
      <div class="neighbor-header">Connected ingredients, strongest first</div>
      <p class="panel-subtext">The recipe count is how often this ingredient and the listed ingredient occur together.</p>
      <div class="neighbor-list">
        ${neighborsHtml || '<p class="empty-message">No connected ingredients match the active category filters.</p>'}
      </div>
    `;

    // Allow a neighbor in the sidebar to become the pinned ingredient too.
    content.querySelectorAll('[data-neighbor]').forEach(button => {
      button.addEventListener('click', function (event) {
        event.stopPropagation();
        const neighborId = this.dataset.neighbor;
        if (nodeInfo[neighborId] && visibleCategories.has(nodeCategories[neighborId])) {
          selectedNodeId = neighborId;
          hoveredNodeId = null;
          renderPanel(selectedNodeId);
          if (window.network) {
            try {
              window.network.selectNodes([neighborId]);
              window.network.focus(neighborId, {
                scale: Math.max(window.network.getScale(), 0.7),
                animation: {duration: 350, easingFunction: 'easeInOutQuad'}
              });
            } catch (e) {
              // The sidebar selection still works if focusing isn't available.
            }
          }
        }
      });
    });
  }


function applyCategoryFilters() {
    visibleCategories = new Set(
        Array.from(document.querySelectorAll('.category-filter'))
            .filter(input => input.checked)
            .map(input => input.dataset.category)
    );

    if (!window.network ||
        !window.network.body ||
        !window.network.body.data) {
        return;
    }

    const nodeDataSet = window.network.body.data.nodes;
    const edgeDataSet = window.network.body.data.edges;

    if (!nodeDataSet || !edgeDataSet) {
        return;
    }

    // ---------------------------------------
    // 1. Calculate only the node changes
    // ---------------------------------------
    const nodeUpdates = [];

    nodeDataSet.get().forEach(node => {
        const category = nodeCategories[node.id] || 'Other';
        const shouldHide = !visibleCategories.has(category);

        // Don't update a node if its visibility is already correct.
        if (Boolean(node.hidden) !== shouldHide) {
            nodeUpdates.push({
                id: node.id,
                hidden: shouldHide
            });
        }
    });

    // Update all changed nodes in one batch.
    if (nodeUpdates.length > 0) {
        nodeDataSet.update(nodeUpdates);
    }

    // ---------------------------------------
    // 2. Calculate only the edge changes
    // ---------------------------------------
    const edgeUpdates = [];

    edgeDataSet.get().forEach(edge => {
        const fromCategory = nodeCategories[edge.from] || 'Other';
        const toCategory = nodeCategories[edge.to] || 'Other';

        // An edge is visible only when both categories are enabled.
        const shouldHide = !(
            visibleCategories.has(fromCategory) &&
            visibleCategories.has(toCategory)
        );

        // Don't update an edge if its visibility is already correct.
        if (Boolean(edge.hidden) !== shouldHide) {
            edgeUpdates.push({
                id: edge.id,
                hidden: shouldHide
            });
        }
    });

    // Update all changed edges in one batch.
    if (edgeUpdates.length > 0) {
        edgeDataSet.update(edgeUpdates);
    }

    // ---------------------------------------
    // 3. Refresh the selected ingredient panel
    // ---------------------------------------
    if (
        selectedNodeId &&
        !visibleCategories.has(nodeCategories[selectedNodeId])
    ) {
        selectedNodeId = null;
    }

    if (
        hoveredNodeId &&
        !visibleCategories.has(nodeCategories[hoveredNodeId])
    ) {
        hoveredNodeId = null;
    }

    renderPanel(selectedNodeId || hoveredNodeId);
}


  document.querySelectorAll('.category-filter').forEach(input => {
    input.addEventListener('change', applyCategoryFilters);
  });
  document.getElementById('selectAllCategories').addEventListener('click', function () {
    document.querySelectorAll('.category-filter').forEach(input => { input.checked = true; });
    applyCategoryFilters();
  });
  document.getElementById('clearAllCategories').addEventListener('click', function () {
    document.querySelectorAll('.category-filter').forEach(input => { input.checked = false; });
    applyCategoryFilters();
  });

  // PyVis normally exposes its Network as the global variable `network`.
  // `window.network` is used here because it is available from this injected script.
  function attachNetworkEvents() {
    if (!window.network || typeof window.network.on !== 'function') {
      window.setTimeout(attachNetworkEvents, 100);
      return;
    }

    window.network.on('hoverNode', function (params) {
      hoveredNodeId = params.node;
      if (!selectedNodeId) renderPanel(hoveredNodeId);
    });

    window.network.on('blurNode', function () {
      hoveredNodeId = null;
      renderPanel(selectedNodeId);
    });

    window.network.on('click', function (params) {
      if (params.nodes && params.nodes.length > 0) {
        selectedNodeId = params.nodes[0];
        hoveredNodeId = null;
        renderPanel(selectedNodeId);
      } else {
        // Clicking empty graph space releases the pinned selection.
        selectedNodeId = null;
        hoveredNodeId = null;
        renderPanel(null);
      }
    });

    applyCategoryFilters();
  }

  showEmptyPanel();
  attachNetworkEvents();
})();
</script>
"""

ui_html = (
    ui_html_template
    .replace("__FILTER_ROWS__", filter_rows_html)
    .replace("__NODE_INFO__", node_info_json)
    .replace("__NODE_CATEGORIES__", node_categories_json)
)

# Generate the HTML first, then inject controls and write it directly. This
# avoids calling net.show() after editing net.html, which can regenerate and
# overwrite the injected HTML in some PyVis versions.
html_document = net.generate_html()
html_document = html_document.replace("</body>", ui_html + "\n</body>")



# ==========================================
# FULL-SCREEN LOADING OVERLAY
# ==========================================

loading_bar_css = """
<style>
    /* Full-screen overlay */
    #loadingBar {
        position: fixed !important;
        inset: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;

        background: rgba(20, 20, 20, 0.50) !important;
        backdrop-filter: grayscale(0.25) brightness(0.75);
        -webkit-backdrop-filter: grayscale(0.25) brightness(0.75);

        /* IMPORTANT: no !important on display.
           PyVis must be able to set display:none when finished. */
        display: flex;
        align-items: center;
        justify-content: center;

        z-index: 10000 !important;
        transition: opacity 0.4s ease;
    }

    /* Responsive loading-bar container */
    #loadingBar .outerBorder {
        position: relative !important;
        top: auto !important;
        left: auto !important;
        transform: none !important;

        width: min(560px, calc(100vw - 40px)) !important;
        height: 64px !important;
        margin: 0 !important;
        padding: 8px !important;
        box-sizing: border-box !important;

        border: 2px solid #dddddd !important;
        border-radius: 20px !important;
        background: #f5f5f5 !important;
    }

    /* Center the percentage over the progress bar */
    #loadingBar #text {
        position: absolute !important;
        inset: 0 !important;
        width: 100% !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;

        display: flex !important;
        align-items: center !important;
        justify-content: center !important;

        color: #111111 !important;
        font-size: 20px !important;
        text-align: center !important;
        z-index: 2 !important;
        pointer-events: none !important;
    }

    /* Progress track */
    #loadingBar #border {
        position: absolute !important;
        left: 8px !important;
        right: 8px !important;
        top: 50% !important;
        transform: translateY(-50%) !important;

        width: auto !important;
        height: 20px !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;

        background: #e5e5e5 !important;
        border: 1px solid #cccccc !important;
        border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* Progress indicator.
       Leave width alone because PyVis updates it dynamically. */
    #loadingBar #bar {
        position: relative !important;
        top: 0 !important;
        left: 0 !important;
        height: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;

        background: #00bcd4 !important;
        border: none !important;
        border-radius: 10px !important;
    }
</style>
<div id="loadingBar">
"""

html_document = html_document.replace(
    '<div id="loadingBar">',
    loading_bar_css,
    1
)

# ==========================================
# VERSION NUMBER & FUTURE UPDATES LINK
# ==========================================

version_box_html = """
<div id="versionBox">
    Version number: 1.0 |
    <a
        href="https://github.com/silverdwarb/Recipe_Database_project#-future-expansion--roadmap"
        target="_blank"
        rel="noopener noreferrer"
    >
        For future updates, click here
    </a>
</div>

<style>
    #versionBox {
        position: fixed;
        bottom: 15px;
        right: 15px;
        z-index: 9999;

        background: rgba(25, 25, 25, 0.92);
        color: #dddddd;
        border: 1px solid #444444;
        border-radius: 8px;
        padding: 10px 14px;

        font-family: Arial, sans-serif;
        font-size: 12px;
        box-shadow: 0 3px 12px rgba(0, 0, 0, 0.35);
    }

    #versionBox a {
        color: #00d2ff;
        text-decoration: none;
    }

    #versionBox a:hover {
        text-decoration: underline;
    }
</style>
"""

html_document = html_document.replace(
    "</body>",
    version_box_html + "\n</body>",
    1
)



output_path = Path("index.html")
output_path.write_text(html_document, encoding="utf-8")
print(f"SUCCESS! Interactive graph saved to: {output_path.resolve()}")
print("Open index.html in your browser to use the category filters and ingredient sidebar.")
