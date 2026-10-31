import streamlit as st
import pandas as pd
import plotly.graph_objects as go
st.set_page_config(page_title="SWMM 월류 분석", layout="wide")
from plotly.subplots import make_subplots
from swmm_tools import (
    modify_inp, summarize, get_series, get_hydrograph,
    load_all, node_types, period_tables,  # 새로
    NODE_VARS, LINK_VARS,
)

st.title("SWMM 우수관로 월류 분석")
st.write("강우와 유역 조건을 바꿔서 맨홀 월류 여부를 확인합니다.")

st.sidebar.header("입력 조건")
scenario = st.sidebar.selectbox("강우 빈도", ["2년", "10년", "100년"])
rain = st.sidebar.slider("강우 할증 배율", 1.0, 2.0, 1.0, 0.1)
imperv = st.sidebar.slider("불투수율 증가 (%p)", 0, 50, 0, 5)
rough = st.sidebar.slider("조도계수 배율", 1.0, 2.0, 1.0, 0.1)

files = {
    "2년": "models/scenario_2yr.inp",
    "10년": "models/scenario_10yr.inp",
    "100년": "models/scenario_100yr.inp",
}

if st.sidebar.button("계산 실행"):
    with st.spinner("SWMM 계산 중..."):
        modify_inp(
            files[scenario],
            "models/app_run.inp",
            rain_factor=rain,
            imperv_add=imperv,
            rough_factor=rough,
        )
        result = summarize("models/app_run.inp")
        result["tables"] = load_all(result["out_file"])  # 새로
        result["types"] = node_types("models/app_run.inp")  # 새로
        st.session_state["result"] = result

if "result" in st.session_state:
    result = st.session_state["result"]
    floods = result["floods"]

    row1 = st.columns(4)
    row1[0].metric("총 강우량", f"{result['total_rain']:.1f} mm")
    row1[1].metric("총 유출량", f"{result['total_runoff']:.1f} mm")
    row1[2].metric("방류구 첨두유량", f"{result['peak_flow']:.3f} m³/s")
    row1[3].metric("첨두 발생시각", result["peak_time"])

    row2 = st.columns(3)
    row2[0].metric("최대 관로 충만도", f"{result['max_capacity']:.0f} %")
    row2[1].metric("월류 노드 수", f"{len(floods)}개")
    row2[2].metric("총 월류량", f"{sum(floods.values()):.1f} m³")

    # 새로: 분석 기간 슬라이더
    minutes = result["tables"]["depth"].index
    t_min = float(minutes.min())
    t_max = float(minutes.max())
    start, end = st.slider(
        "분석 기간 (경과시간, 분)",
        t_min, t_max, (t_min, t_max), step=1.0,
    )

    tab0, tab1, tab2, tab3 = st.tabs(["수문곡선", "지점별 결과", "결과표", "월류 현황"])  # 바뀜

    with tab0:
        hdf = get_hydrograph(result["out_file"]).loc[start:end]  # 바뀜 (.loc 추가)

        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.3, 0.7],
            vertical_spacing=0.05,
        )
        fig.add_trace(
            go.Bar(x=hdf.index, y=hdf["강우강도(mm/hr)"], name="강우강도", marker_color="#4a90d9"),
            row=1, col=1,
        )
        fig.add_trace(
            go.Scatter(x=hdf.index, y=hdf["방류구 유량(m³/s)"], name="방류구 O1", line=dict(color="#5aaee8")),
            row=2, col=1,
        )
        fig.update_yaxes(autorange="reversed", title_text="강우강도 (mm/hr)", row=1, col=1)
        fig.update_yaxes(title_text="유량 (m³/s)", row=2, col=1)
        fig.update_xaxes(title_text="경과시간 (분)", row=2, col=1)
        fig.update_layout(height=550, bargap=0, legend=dict(orientation="h", y=1.08))

        st.plotly_chart(fig)

    with tab1:
        kind = st.radio("대상", ["노드", "관로"], horizontal=True)

        if kind == "노드":
            name = st.selectbox("노드", result["nodes"])
            labels = st.multiselect("변수", list(NODE_VARS), default=["수심(m)", "월류율(m³/s)"])
        else:
            name = st.selectbox("관로", result["links"])
            labels = st.multiselect("변수", list(LINK_VARS), default=["유량(m³/s)", "충만도(%)"])

        if labels:
            df = get_series(result["out_file"], kind, name, labels).loc[start:end]  # 바뀜 (.loc 추가)
            for label in labels:
                st.write(f"**{name} {label}**")
                st.line_chart(df[label])
        else:
            st.info("변수를 하나 이상 골라 주세요.")

    # 새로: 결과표 탭
    with tab2:
        node_df, link_df = period_tables(result["tables"], start, end, floods, result["types"])

        st.caption(
            f"분석 기간 {start:.0f}~{end:.0f}분의 1분 간격 기록값 기준입니다. "
            "월류량은 전체 기간이면 SWMM 요약값, 일부 기간이면 월류율을 시간에 대해 더한 값입니다."
        )

        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("노드별 최댓값")
            st.dataframe(node_df, hide_index=True)
            st.download_button(
                "노드 결과 CSV",
                node_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="node_results.csv",
                mime="text/csv",
            )

        with col_b:
            st.subheader("관로별 최댓값")
            st.dataframe(link_df, hide_index=True)
            st.download_button(
                "관로 결과 CSV",
                link_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="link_results.csv",
                mime="text/csv",
            )

    with tab3:
        if floods:
            df = pd.DataFrame(list(floods.items()), columns=["맨홀", "월류량(m³)"])
            df = df.sort_values("월류량(m³)", ascending=False)
            st.dataframe(df, hide_index=True)
            st.bar_chart(df, x="맨홀", y="월류량(m³)")
        else:
            st.success("월류가 발생하지 않았습니다.")
else:
    st.info("왼쪽에서 조건을 고르고 [계산 실행]을 눌러 주세요.")