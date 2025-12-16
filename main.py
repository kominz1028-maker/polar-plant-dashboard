# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path  # 표준 라이브러리 (requirements.txt 불필요)

# =========================
# 0) 페이지 설정 / 상수
# =========================
st.set_page_config(layout="wide", page_title="극지식물 EC 연구")

SCHOOLS = ["송도고", "하늘고", "아라고", "동산고"]
EC_TARGET = {"송도고": 1, "하늘고": 2, "아라고": 4, "동산고": 8}

school_colors = {
    "송도고": "#AED6F1",
    "하늘고": "#3498DB",
    "아라고": "#E67E22",
    "동산고": "#E74C3C",
}

PLOTLY_FONT_FAMILY = "Malgun Gothic, Apple SD Gothic Neo, NanumGothic, Noto Sans CJK KR, sans-serif"

st.markdown(
    f"""
    <style>
    html, body, [class*="css"] {{
        font-family: {PLOTLY_FONT_FAMILY};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌱 극지식물 최적 EC 농도 연구")
st.subheader("송도고·하늘고·아라고·동산고 공동 실험")


# =========================
# 1) 경로 자동 탐지 (Cloud에서 핵심)
# =========================
def get_data_dir() -> Path:
    """
    data 폴더 위치가 환경에 따라 달라질 수 있어 2군데를 확인:
    1) 현재 작업 폴더(cwd)/data
    2) main.py가 있는 폴더/ data
    """
    candidates = [
        Path.cwd() / "data",
        Path(__file__).resolve().parent / "data",
    ]
    for c in candidates:
        if c.exists() and c.is_dir():
            return c
    # 둘 다 없으면, 그래도 반환(디버그로 확인)
    return candidates[0]


DATA_DIR = get_data_dir()


# =========================
# 2) 유틸 함수
# =========================
def set_plotly_korean(fig):
    fig.update_layout(font=dict(family=PLOTLY_FONT_FAMILY))
    return fig


def safe_read_csv(path: Path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return pd.read_csv(path, encoding="cp949")
        except Exception as e:
            st.warning(f"⚠️ CSV 읽기 실패: {path}\n- 에러: {e}")
            return None
    except FileNotFoundError:
        return None
    except Exception as e:
        st.warning(f"⚠️ CSV 읽기 실패: {path}\n- 에러: {e}")
        return None


def try_parse_time(df: pd.DataFrame, school: str) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if "time" not in df.columns:
        st.warning(f"⚠️ {school} 데이터에 'time' 컬럼이 없습니다.")
        return df
    try:
        df = df.copy()
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time")
        return df
    except Exception as e:
        st.warning(f"⚠️ {school} time 변환 실패: {e}")
        return df


def download_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def fmt_num(x, digits=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "N/A"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "N/A"


def find_first_file(patterns):
    if not DATA_DIR.exists():
        return None
    for pat in patterns:
        cands = sorted(DATA_DIR.glob(pat), key=lambda p: p.name)
        if cands:
            return cands[0]
    return None


@st.cache_data(show_spinner=False)
def load_env_data_all():
    data = {}
    for school in SCHOOLS:
        # 파일명 변화에 최대한 견고하게
        patterns = [
            f"{school}_환경데이터.csv",
            f"*{school}*환경데이터*.csv",
            f"*{school}*_환경데이터*.csv",
        ]
        path = find_first_file(patterns)
        if path is None:
            data[school] = None
            continue

        df = safe_read_csv(path)
        if df is None:
            data[school] = None
        else:
            data[school] = try_parse_time(df, school)
    return data


@st.cache_data(show_spinner=False)
def load_growth_data():
    patterns = [
        "4개교_생육결과데이터.xlsx",
        "*4개교*생육결과*.xlsx",
        "*4개교*생육*데이터*.xlsx",
    ]
    path = find_first_file(patterns)
    if path is None:
        return None
    try:
        return pd.read_excel(path, engine="openpyxl")
    except Exception as e:
        st.warning(f"⚠️ 엑셀 읽기 실패: {path}\n- 에러: {e}")
        return None


def env_means_by_school(env_dict: dict) -> pd.DataFrame:
    rows = []
    for school in SCHOOLS:
        df = env_dict.get(school)
        if df is None or df.empty:
            rows.append({"학교": school, "temperature": None, "humidity": None, "ph": None, "ec": None})
        else:
            rows.append(
                {
                    "학교": school,
                    "temperature": df["temperature"].mean() if "temperature" in df.columns else None,
                    "humidity": df["humidity"].mean() if "humidity" in df.columns else None,
                    "ph": df["ph"].mean() if "ph" in df.columns else None,
                    "ec": df["ec"].mean() if "ec" in df.columns else None,
                }
            )
    out = pd.DataFrame(rows)
    out["color"] = out["학교"].map(school_colors)
    out["target_ec"] = out["학교"].map(EC_TARGET)
    return out


def overall_env_stats(env_dict: dict) -> dict:
    total_rows = 0
    temps, hums = [], []

    for school in SCHOOLS:
        df = env_dict.get(school)
        if df is None or df.empty:
            continue
        total_rows += len(df)
        if "temperature" in df.columns:
            temps.append(df["temperature"])
        if "humidity" in df.columns:
            hums.append(df["humidity"])

    avg_temp = pd.concat(temps).mean() if temps else None
    avg_hum = pd.concat(hums).mean() if hums else None

    return {"total_rows": total_rows, "avg_temp": avg_temp, "avg_hum": avg_hum}


# =========================
# 3) 디버그(Cloud에서 매우 중요)
# =========================
with st.sidebar:
    with st.expander("🛠 디버그: 서버에서 보이는 파일 목록", expanded=False):
        st.write("Path.cwd():", str(Path.cwd()))
        st.write("__file__ dir:", str(Path(__file__).resolve().parent))
        st.write("DATA_DIR:", str(DATA_DIR))
        st.write("DATA_DIR exists?:", DATA_DIR.exists())
        if DATA_DIR.exists():
            st.write("data 폴더 파일들:")
            st.write([p.name for p in sorted(DATA_DIR.iterdir(), key=lambda p: p.name)])
        else:
            st.warning("서버에서 data 폴더 자체를 못 찾고 있습니다.")


# =========================
# 4) 데이터 로딩
# =========================
with st.spinner("데이터 불러오는 중..."):
    env_data = load_env_data_all()
    growth_df = load_growth_data()

# 에러 표시
for school in SCHOOLS:
    if env_data.get(school) is None:
        st.error(f"❌ 파일을 찾을 수 없습니다: {school} 환경데이터 CSV (data 폴더 확인)")

if growth_df is None:
    st.error("❌ 파일을 찾을 수 없습니다: 4개교_생육결과데이터.xlsx (data 폴더 확인)")


# =========================
# 5) 사이드바 UI
# =========================
with st.sidebar:
    st.markdown("## 📌 실험 정보")
    st.write("**실험 기간:** 2025.05 ~ 2025.07")
    st.write("**참여 학교:** 4개교")
    st.write("**총 개체 수:** 58개")
    st.write("**협력 기관:** 극지연구소")

    st.markdown("---")
    st.markdown("## 📌 학교별 EC 조건 (표)")
    st.dataframe(
        pd.DataFrame(
            {"학교": ["송도고", "하늘고", "아라고", "동산고"], "EC": ["1", "2 (최적 예상)", "4", "8"]}
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")
    st.markdown("## 📌 학교 선택")
    selected_school = st.selectbox("분석할 학교를 선택하세요", ["전체"] + SCHOOLS, index=0)


# =========================
# 6) 탭 3개
# =========================
tab1, tab2, tab3 = st.tabs(["🟢 실험 개요", "🟡 환경 데이터 분석", "🔵 생육 결과 분석"])

# ---- Tab 1
with tab1:
    st.markdown(
        """
