import pandas as pd
import streamlit as st

from src.time_utils import parse_times
from src.conflict_graph import Section, build_conflict_graph
from src.solver import find_top_k_solutions
from src.scoring import Weights, score_solution

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 4（偏好评分 + Top-3 智能排序）")

DATA_PATH = "data/sample_sections.csv"

# ---- Load data ----
df = pd.read_csv(DATA_PATH)

required_cols = {"course_id", "section_id", "teacher", "campus", "times"}
missing = required_cols - set(df.columns)
if missing:
  st.error(f"CSV 缺少列：{sorted(missing)}")
  st.stop()

sections = []
for _, row in df.iterrows():
  sections.append(
    Section(
      course_id=str(row["course_id"]),
      section_id=str(row["section_id"]),
      teacher=str(row["teacher"]),
      campus=str(row["campus"]),
      times=parse_times(str(row["times"])),
    )
  )

# ---- Build candidates ----
candidates_by_course = {}
for s in sections:
  candidates_by_course.setdefault(s.course_id, []).append(s)

# ---- Sidebar: preferences ----
st.sidebar.header("偏好设置（Weights & Teacher Preference）")

w_teacher = st.sidebar.slider("老师偏好权重", 0.0, 5.0, 2.0, 0.5)
w_early = st.sidebar.slider("不早八惩罚权重", 0.0, 5.0, 1.5, 0.5)
w_night = st.sidebar.slider("不晚课惩罚权重", 0.0, 5.0, 1.0, 0.5)
w_compact = st.sidebar.slider("集中上课权重", 0.0, 5.0, 1.0, 0.5)
w_cross = st.sidebar.slider("少跨区惩罚权重", 0.0, 5.0, 1.0, 0.5)

weights = Weights(
  w_teacher=w_teacher,
  w_early=w_early,
  w_night=w_night,
  w_compact=w_compact,
  w_cross=w_cross,
)

st.sidebar.markdown("---")
st.sidebar.subheader("老师偏好（简单版：给老师打分）")

teachers = sorted({s.teacher for s in sections})
teacher_pref = {}
for t in teachers:
  teacher_pref[t] = st.sidebar.slider(f"{t} 偏好分", 0.0, 5.0, 3.0, 0.5)

# ---- Phase 2 (optional stats) ----
G = build_conflict_graph(sections)
with st.expander("冲突图统计", expanded=False):
  col1, col2 = st.columns(2)
  col1.metric("节点数（sections）", G.number_of_nodes())
  col2.metric("边数（冲突边）", G.number_of_edges())

# ---- Phase 3: generate feasible solutions ----
st.subheader("先生成可行解（硬约束：不冲突）")
k_candidates = st.slider("先生成多少个可行解候选（越大越可能找到更高分方案）", 1, 30, 10, 1)

solutions = find_top_k_solutions(candidates_by_course, k=k_candidates)

if len(solutions) == 0:
  st.error("没有找到任何可行方案（数据冲突太多）。")
  st.stop()

st.success(f"已生成 {len(solutions)} 个可行候选解。接下来按偏好评分并选 Top-3。")

# ---- Phase 4: score and rank ----
scored = []
for sol in solutions:
  breakdown = score_solution(sol, weights=weights, teacher_pref=teacher_pref)
  scored.append((breakdown.total, breakdown, sol))

scored.sort(key=lambda x: x[0], reverse=True)

top_n = 3
top = scored[: min(top_n, len(scored))]

st.subheader("Top-3 推荐方案（软约束：偏好优化 + 分项解释）")

for rank, (total, breakdown, sol) in enumerate(top, start=1):
  st.markdown(f"## 推荐方案 #{rank}  —  总分：{total:.2f}")

  # show breakdown
  bcol1, bcol2, bcol3, bcol4, bcol5 = st.columns(5)
  bcol1.metric("老师分", f"{breakdown.teacher_score:.1f}")
  bcol2.metric("早八惩罚", f"-{breakdown.early_penalty:.0f}")
  bcol3.metric("晚课惩罚", f"-{breakdown.night_penalty:.0f}")
  bcol4.metric("集中分", f"+{breakdown.compact_score:.0f}")
  bcol5.metric("跨区惩罚", f"-{breakdown.cross_penalty:.0f}")

  # show chosen sections
  rows = []
  for course_id, sec in sol.chosen_by_course.items():
    rows.append(
      {
        "course_id": course_id,
        "section_id": sec.section_id,
        "teacher": sec.teacher,
        "campus": sec.campus,
        "times": sorted(list(sec.times)),
      }
    )
  st.dataframe(pd.DataFrame(rows), width="stretch")

st.caption(
    "说明：我们先用回溯生成若干可行候选解（硬约束），再用加权评分函数排序（软约束），输出Top-3。"
)