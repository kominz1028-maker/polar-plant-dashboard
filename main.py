import streamlit as st
import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.graph_objects as go
from pathlib import Path
import unicodedata
import io

# =========================
# Streamlit 기본 설정
# =========================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =========================
# 한글 폰트 깨짐 방지 (Streamlit)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 공통 설정
# =========================
DATA_DIR = Path("data")

SCHOOL_EC_MAP = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

SCHOOL_COLOR_MAP = {
    "송도고": "#4C72B0",
    "하늘고": "#55A868",
    "아라고": "#C44E52",
    "동산고": "#8172B2"
}

# =========================
# 파일 탐색 유틸 (NFC/NFD 완벽 대응)
# =========================
def normalize_pair(text: str):
    return (
        unicodedata.normalize("NFC", text),
        unicodedata.normalize("NFD", text)
    )

def find_file_by_keyword(directory: Path, keyword: str, suffix: str):
    key_nfc, key_nfd = normalize_pair(keyword)

    for file_path in directory.iterdir():
        if file_path.suffix != suffix:
            continue

        stem_nfc, stem_nfd = normalize_pair(file_path.stem)
        if key_nfc in stem_nfc or key_nfd in stem_nfd:
            return file_path

    return None

# =========================
# 데이터 로딩
# =========================
@st.cache_data
def load_environment_data():
    env_data = {}

    with st.spinner("환경 데이터 로딩 중..."):
        for school in SCHOOL_EC_MAP.keys():
            file_path = find_file_by_keyword(DATA_DIR, school, ".csv")
            if file_path is None:
                st.error(f"❌ 환경 데이터 파일을 찾을 수 없습니다: {school}")
                continue

            df = pd.read_csv(file_path)
            df["time"] = pd.to_datetime(df["time"])
            df["school"] = school
            env_data[school] = df

    return env_data

@st.cache_data
def load_growth_data():
    xlsx_path = None
    for p in DATA_DIR.iterdir():
        if p.suffix == ".xlsx":
            xlsx_path = p
            break

    if xlsx_path is None:
        st.error("❌ 생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return {}

    growth_data = {}

    with st.spinner("생육 결과 데이터 로딩 중..."):
        xls = pd.ExcelFile(xlsx_path, engine="openpyxl")

        for sheet in xls.sheet_names:
            sheet_nfc, sheet_nfd = normalize_pair(sheet)
            for school in SCHOOL_EC_MAP.keys():
                s_nfc, s_nfd = normalize_pair(school)
                if sheet_nfc == s_nfc or sheet_nfd == s_nfd:
                    df = pd.read_excel(xlsx_path, sheet_name=sheet, engine="openpyxl")
                    df["school"] = school
                    df["EC"] = SCHOOL_EC_MAP[school]
                    growth_data[school] = df

    return growth_data

env_data = load_environment_data()
growth_data = load_growth_data()

# =========================
# 사이드바
# =========================
st.sidebar.title("🔍 설정")
school_option = st.sidebar.selectbox(
    "학교 선택",
    ["전체"] + list(SCHOOL_EC_MAP.keys())
)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

tabs = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# Tab 1 : 실험 개요
# =====================================================
with tabs[0]:
    st.subheader("연구 배경 및 목적")
    st.markdown("""
    본 연구는 **EC 농도 차이에 따른 극지식물 생육 특성**을 비교·분석하여  
    **최적 EC 농도 조건을 도출**하는 것을 목표로 합니다.
    """)

    overview_rows = []
    total_count = 0
    for school, ec in SCHOOL_EC_MAP.items():
        count = len(growth_data.get(school, []))
        total_count += count
        overview_rows.append({
            "학교명": school,
            "EC 목표": ec,
            "개체수": count,
            "색상": SCHOOL_COLOR_MAP[school]
        })

    overview_df = pd.DataFrame(overview_rows)
    st.table(overview_df)

    avg_temp = pd.concat(env_data.values())["temperature"].mean()
    avg_hum = pd.concat(env_data.values())["humidity"].mean()

    st.columns(4)[0].metric("총 개체수", f"{total_count} 개")
    st.columns(4)[1].metric("평균 온도", f"{avg_temp:.1f} ℃")
    st.columns(4)[2].metric("평균 습도", f"{avg_hum:.1f} %")
    st.columns(4)[3].metric("최적 EC", "2.0 (하늘고)")

# =====================================================
# Tab 2 : 환경 데이터
# =====================================================
with tabs[1]:
    st.subheader("학교별 환경 평균 비교")

    avg_env = []
    for school, df in env_data.items():
        avg_env.append({
            "학교": school,
            "온도": df["temperature"].mean(),
            "습도": df["humidity"].mean(),
            "pH": df["ph"].mean(),
            "실측 EC": df["ec"].mean(),
            "목표 EC": SCHOOL_EC_MAP[school]
        })
    avg_env_df = pd.DataFrame(avg_env)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["온도"], row=1, col=1)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["습도"], row=1, col=2)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["pH"], row=2, col=1)

    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["목표 EC"], name="목표 EC", row=2, col=2)
    fig.add_bar(x=avg_env_df["학교"], y=avg_env_df["실측 EC"], name="실측 EC", row=2, col=2)

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
    )
    st.plotly_chart(fig, use_container_width=True)

    if school_option != "전체":
        df = env_data[school_option]

        st.subheader(f"{school_option} 시계열 데이터")

        for col, title, unit, target in [
            ("temperature", "온도 변화", "℃", None),
            ("humidity", "습도 변화", "%", None),
            ("ec", "EC 변화", "", SCHOOL_EC_MAP[school_option])
        ]:
            fig = px.line(df, x="time", y=col, title=title)
            if target is not None:
                fig.add_hline(y=target, line_dash="dash", annotation_text="목표 EC")
            fig.update_layout(font=dict(family="Malgun Gothic"))
            st.plotly_chart(fig, use_container_width=True)

        with st.expander("📥 환경 데이터 원본"):
            st.dataframe(df)
            buf = io.BytesIO()
            df.to_csv(buf, index=False)
            buf.seek(0)
            st.download_button(
                "CSV 다운로드",
                data=buf,
                file_name=f"{school_option}_환경데이터.csv",
                mime="text/csv"
            )

