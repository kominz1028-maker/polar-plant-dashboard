# 🌱 극지식물 최적 EC 농도 연구 대시보드 (최종본)
# 즉시 실행 가능 / 한글 파일명·폰트 완벽 대응

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata
import io

# ===============================
# Streamlit 기본 설정
# ===============================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ===============================
# 한글 폰트 CSS (Streamlit)
# ===============================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")

# ===============================
# 학교 설정
# ===============================
school_ec_targets = {
    "송도고": 1.0,
    "하늘고": 2.0,  # 최적 EC
    "아라고": 4.0,
    "동산고": 8.0
}

school_colors = {
    "송도고": "#AED6F1",
    "하늘고": "#3498DB",
    "아라고": "#E67E22",
    "동산고": "#E74C3C"
}

school_sample_counts = {
    "동산고": 58,
    "송도고": 29,
    "아라고": 106,
    "하늘고": 45
}

SCHOOLS = list(school_ec_targets.keys())

# ===============================
# 데이터 로딩 함수 (한글 NFC/NFD 완벽 대응)
# ===============================
@st.cache_data
def load_school_env_data(school):
    data_dir = Path("data")
    school_nfc = unicodedata.normalize("NFC", school)
    school_nfd = unicodedata.normalize("NFD", school)

    for file_path in data_dir.iterdir():
        if file_path.suffix == ".csv":
            stem_nfc = unicodedata.normalize("NFC", file_path.stem)
            stem_nfd = unicodedata.normalize("NFD", file_path.stem)

            if (school_nfc in stem_nfc or school_nfc in stem_nfd or
                school_nfd in stem_nfc or school_nfd in stem_nfd):
                return pd.read_csv(file_path)
    return None


@st.cache_data
def load_school_growth_data(school):
    data_dir = Path("data")
    school_nfc = unicodedata.normalize("NFC", school)
    school_nfd = unicodedata.normalize("NFD", school)

    for file_path in data_dir.iterdir():
        if file_path.suffix == ".xlsx":
            xl = pd.ExcelFile(file_path)
            for sheet in xl.sheet_names:
                sheet_nfc = unicodedata.normalize("NFC", sheet)
                sheet_nfd = unicodedata.normalize("NFD", sheet)
                if (school_nfc == sheet_nfc or school_nfc == sheet_nfd or
                    school_nfd == sheet_nfc or school_nfd == sheet_nfd):
                    return pd.read_excel(file_path, sheet_name=sheet)
    return None


@st.cache_data
def load_all_growth_data():
    data_dir = Path("data")
    all_data = []

    for file_path in data_dir.iterdir():
        if file_path.suffix == ".xlsx":
            xl = pd.ExcelFile(file_path)
            for sheet in xl.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet)
                df["학교"] = sheet
                df["EC"] = school_ec_targets.get(sheet)
                all_data.append(df)

    return pd.concat(all_data, ignore_index=True) if all_data else None

# ===============================
# 사이드바
# ===============================
st.sidebar.title("🏫 학교 선택")
selected_school = st.sidebar.selectbox("분석 대상", ["전체"] + SCHOOLS)

# ===============================
# 제목
# ===============================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ===============================
# Tab 1 : 실험 개요
# ===============================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.markdown("""
- 극지식물의 **최적 EC 농도** 도출
- 학교별 환경 조건과 생육 결과 비교
- **생중량**을 핵심 지표로 활용
""")

    overview_df = pd.DataFrame({
        "학교": SCHOOLS,
        "EC 목표": [school_ec_targets[s] for s in SCHOOLS],
        "개체수": [school_sample_counts[s] for s in SCHOOLS]
    })
    st.dataframe(overview_df, use_container_width=True)

    with st.spinner("지표 계산 중..."):
        all_growth = load_all_growth_data()
        optimal_ec = all_growth.groupby("EC")["생중량(g)"].mean().idxmax()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 개체수", f"{all_growth.shape[0]} 개")
    c2.metric("학교 수", len(SCHOOLS))
    c3.metric("측정 EC 조건", len(school_ec_targets))
    c4.metric("최적 EC", f"{optimal_ec}")

# ===============================
# Tab 2 : 환경 데이터
# ===============================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    env_summary = []
    for s in SCHOOLS:
        df = load_school_env_data(s)
        if df is not None:
            env_summary.append({
                "학교": s,
                "온도": df["temperature"].mean(),
                "습도": df["humidity"].mean(),
                "pH": df["ph"].mean(),
                "EC": df["ec"].mean(),
                "EC 목표": school_ec_targets[s]
            })

    env_df = pd.DataFrame(env_summary)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=["평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC"]
    )

    fig.add_bar(x=env_df["학교"], y=env_df["온도"], row=1, col=1)
    fig.add_bar(x=env_df["학교"], y=env_df["습도"], row=1, col=2)
    fig.add_bar(x=env_df["학교"], y=env_df["pH"], row=2, col=1)
    fig.add_bar(x=env_df["학교"], y=env_df["EC"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=env_df["학교"], y=env_df["EC 목표"], name="목표 EC", row=2, col=2)

    fig.update_layout(font=PLOTLY_FONT, height=700)
    st.plotly_chart(fig, use_container_width=True)

# ===============================
# Tab 3 : 생육 결과
# ===============================
with tab3:
    st.subheader("🥇 EC별 평균 생중량")

    weight_by_ec = all_growth.groupby("EC")["생중량(g)"].mean().reset_index()
    fig_bar = px.bar(weight_by_ec, x="EC", y="생중량(g)", color="EC")
    fig_bar.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_bar, use_container_width=True)

    st.subheader("학교별 생중량 분포")
    fig_box = px.box(all_growth, x="학교", y="생중량(g)", color="학교")
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    st.subheader("상관관계 분석")
    c1, c2 = st.columns(2)
    with c1:
        fig_sc1 = px.scatter(all_growth, x="잎 수(장)", y="생중량(g)", color="학교")
        fig_sc1.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc1, use_container_width=True)

    with c2:
        fig_sc2 = px.scatter(all_growth, x="지상부 길이(mm)", y="생중량(g)", color="학교")
        fig_sc2.update_layout(font=PLOTLY_FONT)
        st.plotly_chart(fig_sc2, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(all_growth)
        buffer = io.BytesIO()
        all_growth.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)
        st.download_button(
            "XLSX 다운로드",
            data=buffer,
            file_name="4개교_생육결과데이터.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
