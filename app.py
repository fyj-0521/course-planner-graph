import pandas as pd
import streamlit as st

from streamlit_agraph import agraph, Node, Edge, Config

from src.time_utils import parse_times
from src.conflict_graph import Section, build_conflict_graph
from src.solver import find_top_k_solutions
from src.scoring import Weights, score_solution
from src.explain import explain_solution, explain_why_section_not_chosen
# from src.cyto_html import build_cytoscape_html

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 5B（可解释推荐 + Cytospace 交互式冲突视图）")

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

st.subheader("Top-3 推荐方案（点击节点可查看解释）")

# Choose which solution to inspect
labels = [f"推荐方案 #{i+1}（总分 {top[i][0]:.2f}）" for i in range(top_n)]
picked_idx = st.radio("选择要查看解释的方案", options=list(range(top_n)), format_func=lambda i: labels[i])
total, breakdown, sol = top[picked_idx]
chosen_ids = {sec.section_id for sec in sol.chosen_by_course.values()}

# Tow-column layout
left, right = st.columns([1.15, 1])

with left:
  st.markdown("### 冲突图")
  st.caption("蓝色节点=当前方案选中的 section；点击节点会在右侧显示解释。")
  # ---- Build agraph nodes/edges ----
  nodes = []
  for n, data in G.nodes(data=True):
    is_chosen = (n in chosen_ids)
    # use difference size to differentiate chosen (maybe change to color in the future)
    nodes.append(
      Node(
        id=n,
        label=n,
        size=25 if is_chosen else 15,
        title=f"{data.get('course_id', '')} | {data.get('teacher', '')} | {data.get('campus', '')}"
      )
    )
  
  edges = []
  for u, v, data in G.edges(data=True):
    reason = data.get("reason", [])
    reason_str = ", ".join([f"{d}-{b}" for (d, b) in reason])
    edges.append(Edge(source=u, target=v, label="conflict", title=reason_str))
  
  config = Config(
    width="100%",
    height=600,
    directed=False,
    physics=True,
    hierarchical=False,
  )

  agraph_result = agraph(nodes=nodes, edges=edges, config=config)

  # st.write("DEBUG agraph_result:", agraph_result) # test to see what node is chosen
  
  # agraph_result contain info of node
  new_selected = None
  if isinstance(agraph_result, str):
    new_selected = agraph_result
  elif isinstance(agraph_result, dict):
    candidates = [
      agraph_result.get("id"),
      agraph_result.get("selected"),
      agraph_result.get("selectedNode"),
      agraph_result.get("selected_node"),
      agraph_result.get("node"),
      agraph_result.get("clickedNode"),
      agraph_result.get("clicked_node"),
    ]
    for c in candidates:
      if isinstance(c, str) and c:
        new_selected = c
        break
      if isinstance(c, dict) and "id" in c and c["id"]:
        new_selected = c["id"]
        break

  if new_selected:
    st.session_state["selected_section_id"] = new_selected
  
  selected = st.session_state.get("selected_section_id", None)
  
  st.write(f"当前选中节点：{selected if selected else '（未选中）'}")

  st.markdown("### 当前方案的选课结果")
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


with right:
  st.markdown("### 方案解释")
  # Explanation panel
  ex = explain_solution(sol, weights=weights, teacher_pref=teacher_pref)
  for b in ex.bullets:
    st.write(f"- {b}")

  st.markdown("---")
  st.markdown("### 点击图上的节点后：解释为什么没选它")
  
  if not selected:
    st.info("在左侧图上点击任意节点，这里会显示解释。")

  else:
    st.write(f"当前选中节点：**{selected}**")
    ex2 = explain_why_section_not_chosen(selected, sol, section_by_id=section_by_id, G=G)
    st.markdown(f"### {ex2.title}")
    for b in ex2.bullets:
      st.write(b)