# =====================================================
# Tab 3 : 생육 결과
# =====================================================
with tabs[2]:
    st.subheader("EC별 생육 결과 분석")

    all_growth = pd.concat(growth_data.values(), ignore_index=True)
    ec_mean = all_growth.groupby("EC")["생중량(g)"].mean().reset_index()
    best_ec = ec_mean.loc[ec_mean["생중량(g)"].idxmax()]

    st.metric("🥇 최적 EC (평균 생중량 최대)", f"EC {best_ec['EC']}")

    metrics = {
        "생중량(g)": "평균 생중량",
        "잎 수(장)": "평균 잎 수",
        "지상부 길이(mm)": "평균 지상부 길이",
        "개체번호": "개체수"
    }

    fig = make_subplots(rows=2, cols=2, subplot_titles=list(metrics.values()))
    positions = [(1,1),(1,2),(2,1),(2,2)]

    for (col, title), pos in zip(metrics.items(), positions):
        agg = all_growth.groupby("EC")[col].mean() if col != "개체번호" else all_growth.groupby("EC")[col].count()
        fig.add_bar(x=agg.index, y=agg.values, row=pos[0], col=pos[1])

    fig.update_layout(
        height=700,
        font=dict(family="Malgun Gothic")
    )
    st.plotly_chart(fig, use_container_width=True)

    fig_box = px.box(
        all_growth,
        x="school",
        y="생중량(g)",
        color="school",
        title="학교별 생중량 분포"
    )
    fig_box.update_layout(font=dict(family="Malgun Gothic"))
    st.plotly_chart(fig_box, use_container_width=True)

    fig_scatter1 = px.scatter(
        all_growth, x="잎 수(장)", y="생중량(g)", color="school",
        title="잎 수 vs 생중량"
    )
    fig_scatter2 = px.scatter(
        all_growth, x="지상부 길이(mm)", y="생중량(g)", color="school",
        title="지상부 길이 vs 생중량"
    )
    for f in [fig_scatter1, fig_scatter2]:
        f.update_layout(font=dict(family="Malgun Gothic"))
        st.plotly_chart(f, use_container_width=True)

    with st.expander("📥 생육 데이터 원본"):
        st.dataframe(all_growth)
        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
