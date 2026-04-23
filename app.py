import pandas as pd
import streamlit as st

from src.time_utils import parse_times
from src.conflict_graph import Section, build_conflict_graph
from src.solver import find_top_k_solutions
from src.scoring import Weights, score_solution
from src.explain import explain_solution, explain_why_section_not_chosen

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 5（可解释推荐 + 交互式冲突视图）")

DATA_PATH = "data/sample_sections.csv"

# ---- Load ----
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

section_by_id = {s.section_id: s for s in sections}

# ---- Build candidates ----
candidates_by_course = {}
for s in sections:
  candidates_by_course.setdefault(s.course_id, []).append(s)

# ---- Sidebar ----
st.sidebar.header("偏好设置（Weights & Teacher Preference）")

w_teacher = st.sidebar.slider("老师偏好权重", 0.0, 5.0, 2.0, 0.5)
w_early = st.sidebar.slider("不早八惩罚", 0.0, 5.0, 1.5, 0.5)
w_night = st.sidebar.slider("不晚课惩罚", 0.0, 5.0, 1.0, 0.5)
w_compact = st.sidebar.slider("集中上课权重", 0.0, 5.0, 1.0, 0.5)
w_cross = st.sidebar.slider("少跨区惩罚", 0.0, 5.0, 1.0, 0.5)

weights = Weights(
  w_teacher=w_teacher,
  w_early=w_early,
  w_night=w_night,
  w_compact=w_compact,
  w_cross=w_cross,
)

st.sidebar.markdown("---")
st.sidebar.subheader("老师偏好（给老师打分）")
teachers = sorted({s.teacher for s in sections})
teacher_pref = {}
for t in teachers:
  teacher_pref[t] = st.sidebar.slider(f"{t} 偏好分", 0.0, 5.0, 3.0, 0.5)

# ---- Conflict graph ----
G = build_conflict_graph(sections)

with st.expander("冲突图统计", expanded=False):
  col1, col2 = st.columns(2)
  col1.metric("节点数（sections）", G.number_of_nodes())
  col2.metric("边数（冲突边）", G.number_of_edges())

# ---- Generate candidates ----
st.subheader("生成可行候选解（硬约束：不冲突）")
k_candidates = st.slider("候选解数量（越大越可能更优）", 1, 50, 15, 1)
solutions = find_top_k_solutions(candidates_by_course, k=k_candidates)

if len(solutions) == 0:
  st.error("没有找到任何可行方案（数据冲突太多）。")
  st.stop()

# ---- Score and pick Top-3 ----
scored = []
for sol in solutions:
  breakdown = score_solution(sol, weights=weights, teacher_pref=teacher_pref)
  scored.append((breakdown.total, breakdown, sol))
scored.sort(key=lambda x: x[0], reverse=True)

top_n = min(3, len(scored))
top = scored[:top_n]

st.subheader("Top-3 推荐方案（可解释）")
st.caption("你可以点选某个推荐方案，然后查看：①为什么推荐它；②为什么没选某个 section。")

# Choose which solution to inspect
labels = [f"推荐方案 #{i+1}（总分 {top[i][0]:.2f}）" for i in range(top_n)]
picked_idx = st.radio("选择要查看解释的方案", options=list(range(top_n)), format_func=lambda i: labels[i])
total, breakdown, sol = top[picked_idx]

# Show chosen schedule
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

# Explanation panel
ex = explain_solution(sol, weights=weights, teacher_pref=teacher_pref)
st.markdown(f"### {ex.title}")
for b in ex.bullets:
  st.write(f"- {b}")

st.markdown("---")
st.subheader("解释查询：为什么没选某个 section？（冲突/取舍）")
all_section_ids = sorted(section_by_id.keys())
target = st.selectbox("选择一个你关心的 section", all_section_ids)

ex2 = explain_why_section_not_chosen(target, sol, section_by_id=section_by_id, G=G)
st.markdown(f"### {ex2.title}")
for b in ex2.bullets:
  st.write(b)