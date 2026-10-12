# Culinary Network Analysis — Project Documentation & AI Handoff Context

**Project:** Cookwell Recipe Database / Culinary Network Analysis  
**Interactive demo:** https://silverdwarb.github.io/Recipe_Database_project/  
**Repository roadmap:** https://github.com/silverdwarb/Recipe_Database_project#-future-expansion--roadmap  
**Purpose of this document:** Serve as project documentation and as the context file to provide at the beginning of a future AI-assisted development session.

---

## 1. Quick context for a new AI session

The project is an interactive ingredient co-occurrence network built from scraped recipes. Python handles the prepared CSV data, graph construction, filtering thresholds, and node/edge attributes. NetworkX represents the network, PyVis generates the browser visualization, and custom HTML/CSS/JavaScript is injected into the generated page to provide UI controls.

### Non-negotiable development constraints

1. **Treat `cleaned_recipes.csv` as already cleaned.** A separate pipeline creates it. Do not add another general-purpose cleaning pass to the graph builder unless explicitly asked.
2. **Preserve the delimiter exactly.** The cleaned ingredient string uses ` | ` (pipe with spaces). The intended graph-builder split is `str(row['ingredients']).split(' | ')`. Do not replace this with a more elaborate cleanup/deduplication pipeline without first confirming a data need.
3. **Make minimal, targeted edits.** The user prefers additions to the existing script over a broad rewrite. Explain exactly which block to replace or where to insert code.
4. **Do not change graph semantics casually.** Node weights count recipe appearances; edge weights count recipes containing both ingredients. Thresholds, exclusions, and category rules affect the analysis and should not be changed just to improve visual performance without explaining the trade-off.
5. **Keep the graph and UI concerns separate.** The Python graph represents the data. JavaScript controls browser interactions. Category filters are intended to hide category nodes and all edges touching them; opacity-only filtering was considered but the user decided not to implement it.
6. **Keep the sidebar behavior.** Hover previews an ingredient; clicking pins its information; clicking the empty graph clears the pin. Connected ingredients are ranked by shared-recipe count, largest first.
7. **Preserve the lightweight roadmap link.** The preferred interface is a small fixed corner box reading approximately: `Version number: 1.0 | For future updates, click here`, linking to the repository's roadmap anchor. Do not recreate the larger roadmap modal unless requested.
8. **Do not claim runtime validation unless it happened.** Syntax checks are not the same as running the full program with both CSV files or testing the deployed page in a browser.

### Recommended opening prompt

> Read this project context before proposing changes. Help me modify the existing Culinary Network Analysis project with the smallest reliable change. Preserve the already-cleaned CSV pipeline, the ` | ` delimiter, the current graph semantics and thresholds, and the existing UI unless I explicitly request a change. First explain which section needs changing and why. Prefer a focused code block or a patch over a full-file rewrite. Clearly separate verified behavior from assumptions, and do not claim that code has been run with the real CSVs unless it has.

---

## 2. Project purpose and current concept

The project evolved from a web-scraping exercise into an interactive tool for examining the co-occurrence structure of recipes. Ingredients are represented as nodes, and an edge links two ingredients when they appear together in one or more recipes. Node size represents how often an ingredient appears; edge weight represents how often a pair appears together. Category-based colors make the graph easier to scan.

The network can be used to investigate culinary patterns such as common pairings, protein-centered clusters, or ingredients that bridge otherwise separate groups. These are exploratory interpretations of co-occurrence, not proof of causation, flavor compatibility, or a chef's intent.

### Current user-facing experience

- Dark, physics-based interactive ingredient graph.
- Ingredient colors assigned from macro-categories: Protein, Vegetable, Seasoning, Carb, Dairy, Fat/Oil, Liquid, and Other.
- Category filter panel on the left with checkboxes plus Select all and Clear all.
- Ingredient details panel on the right.
- Hover preview and click-to-pin selection.
- Ranked list of an ingredient's connected neighbors, based on shared recipe count.
- Intended removal of PyVis's built-in navigation arrows (`navigationButtons: false`).
- Intended full-screen, slightly dimmed loading overlay with a centered progress bar. The overlay must still allow PyVis to hide it at completion; avoid forcing `display:flex !important` on `#loadingBar`.
- Preferred roadmap UI: compact version-number text/link box that opens the GitHub README roadmap in a new tab.

The exact local script and deployed page should be checked before changing these details. Several iterations were discussed, and generated script copies may not contain the user's latest local edits.

---

## 3. Architecture and data flow

