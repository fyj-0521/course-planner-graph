from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from src.conflict_graph import Section

TimeBlock = Tuple[int, int]


@dataclass
class Solution:
  # A solution selects exactly one section per course (in this simplified version).
  chosen_by_course: Dict[str, Section]  # course_id -> chosen Section


def _conflicts(a: Section, b: Section) -> bool:
  return len(a.times & b.times) > 0


def _course_order(candidates_by_course: Dict[str, List[Section]]) -> List[str]:
  """
  Choose an ordering of courses to improve backtracking efficiency.
  Heuristic: courses with fewer candidates first (MRV heuristic).
  """
  return sorted(candidates_by_course.keys(), key=lambda c: len(candidates_by_course[c]))


def find_top_k_solutions(
  candidates_by_course: Dict[str, List[Section]],
  k: int = 3,
) -> List[Solution]:
  """
  Find up to k feasible solutions:
  - choose exactly one section per course
  - no time conflicts between chosen sections

  Backtracking + pruning:
  - order courses by fewest candidates first
  - prune when a course has no candidate that can fit
  """
  course_ids = _course_order(candidates_by_course)

  solutions: List[Solution] = []
  chosen: Dict[str, Section] = {}
  chosen_sections: List[Section] = []  # for quick conflict checks

  def can_choose(sec: Section) -> bool:
    for s in chosen_sections:
      if _conflicts(sec, s):
        return False
    return True

  def backtrack(i: int) -> None:
    # stop early if we already found k
    if len(solutions) >= k:
      return

    # if assigned all courses, record solution
    if i == len(course_ids):
      solutions.append(Solution(chosen_by_course=dict(chosen)))
      return

    course = course_ids[i]
    candidates = candidates_by_course[course]

    # Simple pruning: if no candidate fits, return
    any_fit = False
    for sec in candidates:
      if can_choose(sec):
        any_fit = True
        break
    if not any_fit:
      return

    # Try candidates
    for sec in candidates:
      if not can_choose(sec):
        continue
      chosen[course] = sec
      chosen_sections.append(sec)
      backtrack(i + 1)
      chosen_sections.pop()
      chosen.pop(course, None)

  backtrack(0)
  return solutions