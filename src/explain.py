from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import networkx as nx

from src.conflict_graph import Section
from src.solver import Solution
from src.scoring import Weights, score_solution

TimeBlock = Tuple[int, int]


@dataclass
class Explanation:
  title: str
  bullets: List[str]


def _format_blocks(blocks: List[TimeBlock]) -> str:
  return ", ".join([f"{d}-{b}" for (d, b) in blocks])


def explain_solution(
  sol: Solution,
  weights: Weights,
  teacher_pref: Dict[str, float],
) -> Explanation:
  """
  Explain why this solution scores well (or not):
  - show key contributions: favorite teachers chosen, early/night blocks used, days used, cross-campus moves.
  """
  bd = score_solution(sol, weights=weights, teacher_pref=teacher_pref)
  chosen = list(sol.chosen_by_course.values())

  # Teachers chosen
  teacher_parts = []
  for s in chosen:
    tscore = teacher_pref.get(s.teacher, 0.0)
    teacher_parts.append(f"{s.course_id}: {s.teacher}（偏好分 {tscore}）")
  teacher_line = "、".join(teacher_parts)

  # Early/Night blocks
  used_blocks = set()
  for s in chosen:
    used_blocks |= s.times
  early = sorted([(d, b) for (d, b) in used_blocks if b == 1])
  night = sorted([(d, b) for (d, b) in used_blocks if b == 6])
  days = sorted({d for (d, b) in used_blocks})

  bullets = [
    f"老师贡献（按你给的偏好分）：{teacher_line}",
    f"早八出现 {int(bd.early_penalty)} 次：{_format_blocks(early) if early else '无'}",
    f"晚课出现 {int(bd.night_penalty)} 次：{_format_blocks(night) if night else '无'}",
    f"使用上课天数 {len(days)} 天：{days}",
    f"跨区切换次数：{int(bd.cross_penalty)}",
    f"分项：老师 {bd.teacher_score:.1f}，早八 -{bd.early_penalty:.0f}，晚课 -{bd.night_penalty:.0f}，集中 +{bd.compact_score:.0f}，跨区 -{bd.cross_penalty:.0f}",
    f"总分：{bd.total:.2f}",
  ]
  return Explanation(title="为什么推荐这个方案（可解释分解）", bullets=bullets)


def explain_why_section_not_chosen(
  target_section_id: str,
  solution: Solution,
  section_by_id: Dict[str, Section],
  G: nx.Graph,
) -> Explanation:
  """
  Explain why a specific section wasn't chosen in the given solution:
  - if it's not chosen, list which chosen sections conflict with it (with overlap blocks).
  """
  chosen_sections = list(solution.chosen_by_course.values())
  chosen_ids = {s.section_id for s in chosen_sections}

  if target_section_id in chosen_ids:
    return Explanation(
      title="该 section 已被选中",
      bullets=[f"{target_section_id} 已在当前方案中。"],
    )

  if target_section_id not in section_by_id:
    return Explanation(
      title="找不到该 section",
      bullets=[f"{target_section_id} 不在数据中。"],
    )

  # Conflicts with chosen sections
  conflicts = []
  for s in chosen_sections:
    if G.has_edge(target_section_id, s.section_id):
      reason = G.edges[target_section_id, s.section_id].get("reason", [])
      conflicts.append((s.section_id, s.course_id, reason))

  if not conflicts:
    return Explanation(
      title="该 section 未被选中（但它与当前方案不冲突）",
      bullets=[
        "它与当前方案选中的 section 没有时间冲突。",
        "未被选中通常是因为：该课程已选了另一个 section，或偏好评分更高的替代项存在。",
      ],
    )

  bullets = ["它没被选中的主要原因：与当前方案中的以下已选 section 时间冲突："]
  for sec_id, course_id, reason in conflicts:
    bullets.append(f"- 冲突对象：{course_id} 的 {sec_id}；重叠时间块：{_format_blocks(reason)}")

  return Explanation(title="为什么没选这个 section（冲突解释）", bullets=bullets)