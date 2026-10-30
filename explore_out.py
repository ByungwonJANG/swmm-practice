from pyswmm import Output, NodeSeries, LinkSeries, SystemSeries
from swmm_tools import run_model

run_model("models/scenario_2yr.inp")

with Output("models/scenario_2yr.out") as out:
    rain = SystemSeries(out).rainfall
    depth_j1 = NodeSeries(out)["J1"].invert_depth
    flow_c11 = LinkSeries(out)["C11"].flow_rate

times = list(rain.keys())
step_hr = (times[1] - times[0]).total_seconds() / 3600

print(f"기록된 시각 개수: {len(times)}개")
print(f"처음: {times[0]}, 마지막: {times[-1]}")
print(f"보고 간격: {step_hr * 60:.0f}분")
print()

print("시각    강우(mm/hr)  J1수심(m)  C11유량(m³/s)")
for t in times[:40]:
    print(f"{t.strftime('%H:%M')} {rain[t] * 25.4:12.1f} {depth_j1[t] * 0.3048:10.3f} {flow_c11[t] * 0.0283:12.3f}")

print()
total_rain = sum(rain.values()) * step_hr * 25.4
peak_flow = max(flow_c11.values()) * 0.0283
print(f"총 강우량: {total_rain:.1f} mm")
print(f"C11 첨두유량 (기록값 중 최대): {peak_flow:.3f} m³/s")