from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

from src.conflict_graph import Section
from src.solver import Solution

TimeBlock = Tuple[int, int]  # (day, block)


@dataclass
class Weights:
  w_teacher: float = 1.0
  w_early: float = 1.0
  w_night: float = 1.0
  w_compact: float = 1.0
  w_cross: float = 1.0


@dataclass
class ScoreBreakdown:
  teacher_score: float
  early_penalty: float
  night_penalty: float
  compact_score: float
  cross_penalty: float
  total: float


def _sections_in_solution(sol: Solution) -> List[Section]:
  return list(sol.chosen_by_course.values())


def teacher_score(sol: Solution, teacher_pref: Dict[str, float]) -> float:
  """
  Sum preference scores by teacher name.
  If a teacher is not in teacher_pref, default 0.
  """
  score = 0.0
  for sec in _sections_in_solution(sol):
    score += float(teacher_pref.get(sec.teacher, 0.0))
  return score


def early_penalty(sol: Solution) -> float:
  """
  Penalize early classes: block=1 counts as early.
  Penalty = number of (day,1) blocks used in the schedule.
  """
  used: Set[TimeBlock] = set()
  for sec in _sections_in_solution(sol):
    used |= sec.times
  return float(sum(1 for (d, b) in used if b == 1))


def night_penalty(sol: Solution) -> float:
  """
  Penalize night classes: block=6 counts as night.
  Penalty = number of (day,6) blocks used in the schedule.
  """
  used: Set[TimeBlock] = set()
  for sec in _sections_in_solution(sol):
    used |= sec.times
  return float(sum(1 for (d, b) in used if b == 6))


def compact_score(sol: Solution) -> float:
  """
  Reward compactness: fewer distinct days is better (higher score).
  Simple version:
    compact_score = 6 - (#distinct days used)
  Because your schedule typically spans at most 5 days, this stays positive.
  """
  used: Set[TimeBlock] = set()
  for sec in _sections_in_solution(sol):
    used |= sec.times
  days = {d for (d, b) in used}
  return float(6 - len(days))


def cross_penalty(sol: Solution) -> float:
  """
  Penalize cross-campus moves.
  Simple version:
  - For each day, look at chosen classes in increasing block order.
  - Count transitions where campus changes between consecutive classes that day.
  """
  # day -> list of (block, campus)
  by_day: Dict[int, List[Tuple[int, str]]] = {}
  for sec in _sections_in_solution(sol):
    for (d, b) in sec.times:
      by_day.setdefault(d, []).append((b, sec.campus))

  penalty = 0
  for d, items in by_day.items():
    items_sorted = sorted(items, key=lambda x: x[0])
    for i in range(1, len(items_sorted)):
      prev_campus = items_sorted[i - 1][1]
      cur_campus = items_sorted[i][1]
      if cur_campus != prev_campus:
        penalty += 1
  return float(penalty)


def score_solution(
  sol: Solution,
  weights: Weights,
  teacher_pref: Dict[str, float],
) -> ScoreBreakdown:
  ts = teacher_score(sol, teacher_pref)
  ep = early_penalty(sol)
  np = night_penalty(sol)
  cs = compact_score(sol)
  cp = cross_penalty(sol)

  total = (
    weights.w_teacher * ts
    - weights.w_early * ep
    - weights.w_night * np
    + weights.w_compact * cs
    - weights.w_cross * cp
  )

  return ScoreBreakdown(
    teacher_score=ts,
    early_penalty=ep,
    night_penalty=np,
    compact_score=cs,
    cross_penalty=cp,
    total=total,
  )