import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from swmm_tools import (
    modify_inp, summarize, get_series, get_hydrograph,
    load_all, node_types, period_tables,
    NODE_VARS, LINK_VARS,
)
from map_view import read_geometry, draw_network

st.set_page_config(page_title="SWMM 월류 분석", layout="wide")

FILES = {
    "2년": "models/scenario_2yr.inp",
    "10년": "models/scenario_10yr.inp",
    "100년": "models/scenario_100yr.inp",
}

# 새로: 기본 시나리오 5개 (이름, 빈도, 강우배율, 불투수율 증가, 조도배율)
DEFAULTS = [
    ("2yr 원설계", "2년", 1.0, 0, 1.0),
    ("10yr 원설계", "10년", 1.0, 0, 1.0),
    ("100yr 원설계", "100년", 1.0, 0, 1.0),
    ("100yr 기후변화 ×1.3", "100년", 1.3, 0, 1.0),
    ("100yr ×1.3 · 불투수 +20%p · 조도 ×1.3", "100년", 1.3, 20, 1.3),
]
MAX_SAVED = 5


# 새로: 시나리오 하나 계산하기
def make_entry(name, freq, rain, imperv, rough, work_inp):
    modify_inp(FILES[freq], work_inp, rain_factor=rain, imperv_add=imperv, rough_factor=rough)
    res = summarize(work_inp)
    return {
        "name": name,
        "result": res,
        "hydro": get_hydrograph(res["out_file"]),
    }


# 새로: 시나리오를 목록에 저장하기
def save_entry(entry):
    saved = st.session_state.setdefault("saved", [])
    saved[:] = [s for s in saved if s["name"] != entry["name"]]
    saved.append(entry)
    if len(saved) > MAX_SAVED:
        saved.pop(0)


# 새로: 시나리오 비교 화면
def show_comparison(saved):
    rows = []
    for s in saved:
        r = s["result"]
        fl = r["floods"]
        rows.append({
            "시나리오": s["name"],
            "총 강우량(mm)": round(r["total_rain"], 1),
            "총 유출량(mm)": round(r["total_runoff"], 1),
            "첨두유량(m³/s)": round(r["peak_flow"], 3),
            "첨두시각": r["peak_time"],
            "최대충만도(%)": round(r["max_capacity"]),
            "월류 노드 수": len(fl),
            "총 월류량(m³)": round(sum(fl.values()), 1),
        })
    df = pd.DataFrame(rows)

    st.dataframe(df, hide_index=True)
    st.download_button(
        "시나리오 비교 CSV",
        df.to_csv(index=False).encode("utf-8-sig"),
        file_name="scenario_compare.csv",
        mime="text/csv",
    )

    col_a, col_b = st.columns(2)

    with col_a:
        fig = go.Figure(go.Bar(x=df["시나리오"], y=df["총 월류량(m³)"], marker_color="#d7191c"))
        fig.update_layout(title="시나리오별 총 월류량 (m³)", height=420)
        st.plotly_chart(fig)

    with col_b:
        fig = go.Figure()
        for s in saved:
            h = s["hydro"]
            fig.add_trace(go.Scatter(x=h.index, y=h["방류구 유량(m³/s)"], name=s["name"]))
        fig.update_layout(
            title="방류구 유량 비교 (m³/s)", height=420,
            xaxis_title="경과시간 (분)", legend=dict(orientation="h", y=-0.25),
        )
        st.plotly_chart(fig)


st.title("SWMM 우수관로 월류 분석")
st.write("강우와 유역 조건을 바꿔서 맨홀 월류 여부를 확인합니다.")

st.sidebar.header("입력 조건")
scenario = st.sidebar.selectbox("강우 빈도", ["2년", "10년", "100년"])
rain = st.sidebar.slider("강우 할증 배율", 1.0, 2.0, 1.0, 0.1)
imperv = st.sidebar.slider("불투수율 증가 (%p)", 0, 50, 0, 5)
rough = st.sidebar.slider("조도계수 배율", 1.0, 2.0, 1.0, 0.1)

auto_name = f"{scenario} ×{rain:.1f} / +{imperv}%p / n×{rough:.1f}"  # 새로
scen_name = st.sidebar.text_input("시나리오 이름 (비우면 자동)", "")  # 새로

