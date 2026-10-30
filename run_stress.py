from swmm_tools import modify_inp, run_model

modify_inp(
    "models/scenario_100yr.inp",
    "models/stress.inp",
    rain_factor=1.5,
    imperv_add=20,
    rough_factor=1.3,
)

flow, floods = run_model("models/stress.inp")

print("조건: 100년 빈도 x1.5, 불투수율 +20%p, 조도계수 x1.3")
print(f"방류유량: {flow:.3f} m³/s")
print(f"월류 노드 수: {len(floods)}개")
print(f"총 월류량: {sum(floods.values()):.1f} m³")
print()
print("맨홀별 월류량")
for node_id, volume in floods.items():
    print(f"  {node_id:5} {volume:8.1f} m³")