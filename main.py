# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# =========================
# 0) 기본 설정 / 상수
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

# 한글 폰트(브라우저/OS에 따라 가능한 폰트가 다를 수 있어, 여러 후보를 넣어둠)
PLOTLY_FONT_FAMILY = "Malgun Gothic, Apple SD Gothic Neo, NanumGothic, Noto Sans CJK KR, sans-serif"

# Streamlit 화면 글꼴도 최대한 한글이 자연스럽게 보이도록 CSS 설정
st.markdown(
    f"""
    <style>
    html, body, [class*="css"]  {{
        font-family: {PLOTLY_FONT_FAMILY};
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 1) 유틸 함수들
# =========================
def set_plotly_korean(fig):
    """Plotly 그래프에서 한글이 깨지지 않도록 기본 폰트를 지정"""
    fig.update_layout(font=dict(family=PLOTLY_FONT_FAMILY))
    return fig


def safe_read_csv(file_path: str) -> pd.DataFrame | None:
    """
    CSV를 utf-8-sig로 먼저 읽고, 실패하면 cp949로 재시도.
    파일이 없으면 None 반환(화면에서 st.error로 처리).
    """
    try:
        return pd.read_csv(file_path, encoding="utf-8-sig")
    except FileNotFoundError:
        return None
    except Exception:
        # utf-8-sig 실패 → cp949 재시도
        try:
            return pd.read_csv(file_path, encoding="cp949")
        except FileNotFoundError:
            return None
        except Exception as e:
            st.warning(f"⚠️ CSV 읽기에 실패했습니다: {file_path}\n- 에러: {e}")
            return None


def try_parse_time(df: pd.DataFrame, school: str) -> pd.DataFrame:
    """
    time 컬럼을 datetime으로 변환 후 정렬.
    실패하면 경고 표시하고 원본 유지.
    """
    if df is None or df.empty:
        return df
    if "time" not in df.columns:
        st.warning(f"⚠️ {school} 환경 데이터에 'time' 컬럼이 없습니다. 시계열 분석이 제한됩니다.")
        return df

    try:
        df = df.copy()
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time")
        return df
    except Exception as e:
        st.warning(f"⚠️ {school} time 변환 실패: pd.to_datetime() 처리 불가\n- 에러: {e}")
        return df


@st.cache_data(show_spinner=False)
def load_env_data_all():
    """
    4개 학교 환경데이터를 모두 읽어서 dict로 반환
    반환 형태: {"송도고": df, ...}
    """
    data = {}
    for school in SCHOOLS:
        path = f"data/{school}_환경데이터.csv"
        df = safe_read_csv(path)
        if df is None:
            data[school] = None
        else:
            df = try_parse_time(df, school)
            data[school] = df
    return data


@st.cache_data(show_spinner=False)
def load_growth_data():
    """
    생육 결과 엑셀 로드 (학교 정보 없음 → 전체 통계만)
    """
    path = "data/4개교_생육결과데이터.xlsx"
    try:
        df = pd.read_excel(path, engine="openpyxl")
        return df
    except FileNotFoundError:
        return None
    except Exception as e:
        st.warning(f"⚠️ 엑셀 읽기에 실패했습니다: {path}\n- 에러: {e}")
        return None


def env_means_by_school(env_dict: dict) -> pd.DataFrame:
    """학교별 평균(temperature/humidity/ph/ec)을 표로 계산"""
    rows = []
    for school in SCHOOLS:
        df = env_dict.get(school)
        if df is None or df.empty:
            rows.append({"학교": school, "temperature": None, "humidity": None, "ph": None, "ec": None})
            continue

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
    return out


def overall_env_stats(env_dict: dict) -> dict:
    """전체(4개교 합산) 측정 횟수/평균 온도/평균 습도 계산"""
    total_rows = 0
    temps = []
    hums = []

    for school in SCHOOLS:
        df = env_dict.get(school)
        if df is None or df.empty:
            continue
        total_rows += len(df)
        if "temperature" in df.columns:
            temps.append(df["temperature"])
        if "humidity" in df.columns:
            hums.append(df["humidity"])

    avg_temp = pd.concat(temps).mean() if len(temps) > 0 else None
    avg_hum = pd.concat(hums).mean() if len(hums) > 0 else None

    return {
        "total_rows": total_rows,
        "avg_temp": avg_temp,
        "avg_hum": avg_hum,
    }


def download_csv_bytes(df: pd.DataFrame) -> bytes:
    """다운로드용 CSV bytes (utf-8-sig)"""
    return df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def fmt_num(x, digits=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "N/A"
    try:
        return f"{float(x):.{digits}f}"
    except Exception:
        return "N/A"


# =========================
# 2) 제목 영역
# =========================
st.title("🌱 극지식물 최적 EC 농도 연구")
st.subheader("송도고·하늘고·아라고·동산고 공동 실험")

# =========================
# 3) 데이터 로딩 (스피너 필수)
# =========================
with st.spinner("데이터 불러오는 중..."):
    env_data = load_env_data_all()
    growth_df = load_growth_data()

# 파일 누락 에러 처리(요구사항: 파일 없으면 st.error)
for school in SCHOOLS:
    if env_data.get(school) is None:
        st.error(f"❌ 파일을 찾을 수 없습니다: data/{school}_환경데이터.csv")

if growth_df is None:
    st.error("❌ 파일을 찾을 수 없습니다: data/4개교_생육결과데이터.xlsx")

# =========================
# 4) 사이드바
# =========================
with st.sidebar:
    st.markdown("## 📌 실험 정보")
    st.write("**실험 기간:** 2025.05 ~ 2025.07")
    st.write("**참여 학교:** 4개교")
    st.write("**총 개체 수:** 58개")
    st.write("**협력 기관:** 극지연구소")

    st.markdown("---")
    st.markdown("## 📌 학교별 EC 조건 (표)")
    ec_table = pd.DataFrame(
        {
            "학교": ["송도고", "하늘고", "아라고", "동산고"],
            "EC": ["1", "2 (최적 예상)", "4", "8"],
        }
    )
    st.dataframe(ec_table, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("## 📌 학교 선택")
    selected_school = st.selectbox("분석할 학교를 선택하세요", ["전체"] + SCHOOLS, index=0)


# =========================
# 5) 메인 화면 (탭 3개)
# =========================
tab1, tab2, tab3 = st.tabs(["🟢 실험 개요", "🟡 환경 데이터 분석", "🔵 생육 결과 분석"])

# ---------------------------------
# Tab 1: 실험 개요
# ---------------------------------
with tab1:
    st.markdown(
        """
### 연구 배경
극지식물은 낮은 온도, 제한된 영양 환경에서도 생존하는 특별한 식물입니다.  
이번 실험은 **양액 농도(EC)** 가 극지식물 생육에 어떤 영향을 주는지 알아보기 위해 진행했습니다.

### 실험 방법
1. 4개 학교가 **같은 극지식물**을 재배했습니다.
2. 학교마다 **EC 조건(1, 2, 4, 8)** 을 다르게 설정했습니다.
3. 환경 센서로 **온도/습도/pH/EC** 를 일정 간격으로 자동 측정했습니다.
4. 실험 종료 후 개체별 **잎 수, 길이, 생중량** 등을 측정했습니다.

👉 연구 질문: **극지식물 생육에 가장 적합한 EC 농도는 무엇일까?**
"""
    )

    stats = overall_env_stats(env_data)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("총 측정 횟수", f"{stats['total_rows']:,}" if stats["total_rows"] is not None else "N/A")
    col2.metric("평균 온도", f"{fmt_num(stats['avg_temp'], 2)} °C")
    col3.metric("평균 습도", f"{fmt_num(stats['avg_hum'], 2)} %")
    col4.metric("전체 개체 수", "58")


# ---------------------------------
# Tab 2: 환경 데이터 분석
# ---------------------------------
with tab2:
    st.markdown("### ✔ 학교별 평균 비교 (2x2 그래프)")
    means_df = env_means_by_school(env_data)

    # 학교 순서 고정 + 색 고정
    means_df["color"] = means_df["학교"].map(school_colors)
    means_df["target_ec"] = means_df["학교"].map(EC_TARGET)

    # 2x2 subplot: temperature, humidity, ph, ec
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

    # EC는 평균 막대 + 목표 EC 점(또는 선)
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
    fig = set_plotly_korean(fig)
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### ✔ 선택한 학교 시계열")

    if selected_school == "전체":
        st.info("ℹ️ 시계열 그래프는 **학교 1개를 선택**했을 때 더 이해하기 쉽습니다. (사이드바에서 선택)")
    else:
        df_sel = env_data.get(selected_school)

        if df_sel is None or df_sel.empty:
            st.warning("⚠️ 선택한 학교의 환경 데이터가 비어있습니다.")
        else:
            if "time" not in df_sel.columns or not pd.api.types.is_datetime64_any_dtype(df_sel["time"]):
                st.warning("⚠️ time 컬럼이 datetime으로 준비되지 않아 시계열 그래프가 제한될 수 있습니다.")

            # 온도 변화
            if "temperature" in df_sel.columns and "time" in df_sel.columns:
                fig_t = px.line(df_sel, x="time", y="temperature", title=f"{selected_school} 온도 변화")
                fig_t.update_traces(line=dict(color=school_colors[selected_school]))
                fig_t = set_plotly_korean(fig_t)
                st.plotly_chart(fig_t, use_container_width=True)
            else:
                st.warning("⚠️ temperature 또는 time 컬럼이 없어 온도 시계열을 그릴 수 없습니다.")

            # 습도 변화
            if "humidity" in df_sel.columns and "time" in df_sel.columns:
                fig_h = px.line(df_sel, x="time", y="humidity", title=f"{selected_school} 습도 변화")
                fig_h.update_traces(line=dict(color=school_colors[selected_school]))
                fig_h = set_plotly_korean(fig_h)
                st.plotly_chart(fig_h, use_container_width=True)
            else:
                st.warning("⚠️ humidity 또는 time 컬럼이 없어 습도 시계열을 그릴 수 없습니다.")

            # EC 변화 + 목표 EC 기준선
            if "ec" in df_sel.columns and "time" in df_sel.columns:
                fig_ec = go.Figure()
                fig_ec.add_trace(
                    go.Scatter(
                        x=df_sel["time"],
                        y=df_sel["ec"],
                        mode="lines",
                        name="측정 EC",
                        line=dict(color=school_colors[selected_school]),
                        hovertemplate="시간=%{x}<br>EC=%{y:.2f}<extra></extra>",
                    )
                )
                fig_ec.add_hline(
                    y=EC_TARGET[selected_school],
                    line_dash="dash",
                    annotation_text=f"목표 EC = {EC_TARGET[selected_school]}",
                    annotation_position="top left",
                )
                fig_ec.update_layout(title=f"{selected_school} EC 변화 (목표 EC 기준선 포함)")
                fig_ec = set_plotly_korean(fig_ec)
                st.plotly_chart(fig_ec, use_container_width=True)
            else:
                st.warning("⚠️ ec 또는 time 컬럼이 없어 EC 시계열을 그릴 수 없습니다.")

    st.markdown("---")
    st.markdown("### ✔ 원본 데이터")

    if selected_school == "전체":
        st.info("ℹ️ 원본 데이터 표/다운로드는 **학교를 선택**했을 때 제공합니다.")
    else:
        df_sel = env_data.get(selected_school)
        if df_sel is None:
            st.error(f"❌ 파일을 찾을 수 없습니다: data/{selected_school}_환경데이터.csv")
        elif df_sel.empty:
            st.warning("⚠️ 데이터가 비어있습니다.")
        else:
            with st.expander("원본 데이터 미리보기 (처음 100행)"):
                st.dataframe(df_sel.head(100), use_container_width=True)

            st.download_button(
                label=f"⬇️ {selected_school} 환경데이터 CSV 다운로드",
                data=download_csv_bytes(df_sel),
                file_name=f"{selected_school}_환경데이터_download.csv",
                mime="text/csv",
            )


# ---------------------------------
# Tab 3: 생육 결과 분석
# ---------------------------------
with tab3:
    st.warning(
        "⚠️ 이 데이터는 4개 학교의 개체가 합쳐진 데이터입니다.\n"
        "학교별 비교는 불가능합니다."
    )

    if growth_df is None or (isinstance(growth_df, pd.DataFrame) and growth_df.empty):
        st.error("❌ 생육 결과 데이터를 불러올 수 없습니다: data/4개교_생육결과데이터.xlsx")
    else:
        # 예상 컬럼명(요구사항 기준)
        # 개체번호, 잎 수(장), 지상부 길이(mm), 지하부 길이(mm), 생중량(g)
        # 데이터 제작자에 따라 약간 다를 수 있어, 최대한 그대로 쓰되 없으면 안내
        required_cols = ["잎 수(장)", "지상부 길이(mm)", "지하부 길이(mm)", "생중량(g)"]
        missing = [c for c in required_cols if c not in growth_df.columns]

        if missing:
            st.warning(
                "⚠️ 아래 컬럼이 엑셀에 없어서 일부 그래프/통계가 제한될 수 있습니다:\n"
                + "\n".join([f"- {c}" for c in missing])
            )

        st.markdown("### ✔ 전체 통계")

        def stat_block(colname, unit="", digits=2):
            if colname not in growth_df.columns:
                return ("N/A", "N/A")
            s = pd.to_numeric(growth_df[colname], errors="coerce")
            mean_v = s.mean()
            min_v = s.min()
            max_v = s.max()
            mean_txt = f"{fmt_num(mean_v, digits)}{unit}"
            range_txt = f"{fmt_num(min_v, digits)} ~ {fmt_num(max_v, digits)}{unit}"
            return (mean_txt, range_txt)

        c1, c2, c3 = st.columns(3)

        mean_w, range_w = stat_block("생중량(g)", " g", 2)
        mean_l, range_l = stat_block("잎 수(장)", " 장", 1)
        mean_sh, range_sh = stat_block("지상부 길이(mm)", " mm", 1)

        with c1:
            st.metric("평균 생중량", mean_w)
            st.caption(f"최소~최대: {range_w}")
        with c2:
            st.metric("평균 잎 수", mean_l)
            st.caption(f"최소~최대: {range_l}")
        with c3:
            st.metric("평균 지상부 길이", mean_sh)
            st.caption(f"최소~최대: {range_sh}")

        st.markdown("---")
        st.markdown("### ✔ 분포 그래프")

        # 히스토그램 3개
        hist_cols = st.columns(3)

        def draw_hist(colname, title):
            if colname not in growth_df.columns:
                return None
            s = pd.to_numeric(growth_df[colname], errors="coerce")
            tmp = pd.DataFrame({colname: s}).dropna()
            if tmp.empty:
                return None
            fig = px.histogram(tmp, x=colname, nbins=15, title=title)
            fig = set_plotly_korean(fig)
            return fig

        figs = [
            draw_hist("생중량(g)", "생중량 히스토그램"),
            draw_hist("잎 수(장)", "잎 수 히스토그램"),
            draw_hist("지상부 길이(mm)", "지상부 길이 히스토그램"),
        ]

        for i, figx in enumerate(figs):
            with hist_cols[i]:
                if figx is None:
                    st.info("표시할 데이터가 없어요.")
                else:
                    st.plotly_chart(figx, use_container_width=True)

        st.markdown("---")
        st.markdown("### ✔ 상관관계 (선택)")

        # 잎 수 vs 생중량, 지상부 길이 vs 생중량
        options = []
        if "잎 수(장)" in growth_df.columns and "생중량(g)" in growth_df.columns:
            options.append("잎 수 vs 생중량")
        if "지상부 길이(mm)" in growth_df.columns and "생중량(g)" in growth_df.columns:
            options.append("지상부 길이 vs 생중량")

        if not options:
            st.info("상관관계 그래프를 그리기 위한 컬럼이 부족합니다.")
        else:
            choice = st.selectbox("보고 싶은 관계를 선택하세요", options)

            if choice == "잎 수 vs 생중량":
                x_col, y_col = "잎 수(장)", "생중량(g)"
            else:
                x_col, y_col = "지상부 길이(mm)", "생중량(g)"

            tmp = growth_df[[x_col, y_col]].copy()
            tmp[x_col] = pd.to_numeric(tmp[x_col], errors="coerce")
            tmp[y_col] = pd.to_numeric(tmp[y_col], errors="coerce")
            tmp = tmp.dropna()

            if tmp.empty:
                st.info("표시할 데이터가 없어요.")
            else:
                fig_sc = px.scatter(tmp, x=x_col, y=y_col, title=f"{choice} 산점도")
                fig_sc = set_plotly_korean(fig_sc)
                st.plotly_chart(fig_sc, use_container_width=True)

# =========================
# 6) 푸터
# =========================
st.markdown("---")
st.markdown("Made with ❤️ by 극지식물 연구팀 | Powered by Streamlit")
