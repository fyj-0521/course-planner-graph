import pandas as pd
import streamlit as st

from src.time_utils import parse_times

st.set_page_config(page_title="CourseGraph", layout="wide")
st.title("CourseGraph：Phase 1（数据导入 + 时间解析）")

st.write(
    """
    目标：
    1) 从 CSV 读取 section 数据
    2) 将 times 字符串（如 '1-1;1-2;3-3'）解析为离散时间块集合 times={(day, block)}
    """
)

# ---- Load data ----
DATA_PATH = "data/sample_sections.csv"

try:
    df = pd.read_csv(DATA_PATH)
except FileNotFoundError:
    st.error(f"找不到文件：{DATA_PATH}。请确认你创建了 data/sample_sections.csv")
    st.stop()

required_cols = {"course_id", "section_id", "teacher", "campus", "times"}
missing = required_cols - set(df.columns)
if missing:
    st.error(f"CSV 缺少列：{sorted(missing)}。需要列：{sorted(required_cols)}")
    st.stop()

st.subheader("原始 CSV 数据")
st.dataframe(df, width="stretch")

# ---- Parse times ----
st.subheader("解析后的 times（集合形式）")

parsed_times = []
parse_errors = 0

for idx, row in df.iterrows():
    try:
        times_set = parse_times(str(row["times"]))
        parsed_times.append(times_set)
    except Exception as e:
        parse_errors += 1
        parsed_times.append(set())
        st.warning(f"第 {idx} 行 times 解析失败：{row['times']!r}，错误：{e}")

df2 = df.copy()
df2["times_set"] = parsed_times

st.dataframe(df2, width="stretch")

if parse_errors == 0:
    st.success("✅ Phase 1 完成：CSV 读取成功，times 全部解析成功。")
else:
    st.error(f"❌ 有 {parse_errors} 行 times 解析失败，请修正 CSV 再试。")

# ---- Quick sanity checks ----
st.subheader("快速检查（你应该能看懂的几个例子）")
example = df2.iloc[0]
st.write(f"Example section: **{example['section_id']}**")
st.write(f"times string: `{example['times']}`")
st.write(f"times_set: `{example['times_set']}`")