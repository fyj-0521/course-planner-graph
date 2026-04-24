from __future__ import annotations

import json
from typing import Dict, List, Tuple

import networkx as nx


def _to_cytoscape_elements(
    G: nx.Graph,
    chosen_nodes: set[str],
) -> List[Dict]:
    """
    Convert NetworkX graph to Cytoscape elements.
    - node id = section_id
    - node label shows section_id (you can improve later)
    - chosen nodes get a class 'chosen'
    - edges include reason (overlap blocks)
    """
    elements: List[Dict] = []

    for n, data in G.nodes(data=True):
        elements.append(
            {
                "data": {
                    "id": n,
                    "label": n,
                    "course_id": data.get("course_id", ""),
                    "teacher": data.get("teacher", ""),
                    "campus": data.get("campus", ""),
                },
                "classes": "chosen" if n in chosen_nodes else "",
            }
        )

    for u, v, data in G.edges(data=True):
        reason = data.get("reason", [])
        # reason is list of (day, block); convert to string like "1-1,1-2"
        reason_str = ",".join([f"{d}-{b}" for (d, b) in reason]) if reason else ""
        elements.append(
            {
                "data": {
                    "id": f"{u}__{v}",
                    "source": u,
                    "target": v,
                    "reason": reason_str,
                }
            }
        )

    return elements


def build_cytoscape_html(
    G: nx.Graph,
    chosen_nodes: set[str],
    height_px: int = 560,
) -> str:
    """
    Return an HTML string embedding Cytoscape.js with:
    - interactive graph (pan/zoom/drag)
    - click node to set window.location.hash = '#selected=<node_id>'
    - click background clears selection
    """
    elements = _to_cytoscape_elements(G, chosen_nodes)
    elements_json = json.dumps(elements)

    html = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <script src="https://unpkg.com/cytoscape@3.27.0/dist/cytoscape.min.js"></script>
  <style>
    #cy {{
      width: 100%;
      height: {height_px}px;
      border: 1px solid #ddd;
      border-radius: 10px;
    }}
    body {{
      margin: 0;
      padding: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }}
  </style>
</head>
<body>
  <div id="cy"></div>
  <script>
    const elements = {elements_json};

    const cy = cytoscape({{
      container: document.getElementById('cy'),
      elements: elements,
      style: [
        {{
          selector: 'node',
          style: {{
            'label': 'data(label)',
            'font-size': 10,
            'text-valign': 'center',
            'text-halign': 'center',
            'width': 28,
            'height': 28,
            'background-color': '#888',
            'color': '#fff'
          }}
        }},
        {{
          selector: 'node.chosen',
          style: {{
            'background-color': '#1f77b4'
          }}
        }},
        {{
          selector: 'edge',
          style: {{
            'width': 2,
            'line-color': '#bbb',
            'target-arrow-color': '#bbb',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }}
        }},
        {{
          selector: 'node:selected',
          style: {{
            'border-width': 3,
            'border-color': '#ff7f0e'
          }}
        }},
        {{
          selector: 'edge.highlight',
          style: {{
            'line-color': '#ff7f0e',
            'width': 4
          }}
        }},
        {{
          selector: 'node.highlight',
          style: {{
            'background-color': '#ff7f0e'
          }}
        }}
      ],
      layout: {{ name: 'cose', animate: false }}
    }});

    function clearHighlights() {{
      cy.nodes().removeClass('highlight');
      cy.edges().removeClass('highlight');
    }}

    cy.on('tap', 'node', function(evt) {{
      clearHighlights();
      const node = evt.target;
      const nodeId = node.id();

      // highlight neighbors
      node.addClass('highlight');
      node.connectedEdges().addClass('highlight');
      node.neighborhood().addClass('highlight');

      // communicate selection back via URL hash
      window.location.hash = 'selected=' + encodeURIComponent(nodeId);
    }});

    cy.on('tap', function(evt) {{
      if (evt.target === cy) {{
        clearHighlights();
        window.location.hash = '';
      }}
    }});
  </script>
</body>
</html>
"""
    return html