### 연구 배경
극지식물은 낮은 온도, 제한된 영양 환경에서도 생존하는 특별한 식물입니다.  
이번 실험은 **양액 농도(EC)** 가 생육에 어떤 영향을 주는지 알아보기 위해 진행했습니다.

### 실험 방법
1. 4개 학교가 같은 극지식물을 재배했습니다.
2. 학교마다 EC 조건(1, 2, 4, 8)을 다르게 설정했습니다.
3. 환경 센서로 온도/습도/pH/EC를 일정 간격으로 자동 측정했습니다.
4. 실험 종료 후 개체별 잎 수/길이/생중량을 측정했습니다.
"""
    )

    stats = overall_env_stats(env_data)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("총 측정 횟수", f"{stats['total_rows']:,}" if stats["total_rows"] is not None else "N/A")
    c2.metric("평균 온도", f"{fmt_num(stats['avg_temp'], 2)} °C")
    c3.metric("평균 습도", f"{fmt_num(stats['avg_hum'], 2)} %")
    c4.metric("전체 개체 수", "58")

# ---- Tab 2
with tab2:
    st.markdown("### ✔ 학교별 평균 비교 (2x2 그래프)")
    means_df = env_means_by_school(env_data)

    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "평균 EC (목표 EC와 비교)"),
        horizontal_spacing=0.10,
        vertical_spacing=0.15,
    )

    def add_bar(row, col, y_col, y_name, suffix=""):
        fig.add_trace(
            go.Bar(
                x=means_df["학교"],
                y=means_df[y_col],
                name=y_name,
                marker_color=means_df["color"],
                hovertemplate="학교=%{x}<br>" + f"{y_name}=%{{y:.2f}}{suffix}<extra></extra>",
            ),
            row=row,
            col=col,
        )

    add_bar(1, 1, "temperature", "온도", "°C")
    add_bar(1, 2, "humidity", "습도", "%")
    add_bar(2, 1, "ph", "pH", "")

    fig.add_trace(
        go.Bar(
            x=means_df["학교"],
            y=means_df["ec"],
            name="평균 EC",
            marker_color=means_df["color"],
            hovertemplate="학교=%{x}<br>평균 EC=%{y:.2f}<extra></extra>",
        ),
        row=2,
        col=2,
    )
    fig.add_trace(
        go.Scatter(
            x=means_df["학교"],
            y=means_df["target_ec"],
            mode="lines+markers",
            name="목표 EC",
            line=dict(width=2, dash="dash"),
            hovertemplate="학교=%{x}<br>목표 EC=%{y}<extra></extra>",
        ),
        row=2,
        col=2,
    )

    fig.update_layout(height=720, legend_orientation="h", legend_y=-0.12)
    st.plotly_chart(set_plotly_korean(fig), use_container_width=True)

    st.markdown("---")
    st.markdown("### ✔ 선택한 학교 시계열")

    if selected_school == "전체":
        st.info("ℹ️ 시계열 그래프는 학교 1개를 선택했을 때 보기 좋아요.")
    else:
        df_sel = env_data.get(selected_school)
        if df_sel is None or df_sel.empty:
            st.warning("⚠️ 선택한 학교 데이터가 없습니다.")
        else:
            if "temperature" in df_sel.columns and "time" in df_sel.columns:
                f = px.line(df_sel, x="time", y="temperature", title=f"{selected_school} 온도 변화")
                f.update_traces(line=dict(color=school_colors[selected_school]))
                st.plotly_chart(set_plotly_korean(f), use_container_width=True)

            if "humidity" in df_sel.columns and "time" in df_sel.columns:
                f = px.line(df_sel, x="time", y="humidity", title=f"{selected_school} 습도 변화")
                f.update_traces(line=dict(color=school_colors[selected_school]))
                st.plotly_chart(set_plotly_korean(f), use_container_width=True)

            if "ec" in df_sel.columns and "time" in df_sel.columns:
                f = go.Figure()
                f.add_trace(
                    go.Scatter(
                        x=df_sel["time"],
                        y=df_sel["ec"],
                        mode="lines",
                        name="측정 EC",
                        line=dict(color=school_colors[selected_school]),
                    )
                )
                f.add_hline(
                    y=EC_TARGET[selected_school],
                    line_dash="dash",
                    annotation_text=f"목표 EC = {EC_TARGET[selected_school]}",
                    annotation_position="top left",
                )
                f.update_layout(title=f"{selected_school} EC 변화 (목표 EC 기준선 포함)")
                st.plotly_chart(set_plotly_korean(f), use_container_width=True)

    st.markdown("---")
    st.markdown("### ✔ 원본 데이터")
    if selected_school == "전체":
        st.info("ℹ️ 원본 테이블/다운로드는 학교를 선택했을 때 제공합니다.")
    else:
        df_sel = env_data.get(selected_school)
        if df_sel is None:
            st.error(f"❌ 파일을 찾을 수 없습니다: {selected_school} 환경데이터 CSV")
        else:
            with st.expander("원본 데이터 미리보기 (처음 100행)"):
                st.dataframe(df_sel.head(100), use_container_width=True)

            st.download_button(
                label=f"⬇️ {selected_school} 환경데이터 CSV 다운로드",
                data=download_csv_bytes(df_sel),
                file_name=f"{selected_school}_환경데이터_download.csv",
                mime="text/csv",
            )

# ---- Tab 3
with tab3:
    st.warning("⚠️ 이 데이터는 4개 학교의 개체가 합쳐진 데이터입니다.\n학교별 비교는 불가능합니다.")

    if growth_df is None or growth_df.empty:
        st.error("❌ 파일을 찾을 수 없습니다: 4개교_생육결과데이터.xlsx")
    else:
        st.markdown("### ✔ 전체 통계")

        def stat_block(colname, unit="", digits=2):
            if colname not in growth_df.columns:
                return ("N/A", "N/A")
            s = pd.to_numeric(growth_df[colname], errors="coerce")
            return (
                f"{fmt_num(s.mean(), digits)}{unit}",
                f"{fmt_num(s.min(), digits)} ~ {fmt_num(s.max(), digits)}{unit}",
            )

        c1, c2, c3 = st.columns(3)
        m1, r1 = stat_block("생중량(g)", " g", 2)
        m2, r2 = stat_block("잎 수(장)", " 장", 1)
        m3, r3 = stat_block("지상부 길이(mm)", " mm", 1)

        with c1:
            st.metric("평균 생중량", m1)
            st.caption(f"최소~최대: {r1}")
        with c2:
            st.metric("평균 잎 수", m2)
            st.caption(f"최소~최대: {r2}")
        with c3:
            st.metric("평균 지상부 길이", m3)
            st.caption(f"최소~최대: {r3}")

        st.markdown("---")
        st.markdown("### ✔ 분포 그래프")
        cols = st.columns(3)

        def draw_hist(colname, title):
            if colname not in growth_df.columns:
                return None
            s = pd.to_numeric(growth_df[colname], errors="coerce").dropna()
            if s.empty:
                return None
            f = px.histogram(pd.DataFrame({colname: s}), x=colname, nbins=15, title=title)
            return set_plotly_korean(f)

        figs = [
            draw_hist("생중량(g)", "생중량 히스토그램"),
            draw_hist("잎 수(장)", "잎 수 히스토그램"),
            draw_hist("지상부 길이(mm)", "지상부 길이 히스토그램"),
        ]

        for i, f in enumerate(figs):
            with cols[i]:
                if f is None:
                    st.info("표시할 데이터가 없어요.")
                else:
                    st.plotly_chart(f, use_container_width=True)

        st.markdown("---")
        st.markdown("### ✔ 상관관계 (선택)")
        options = []
        if "잎 수(장)" in growth_df.columns and "생중량(g)" in growth_df.columns:
            options.append("잎 수 vs 생중량")
        if "지상부 길이(mm)" in growth_df.columns and "생중량(g)" in growth_df.columns:
            options.append("지상부 길이 vs 생중량")

        if options:
            choice = st.selectbox("보고 싶은 관계를 선택하세요", options)
            x_col = "잎 수(장)" if "잎 수" in choice else "지상부 길이(mm)"
            y_col = "생중량(g)"

            tmp = growth_df[[x_col, y_col]].copy()
            tmp[x_col] = pd.to_numeric(tmp[x_col], errors="coerce")
            tmp[y_col] = pd.to_numeric(tmp[y_col], errors="coerce")
            tmp = tmp.dropna()

            if tmp.empty:
                st.info("표시할 데이터가 없어요.")
            else:
                f = px.scatter(tmp, x=x_col, y=y_col, title=f"{choice} 산점도")
                st.plotly_chart(set_plotly_korean(f), use_container_width=True)
        else:
            st.info("상관관계 그래프를 그리기 위한 컬럼이 부족합니다.")


st.markdown("---")
st.markdown("Made with ❤️ by 극지식물 연구팀 | Powered by Streamlit")