```text
Source recipe websites
        |
        v
Scraping and source-specific extraction
        |
        v
Cleaning / repair scripts
  - buildvis.py (cleaning logic discussed in project history)
  - fix_csv.py (targeted repair for 'low fat' scraping issue)
  - clean_data.py (dedicated canonical cleaning output)
        |
        +------------------------------+
        |                              |
        v                              v
cleaned_recipes.csv             build_vis_categorized.csv
(recipe_id, title, ingredients) (Ingredient, Count, Category)
        |                              |
        +---------------+--------------+
                        v
              Python graph builder
              pandas + NetworkX
                        |
                        v
              Thresholded graph
                        |
                        v
              PyVis HTML generation
                        |
                        v
         Inject custom HTML/CSS/JavaScript
                        |
                        v
                    index.html
                        |
                        v
              GitHub Pages live demo
```

The graph-building script reads two CSVs:

### `cleaned_recipes.csv`
The canonical recipe-level dataset produced by the separate cleaning pipeline. The documented schema is `recipe_id`, `title`, and `ingredients`. The graph builder primarily uses the `ingredients` column; title and recipe ID are retained for future analysis and traceability.

The `ingredients` field is already cleaned and separated using ` | `. Do not assume that raw ingredient text or original scraper output is being loaded at this stage.

### `build_vis_categorized.csv`
Used to map each ingredient to a category and to obtain a `Count` used when choosing a dominant category for coloring edges. Expected columns in the graph script are:

- `Ingredient`
- `Count`
- `Category`

Category lookup is case-normalized to help match ingredients, while graph labels are displayed as they appear in the cleaned recipe file.

---

## 4. Data preparation history and decisions

These details explain why the data pipeline is separated from graph construction:

- **Cleaning order:** `JUNK_PHRASES` checks were moved before a regex that removes text after `for`. This avoided chopping junk phrases at the word `for` and allowing their remnants through the filter.
- **Manual long-tail review:** The `MIN_COUNT = 5` filter was temporarily removed during inspection so rare ingredients could be reviewed before deciding what to exclude.
- **Low-fat scraper bug:** An early scraper rule accidentally removed `fat` from phrases like `low fat cream`, leaving `low-`. Instead of re-scraping, a targeted regex patch in `fix_csv.py` used `low-(?![a-zA-Z])` to repair the damaged entries without changing valid terms such as `low-moisture`.
- **Stray characters:** Word-boundary matching such as `\bx\b` and simple replacements were used to remove stray `x` and `+` tokens remaining after measurement stripping.
- **Single source of truth:** The project moved toward a dedicated `clean_data.py` output named `cleaned_recipes.csv` rather than putting all cleaning inside the visualization builder. The canonical cleaned dataset is intended for graphing, future SQL migration, and other analyses.
- **Scraper configuration:** `scraper_config.py` was adjusted to remove dangerous generic terms such as `FAT` from `FLAVOR_WORDS` and to move website UI terms into `NAV_JUNK`.

When extending the pipeline, avoid using broad regex substitutions that could damage valid ingredient names. Prefer targeted rules, inspect affected rows, and keep repairs reproducible.

---

## 5. Graph model and filtering rules

### Meaning of the graph

- **Node:** one ingredient.
- **Node weight:** number of recipe rows containing that ingredient.
- **Edge:** an undirected relationship between two ingredients appearing in the same recipe.
- **Edge weight:** number of recipes in which both ingredients appear together.
- **Node size:** current formula in the reviewed script is `10 + (count * 0.5)`.
- **Edge opacity:** currently computed from the edge weight, with a low baseline and stronger co-occurrence displayed more opaquely. This is styling; it does not alter the edge weight.
- **Edge color:** based on the category color of the ingredient with the larger `Count` value in `build_vis_categorized.csv`.

This construction uses pairwise combinations within each recipe. A recipe containing `k` distinct ingredients contributes `k(k-1)/2` possible pairs. This can make graph-building and browser rendering expensive for a large corpus.

### Visual graph thresholds

In the graph-builder code examined during this conversation, the settings were:

```python
MIN_APPEARANCES = 5
MIN_CONNECTIONS = 4
EXCLUDE_INGREDIENTS = {"salt", "water"}
```

The builder first identifies valid nodes, then valid edges, then retains only nodes that participate in a valid edge. This two-pass design avoids isolated nodes after weak edges are removed. Salt and water remain in the underlying recipe data but are excluded from the displayed network because highly ubiquitous ingredients can dominate the layout and contribute to the “black hole” / hairball effect.

