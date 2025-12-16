import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import unicodedata

# =========================
# Streamlit 기본 설정
# =========================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# =========================
# 한글 폰트 (Streamlit CSS)
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

# =========================
# 학교 설정
# =========================
school_ec_targets = {
    "송도고": 1.0,
    "하늘고": 2.0,
    "아라고": 4.0,
    "동산고": 8.0
}

school_colors = {
    "송도고": "#AED6F1",
    "하늘고": "#3498DB",
    "아라고": "#E67E22",
    "동산고": "#E74C3C"
}

schools = ["전체"] + list(school_ec_targets.keys())

# =========================
# 데이터 로딩 함수 (필수 요구사항)
# =========================
@st.cache_data
def load_school_env_data(school):
    data_dir = Path("data")
    if not data_dir.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        return None

    school_nfc = unicodedata.normalize("NFC", school)
    school_nfd = unicodedata.normalize("NFD", school)

    for file_path in data_dir.iterdir():
        if file_path.suffix == ".csv":
            filename_nfc = unicodedata.normalize("NFC", file_path.stem)
            filename_nfd = unicodedata.normalize("NFD", file_path.stem)

            if (
                school_nfc in filename_nfc or school_nfc in filename_nfd or
                school_nfd in filename_nfc or school_nfd in filename_nfd
            ):
                return pd.read_csv(file_path)

    return None


@st.cache_data
def load_growth_data():
    data_dir = Path("data")
    if not data_dir.exists():
        st.error("❌ data 폴더를 찾을 수 없습니다.")
        return None

    for file_path in data_dir.iterdir():
        if file_path.suffix == ".xlsx":
            return pd.read_excel(file_path)

    return None


# =========================
# 사이드바
# =========================
st.sidebar.title("🏫 학교 선택")
selected_school = st.sidebar.selectbox("학교", schools)

# =========================
# 제목
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")

# =========================
# 탭 구성
# =========================
tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# =====================================================
# Tab 1 : 실험 개요
# =====================================================
with tab1:
    st.subheader("연구 배경")
    st.write(
        "본 연구는 극지식물의 생육 최적화를 위해 "
        "EC(Electrical Conductivity) 농도 조건에 따른 환경 변화를 분석하고, "
        "전체 생육 결과를 종합적으로 평가하는 것을 목표로 합니다."
    )

    st.subheader("실험 방법")
    st.write(
        "- 4개 고등학교에서 서로 다른 목표 EC 조건으로 재배\n"
        "- 환경 데이터: 온도, 습도, pH, EC 실시간 측정\n"
        "- 생육 데이터: 58개 개체 통합 분석 (학교 구분 없음)"
    )

    st.subheader("학교별 EC 조건")
    ec_df = pd.DataFrame({
        "학교": list(school_ec_targets.keys()),
        "목표 EC": list(school_ec_targets.values())
    })
    st.table(ec_df)

    st.subheader("주요 지표")
    cols = st.columns(4)
    for idx, (school, ec) in enumerate(school_ec_targets.items()):
        cols[idx].metric(label=school, value=f"EC {ec}")

# =====================================================
# Tab 2 : 환경 데이터
# =====================================================
with tab2:
    st.subheader("학교별 환경 비교")

    env_data_all = {}
    for school in school_ec_targets:
        df = load_school_env_data(school)
        if df is not None:
            env_data_all[school] = df

    if not env_data_all:
        st.error("❌ 환경 데이터를 불러올 수 없습니다.")
    else:
        # 평균 비교
        avg_df = pd.DataFrame({
            school: df[["temperature", "humidity", "ph", "ec"]].mean()
            for school, df in env_data_all.items()
        }).T

        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["온도", "습도", "pH", "EC"]
        )

        metrics = ["temperature", "humidity", "ph", "ec"]
        positions = [(1,1), (1,2), (2,1), (2,2)]

        for metric, (r, c) in zip(metrics, positions):
            for school in avg_df.index:
                fig.add_trace(
                    go.Bar(
                        x=[school],
                        y=[avg_df.loc[school, metric]],
                        name=school,
                        marker_color=school_colors[school],
                        showlegend=False
                    ),
                    row=r, col=c
                )

        fig.update_layout(
            height=700,
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif")
        )
        st.plotly_chart(fig, use_container_width=True)

        # 시계열
        if selected_school != "전체":
            st.subheader(f"{selected_school} 시계열 데이터")
            df = env_data_all.get(selected_school)

            if df is None:
                st.error("❌ 선택한 학교 데이터가 없습니다.")
            else:
                fig_ts = go.Figure()
                fig_ts.add_trace(go.Scatter(x=df["time"], y=df["ec"], name="실측 EC"))
                fig_ts.add_hline(
                    y=school_ec_targets[selected_school],
                    line_dash="dash",
                    annotation_text="목표 EC"
                )

                fig_ts.update_layout(
                    font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
                    xaxis_title="시간",
                    yaxis_title="EC"
                )
                st.plotly_chart(fig_ts, use_container_width=True)

# =====================================================
# Tab 3 : 생육 결과
# =====================================================
with tab3:
    st.subheader("전체 생육 통계")

    with st.spinner("생육 데이터 로딩 중..."):
        growth_df = load_growth_data()

    if growth_df is None:
        st.error("❌ 생육 데이터를 불러올 수 없습니다.")
    else:
        cols = st.columns(4)
        cols[0].metric("개체 수", len(growth_df))
        cols[1].metric("평균 잎 수", round(growth_df["잎 수(장)"].mean(), 2))
        cols[2].metric("평균 지상부 길이(mm)", round(growth_df["지상부 길이(mm)"].mean(), 2))
        cols[3].metric("평균 생중량(g)", round(growth_df["생중량(g)"].mean(), 2))

        st.subheader("생육 지표 분포")
        hist_col = st.selectbox(
            "지표 선택",
            ["잎 수(장)", "지상부 길이(mm)", "지하부길이(mm)", "생중량(g)"]
        )

        fig_hist = go.Figure(
            go.Histogram(x=growth_df[hist_col])
        )
        fig_hist.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
            xaxis_title=hist_col,
            yaxis_title="빈도"
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        st.subheader("상관관계 분석")
        fig_scatter = go.Figure(
            go.Scatter(
                x=growth_df["지상부 길이(mm)"],
                y=growth_df["생중량(g)"],
                mode="markers"
            )
        )
        fig_scatter.update_layout(
            font=dict(family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"),
            xaxis_title="지상부 길이(mm)",
            yaxis_title="생중량(g)"
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
