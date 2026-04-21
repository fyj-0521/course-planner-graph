import pandas as pd
import streamlit as st

from src.time_utils import parse_times
from src.conflict_graph import Section, build_conflict_graph, edges_with_reasons

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 2（冲突判定 + 冲突图构建）")

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

# ---- Build conflict graph ----
G = build_conflict_graph(sections)

st.subheader("冲突图统计（Graph Stats）")
col1, col2, col3 = st.columns(3)
col1.metric("节点数（sections）", G.number_of_nodes())
col2.metric("边数（冲突边）", G.number_of_edges())
col3.metric("平均度数（avg degree）", round(sum(dict(G.degree()).values()) / max(1, G.number_of_nodes()), 2))

# ---- Show conflict edges with reasons ----
st.subheader("冲突边列表（带原因：重叠的 day-block）")
edges = edges_with_reasons(G)
if len(edges) == 0:
  st.success("没有检测到冲突边（这通常意味着样例数据没有时间重叠）。")
else:
  edges_df = pd.DataFrame(edges)
  st.dataframe(edges_df, width="stretch")

# ---- Simple query: pick a section and show its conflicts ----
st.subheader("点选一个 section，看它和谁冲突（以及冲突原因）")
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