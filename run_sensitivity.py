from swmm_tools import modify_inp, run_model

cases = [
    ("기준 (100년)", 1.0, 0, 1.0),
    ("강우만 x1.5", 1.5, 0, 1.0),
    ("불투수율만 +20%p", 1.0, 20, 1.0),
    ("조도만 x1.3", 1.0, 0, 1.3),
    ("세 조건 모두", 1.5, 20, 1.3),
]

print("조건                 방류유량(m³/s)  월류노드  총월류량(m³)")
for label, rain, imperv, rough in cases:
    modify_inp(
        "models/scenario_100yr.inp",
        "models/test.inp",
        rain_factor=rain,
        imperv_add=imperv,
        rough_factor=rough,
    )
    flow, floods = run_model("models/test.inp")
    print(f"{label:18} {flow:12.3f} {len(floods):8d} {sum(floods.values()):12.1f}")