**Configuration-history warning:** the supplied project summary describes an earlier iteration with `MIN_CONNECTIONS = 5`, `springLength = 200`, and `damping = 0.6`. The script versions inspected during this conversation instead showed `MIN_CONNECTIONS = 4`, `springLength = 1000`, and `damping = 0.7`. Treat the current local Python script as the source of truth; these values changed across iterations and should not be silently reconciled by an AI assistant.

### Physics and layout history

Important visual fixes described in the project history:

- Node size multiplier reduced from `* 2` to `* 0.5` to address the giant-node / blue-blob issue.
- Curved edges disabled (`"smooth": false`) to reduce overlapping loops and favor a geometric constellation appearance.
- Salt and water removed from the displayed graph to reduce gravitational centralization.
- `avoidOverlap` increased and `damping` adjusted during tuning to encourage a more spread-out, stable graph.
- A two-pass node/edge filter eliminates orphan nodes from the rendered view.

Physics settings alter layout and performance, not the underlying co-occurrence counts. Avoid changing several physics parameters at once; test changes one at a time.

---

## 6. Browser UI and interaction behavior

The custom UI is injected into the HTML produced by PyVis. Python prepares the data and markup; browser-side JavaScript responds to user interaction.

### Category filter panel

- Each displayed category gets a checkbox and color swatch.
- Select all and Clear all toggle the checkbox states.
- In the currently implemented filtering approach, unchecking a category hides its nodes and all edges for which either endpoint is in that category.
- This is **not** the opacity-only behavior discussed later. The user decided not to implement opacity-only category filtering because the visual benefit did not seem worth the change.
- Re-enabling the category makes its nodes and edges visible again.

### Ingredient information panel

- Hovering an ingredient previews its details.
- Clicking a node pins its details.
- Clicking the empty graph unpins the selection.
- The panel shows ingredient name, category, number of recipes containing it, number of visible connections, and a list of connected ingredients.
- Neighbor rows are ordered by edge weight descending (shared-recipe count); ingredient name is a tie-breaker in the prepared list.
- Clicking a neighbor row selects/focuses that neighbor.
- Category filters also affect the neighbor list so it reflects enabled categories.

### Filter performance issue

The script version inspected in the conversation loops through every node and every edge and calls `DataSet.update()` for each item on every filter change. On a large graph this can cause a multi-second delay. A low-risk optimization is to gather changed records and call `nodeDataSet.update(arrayOfChanges)` / `edgeDataSet.update(arrayOfChanges)` in batches, optionally skipping elements whose `hidden` state is already correct. This should be tested with the actual graph and browser; no guaranteed speedup should be claimed until measured.

Opacity-only filtering was considered: set affected edge RGBA alpha to zero while leaving nodes visible. It was not chosen for implementation. If revisited, be careful to preserve original edge colors and make sidebar counts consistent with the intended definition of a “visible connection.”

### HTML generation / injection

A key integration detail is to generate the page first, inject custom UI, then write the final file. The reviewed code uses the pattern:

```python
html_document = net.generate_html()
html_document = html_document.replace("</body>", ui_html + "\n</body>")
output_path.write_text(html_document, encoding="utf-8")
```

Do not call a `net.show()` path that regenerates HTML after modifying a previously generated document; that can overwrite injected UI in some PyVis versions. Keep the custom CSS/HTML/JavaScript injection after `generate_html()` and before writing `index.html`.

### Loading overlay

A full-viewport translucent overlay was requested so the page looks slightly dimmed while the network loads, with the progress bar centered. Important implementation caveat: PyVis needs to be able to hide `#loadingBar` on completion. A CSS declaration like `display: flex !important` can override PyVis's JavaScript that attempts to set `display: none`. Use flex centering without `!important` on the overlay's `display` property, and verify the loading bar disappears after reaching 100%.

### Navigation arrows

The built-in PyVis arrow controls were considered clutter. Set this option to false to remove them:

```json
"interaction": {
  "hover": true,
  "navigationButtons": false,
  "keyboard": true
}
```

### Compact version / roadmap link

Preferred final design: a small fixed corner box, not a large modal. The text should read approximately:

`Version number: 1.0 | For future updates, click here`

The link destination is:

https://github.com/silverdwarb/Recipe_Database_project#-future-expansion--roadmap

When using the `html_document` approach, inject the snippet after `html_document = net.generate_html()` and before writing the file. Do not insert duplicate version boxes if one is already present.

---

## 7. Major issues resolved / lessons learned

### Hairball and universal ingredients
Salt and water were excluded from the visualization because they appeared with many other ingredients and visually dominated the network. The data was not deleted from the canonical CSV; only the displayed graph excludes them.