if st.sidebar.button("계산 실행", type="primary"):  # 바뀜 (빨간 버튼)
    with st.spinner("SWMM 계산 중..."):
        modify_inp(
            FILES[scenario],
            "models/app_run.inp",
            rain_factor=rain,
            imperv_add=imperv,
            rough_factor=rough,
        )
        result = summarize("models/app_run.inp")
        result["tables"] = load_all(result["out_file"])
        result["types"] = node_types("models/app_run.inp")
        result["geom"] = read_geometry("models/app_run.inp")
        st.session_state["result"] = result

        # 새로: 계산한 결과를 비교 목록에도 저장
        save_entry({
            "name": scen_name or auto_name,
            "result": result,
            "hydro": get_hydrograph(result["out_file"]),
        })

# 새로: 일괄 실행과 저장 목록
st.sidebar.divider()
if st.sidebar.button("기본 시나리오 일괄 실행"):
    with st.spinner("기본 시나리오 5개 계산 중..."):
        for name, freq, r, i, n in DEFAULTS:
            save_entry(make_entry(name, freq, r, i, n, "models/batch_run.inp"))

saved = st.session_state.get("saved", [])
st.sidebar.caption(f"저장됨 {len(saved)}/{MAX_SAVED}")
for idx, s in enumerate(saved):
    c1, c2 = st.sidebar.columns([5, 1])
    c1.write(s["name"])
    if c2.button("✕", key=f"del_{idx}"):
        saved.pop(idx)
        st.rerun()

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

    minutes = result["tables"]["depth"].index
    t_min = float(minutes.min())
    t_max = float(minutes.max())
    start, end = st.slider(
        "분석 기간 (경과시간, 분)",
        t_min, t_max, (t_min, t_max), step=1.0,
        format="%.0f분",
    )

    node_df, link_df = period_tables(result["tables"], start, end, floods, result["types"])

    tab0, tab_map, tab1, tab2, tab_cmp = st.tabs(
        ["수문곡선", "관망도", "지점별 결과", "결과표", "시나리오 비교"]
    )  # 바뀜 (월류 현황 → 시나리오 비교)

    with tab0:
        hdf = get_hydrograph(result["out_file"]).loc[start:end]

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

    with tab_map:
        mode = st.radio("표시 기준", ["기간 최댓값", "특정 시각"], horizontal=True)

        if mode == "기간 최댓값":
            link_pct = dict(zip(link_df["관로"], link_df["최대충만도(%)"]))
            node_depth = dict(zip(node_df["노드"], node_df["최대수심(m)"]))
            node_flood = dict(zip(node_df["노드"], node_df["월류량(m³)"]))
            flood_label = "월류량(m³)"
        else:
            t = st.slider("시각 (경과시간, 분)", start, end, start, step=1.0, format="%.0f분")
            tables = result["tables"]
            link_pct = tables["capacity"].loc[t].to_dict()
            node_depth = tables["depth"].loc[t].to_dict()
            node_flood = tables["flood"].loc[t].to_dict()
            flood_label = "월류율(m³/s)"

        st.caption(
            "관로 색: 충만도(수심/만관 수심), 파랑→빨강 · "
            "빨간 원: 월류 발생, 크기는 월류량에 비례 · 마우스를 올리면 값이 보입니다."
        )
        st.plotly_chart(draw_network(result["geom"], link_pct, node_depth, node_flood, flood_label))

    with tab1:
        kind = st.radio("대상", ["노드", "관로"], horizontal=True)

        if kind == "노드":
            name = st.selectbox("노드", result["nodes"])
            labels = st.multiselect("변수", list(NODE_VARS), default=["수심(m)", "월류율(m³/s)"])
        else:
            name = st.selectbox("관로", result["links"])
            labels = st.multiselect("변수", list(LINK_VARS), default=["유량(m³/s)", "충만도(%)"])

        if labels:
            df = get_series(result["out_file"], kind, name, labels).loc[start:end]
            for label in labels:
                st.write(f"**{name} {label}**")
                st.line_chart(df[label])
        else:
            st.info("변수를 하나 이상 골라 주세요.")

    with tab2:
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

    # 새로: 시나리오 비교 탭
    with tab_cmp:
        if saved:
            show_comparison(saved)
        else:
            st.info("저장된 시나리오가 없습니다.")

# 새로: 계산 실행 없이 일괄 실행만 한 경우에도 비교 화면 보여주기
elif saved:
    st.subheader("시나리오 비교")
    show_comparison(saved)
else:
    st.info("왼쪽에서 조건을 고르고 [계산 실행]을 누르거나, [기본 시나리오 일괄 실행]을 눌러 주세요.")