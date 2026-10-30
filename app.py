import streamlit as st
import pandas as pd
from swmm_tools import modify_inp, run_model

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
        flow, floods = run_model("models/app_run.inp")

    col1, col2, col3 = st.columns(3)
    col1.metric("방류유량", f"{flow:.3f} m³/s")
    col2.metric("월류 맨홀 수", f"{len(floods)}개")
    col3.metric("총 월류량", f"{sum(floods.values()):.1f} m³")

    if floods:
        st.subheader("맨홀별 월류량")
        df = pd.DataFrame(list(floods.items()), columns=["맨홀", "월류량(m³)"])
        df = df.sort_values("월류량(m³)", ascending=False)
        st.dataframe(df, hide_index=True)
        st.bar_chart(df, x="맨홀", y="월류량(m³)")
    else:
        st.success("월류가 발생하지 않았습니다.")