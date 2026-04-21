from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import networkx as nx

TimeBlock = Tuple[int, int]  # (day, block)


@dataclass(frozen=True)
class Section:
  course_id: str
  section_id: str
  teacher: str
  campus: str
  times: Set[TimeBlock]


def conflict_reason(a: Section, b: Section) -> List[TimeBlock]:
  # Return sorted list of overlapping (day, block) between two sections.
  overlap = a.times & b.times
  return sorted(overlap)


def build_conflict_graph(sections: List[Section]) -> nx.Graph:
  """
  Build an undirected conflict graph:
  - node = section_id
  - edge between two nodes if their times overlap
  - edge attribute 'reason' = list of overlapping (day, block)
  - node attributes include course_id, teacher, campus, times
  """
  G = nx.Graph()

  # Add nodes with attributes
  for s in sections:
    G.add_node(
      s.section_id,
      course_id=s.course_id,
      teacher=s.teacher,
      campus=s.campus,
      times=sorted(list(s.times)),
    )

  # Add conflict edges
  n = len(sections)
  for i in range(n):
    for j in range(i + 1, n):
      a, b = sections[i], sections[j]
      overlap = a.times & b.times
      if overlap:
        G.add_edge(a.section_id, b.section_id, reason=sorted(list(overlap)))

  return G


def edges_with_reasons(G: nx.Graph) -> List[Dict]:
  # Return edges as a list of dicts for display.
  out = []
  for u, v, data in G.edges(data=True):
    out.append(
      {
        "u": u,
        "v": v,
        "reason": data.get("reason", []),
      }
    )
  return out