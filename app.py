import pandas as pd
import streamlit as st

from src.time_utils import parse_times
from src.conflict_graph import Section, build_conflict_graph, edges_with_reasons
from src.solver import find_top_k_solutions

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 3（Top-3 可行方案：回溯 + 剪枝）")

DATA_PATH = "data/sample_sections.csv"

# ---- Load data ----
df = pd.read_csv(DATA_PATH)

required_cols = {"course_id", "section_id", "teacher", "campus", "times"}
missing = required_cols - set(df.columns)
if missing:
  st.error(f"CSV 缺少列：{sorted(missing)}")
  st.stop()

# ---- Parse into Section objects ----
sections = []
for _, row in df.iterrows():
  s = Section(
    course_id=str(row["course_id"]),
    section_id=str(row["section_id"]),
    teacher=str(row["teacher"]),
    campus=str(row["campus"]),
    times=parse_times(str(row["times"])),
  )
  sections.append(s)

st.subheader("原始数据（sections）")
st.dataframe(df, width="stretch")

# ---- Phase 2: Build conflict graph ----
G = build_conflict_graph(sections)

with st.expander("Phase 2：冲突图统计与冲突边列表（点击展开）", expanded=False):
  col1, col2, col3 = st.columns(3)
  col1.metric("节点数（sections）", G.number_of_nodes())
  col2.metric("边数（冲突边）", G.number_of_edges())
  col3.metric(
    "平均度数（avg degree）",
    round(sum(dict(G.degree()).values()) / max(1, G.number_of_nodes()), 2),
  )

  edges = edges_with_reasons(G)
  if len(edges) == 0:
    st.success("没有检测到冲突边（这通常意味着样例数据没有时间重叠）。")
  else:
    st.dataframe(pd.DataFrame(edges), width="stretch")

  st.write("点选一个 section，看它和谁冲突（以及冲突原因）")
  all_sections = sorted(list(G.nodes()))
  picked = st.selectbox("选择 section", all_sections)
  neighbors = list(G.neighbors(picked))
  if not neighbors:
    st.info(f"{picked} 没有与任何 section 冲突。")
  else:
    rows = []
    for nb in neighbors:
      reason = G.edges[picked, nb].get("reason", [])
      rows.append({"conflicts_with": nb, "reason": reason})
    st.dataframe(pd.DataFrame(rows), width="stretch")

# ---- Phase 3: Build candidates_by_course ----
candidates_by_course = {}
for s in sections:
  candidates_by_course.setdefault(s.course_id, []).append(s)

st.subheader("Phase 3：生成 Top-3 可行选课方案（每门课选一个 section，且时间不冲突）")
st.caption("算法：回溯（Backtracking）+ 剪枝（MRV：候选最少的课优先）")

k = st.slider("输出方案数量（Top-k）", min_value=1, max_value=5, value=3, step=1)

solutions = find_top_k_solutions(candidates_by_course, k=k)

if len(solutions) == 0:
  st.error("没有找到任何可行方案（可能是数据冲突太多或必须选的课太多）。")
else:
  st.success(f"找到 {len(solutions)} 个可行方案（最多 {k} 个）。")

  for idx, sol in enumerate(solutions, start=1):
    st.markdown(f"### 方案 #{idx}")
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