### Giant node sizing
The node size multiplier was reduced from `* 2` to `* 0.5`, producing more manageable node sizes.

### Threshold logic and edge duplication
An inverted conditional caused edges to be filtered incorrectly, and an earlier double-add issue drew edges before the filter was applied. The intended sequence is: identify valid nodes, identify valid edges, collect endpoints of valid edges, then add nodes and edges to PyVis.

### Python f-strings and JavaScript templates
Embedding JavaScript template literals with `${...}` inside Python f-strings can make Python try to interpret JavaScript variables and fail with `NameError`. Avoid making the large HTML/JavaScript template an f-string unless interpolation is intentionally escaped. Prepare JSON with `json.dumps()` and substitute explicit placeholders such as `__NODE_INFO__` after defining the static template.

### GitHub Pages case sensitivity
GitHub Pages runs on a case-sensitive filesystem. Image and screenshot paths must match capitalization exactly. Lowercase directory/file names were adopted to avoid image 404 errors.

---

## 8. Deployment and repository context

- Repository: https://github.com/silverdwarb/Recipe_Database_project
- Interactive deployment: https://silverdwarb.github.io/Recipe_Database_project/
- Roadmap section: https://github.com/silverdwarb/Recipe_Database_project#-future-expansion--roadmap
- Local graph output: `index.html`

The documented deployment flow is to regenerate the HTML from the graph builder and publish the updated `index.html` to the repository/Pages site. If a deployed page does not reflect code changes, verify that the correct generated file was committed and pushed, then refresh the site without relying on a stale browser cache.

### Roadmap

**Version 1.0 — Adjustable Cookwell Database (current baseline)**
- End-to-end scrape and clean pipeline.
- Macro-categorization and color-coded ingredient network.
- Physics tuning to reduce the hairball effect.
- Category filtering and interactive ingredient exploration were added during the later UI work in this conversation.

**Version 2.0 — Author-centric analysis (e.g., Serious Eats)**
- Expand scraping to additional culinary sources.
- Extract author/chef metadata per recipe.
- Compare ingredient-network structures between authors.
- Compare networks over time, such as 2020 versus 2026.

**Version 3.0 — Cross-platform and temporal analysis**
- Migrate canonical CSV data to a relational SQL database.
- Expand the deployed visualization for broader public use and/or a different app host if needed.
- Identify signature pairings associated with particular culinary creators.

The README roadmap is the public-facing plan. A few checklist states in historical drafts are stale: for example, category filtering was listed as pending in the supplied Qwen summary, but a filter panel was later implemented in the scripts discussed here. Update public checkboxes deliberately when confirmed in the live repository.

---

## 9. Recommended structure for future changes

When adding a feature, prefer this order:

1. **State the user-facing behavior precisely.** Example: “Unchecking Dairy hides Dairy nodes and every edge touching Dairy; it does not remove anything from the CSV.”
2. **Identify the layer involved.** Data cleaning, graph-building, graph styling, injected markup, JavaScript behavior, or deployment.
3. **Change the smallest relevant section.** Avoid rewriting the working graph builder for a browser-only request.
4. **Preserve the current graph semantics.** If thresholds or counts must change, explain the analytical consequence first.
5. **Validate incrementally.** Check Python syntax; run with both real CSVs; record node/edge counts; open `index.html`; test filters, hover/click pinning, the loading overlay, and the roadmap link; then check the GitHub Pages build.
6. **Report limitations honestly.** Say whether code was only reviewed, syntax-checked, run against sample data, run against actual CSVs, or tested in the browser.

### Useful regression checks

- Input schemas/delimiter are correct; graph counts are plausible; every displayed node has at least one qualifying edge.
- Filters hide/reveal the intended nodes and touching edges; hover/pin/unpin works; sidebar neighbors rank by shared-recipe count descending.
- Loading overlay disappears at 100%; navigation arrows are absent; the version box and deployed page match the correct roadmap URL and latest committed files.

---

## 10. Source-of-truth and uncertainty notes

This document combines the supplied Qwen project summary with the development conversation and review of script copies available during the conversation. They represent multiple iterations, not necessarily one synchronized current working tree.

When an instruction in this document conflicts with the user's latest message or latest local code, use the latest explicit user instruction and inspect the active script before making changes. In particular:

- Treat the cleaned CSV and exact delimiter as authoritative.
- Do not assume values from older tuning passes are still active.
- Do not assume an assistant-generated downloadable script was adopted into the user's local repository.
- Do not claim the filter's batching optimization, final full-screen overlay, or compact version box is live unless the active script and deployed page confirm it.
- The current intended category filter remains hide/show, not opacity-only.

