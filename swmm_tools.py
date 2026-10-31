import pandas as pd  # 새로 추가
from pyswmm import Simulation, Nodes, Links, Output, NodeSeries, LinkSeries, SystemSeries  # 바뀜 (NodeSeries 추가)

FT_TO_M = 0.3048  # 새로 추가
CFS_TO_CMS = 0.0283168
FT3_TO_M3 = 0.0283168

# 새로 추가: 화면에 보여줄 이름 → (.out 파일 속성 이름, 환산 계수)
NODE_VARS = {
    "수심(m)": ("invert_depth", FT_TO_M),
    "월류율(m³/s)": ("flooding_losses", CFS_TO_CMS),
    "유입량(m³/s)": ("total_inflow", CFS_TO_CMS),
}

LINK_VARS = {
    "유량(m³/s)": ("flow_rate", CFS_TO_CMS),
    "수심(m)": ("flow_depth", FT_TO_M),
    "유속(m/s)": ("flow_velocity", FT_TO_M),
    "충만도(%)": ("capacity", 100),
}


def modify_inp(src, dst, rain_factor=1.0, imperv_add=0.0, rough_factor=1.0):
    with open(src, encoding="utf-8") as f:
        lines = f.read().splitlines()

    section = ""
    new_lines = []

    for line in lines:
        text = line.strip()

        if text.startswith("["):
            section = text.upper()
            new_lines.append(line)
            continue

        if not text or text.startswith(";"):
            new_lines.append(line)
            continue

        parts = line.split()

        if section == "[TIMESERIES]":
            value = float(parts[-1]) * rain_factor
            parts[-1] = f"{value:.4f}"
        elif section == "[SUBCATCHMENTS]":
            imperv = float(parts[4]) + imperv_add
            imperv = max(0, min(imperv, 100))
            parts[4] = f"{imperv:.2f}"
        elif section == "[CONDUITS]":
            rough = float(parts[4]) * rough_factor
            parts[4] = f"{rough:.4f}"
        else:
            new_lines.append(line)
            continue

        new_lines.append("  ".join(parts))

    with open(dst, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))


def run_model(inp_file):
    with Simulation(inp_file) as sim:
        nodes = Nodes(sim)
        links = Links(sim)

        for step in sim:
            pass

        floods = {}
        for node in nodes:
            volume = node.statistics["flooding_volume"] * FT3_TO_M3
            if volume > 0:
                floods[node.nodeid] = volume

        outlet_flow = links["C11"].conduit_statistics["peak_flow"] * CFS_TO_CMS

    return outlet_flow, floods


def total_area_acres(inp_file):
    with open(inp_file, encoding="utf-8") as f:
        lines = f.read().splitlines()

    section = ""
    total = 0.0

    for line in lines:
        text = line.strip()
        if text.startswith("["):
            section = text.upper()
            continue
        if not text or text.startswith(";"):
            continue
        if section == "[SUBCATCHMENTS]":
            total += float(line.split()[3])

    return total


def summarize(inp_file):
    flow, floods = run_model(inp_file)
    out_file = inp_file.replace(".inp", ".out")

    with Output(out_file) as out:
        rain = SystemSeries(out).rainfall
        runoff = SystemSeries(out).runoff_flow
        outlet = LinkSeries(out)["C11"].flow_rate
        node_names = list(out.nodes)  # 새로 추가
        link_names = list(out.links)  # 새로 추가

        max_capacity = 0.0
        for name in out.links:
            capacity = max(LinkSeries(out)[name].capacity.values())
            if capacity > max_capacity:
                max_capacity = capacity

    times = list(rain.keys())
    step = times[1] - times[0]
    step_s = step.total_seconds()
    start = times[0] - step

    total_rain = sum(rain.values()) * step_s / 3600 * 25.4

    area_ft2 = total_area_acres(inp_file) * 43560
    total_runoff = sum(runoff.values()) * step_s / area_ft2 * 304.8

    peak_time = max(outlet, key=outlet.get)
    peak_flow = outlet[peak_time] * CFS_TO_CMS
    minutes = int((peak_time - start).total_seconds() // 60)
    peak_label = f"{minutes // 60:02d}:{minutes % 60:02d}"

    return {
        "total_rain": total_rain,
        "total_runoff": total_runoff,
        "peak_flow": peak_flow,
        "peak_time": peak_label,
        "max_capacity": max_capacity * 100,
        "floods": floods,
        "nodes": node_names,  # 새로 추가
        "links": link_names,  # 새로 추가
        "out_file": out_file,  # 새로 추가
    }


# 새로 추가: 노드나 관로 하나의 시간별 값을 표로 꺼내기
def get_series(out_file, kind, name, labels):
    if kind == "노드":
        var_table = NODE_VARS
    else:
        var_table = LINK_VARS

    data = {}
    with Output(out_file) as out:
        if kind == "노드":
            series = NodeSeries(out)[name]
        else:
            series = LinkSeries(out)[name]

        for label in labels:
            attr, factor = var_table[label]
            values = getattr(series, attr)

            converted = {}
            for t, v in values.items():
                converted[t] = v * factor
            data[label] = converted

    df = pd.DataFrame(data)

    times = list(df.index)
    step = times[1] - times[0]
    start = times[0] - step
    df.index = [(t - start).total_seconds() / 60 for t in times]
    df.index.name = "경과시간(분)"

    return df


def get_hydrograph(out_file):
    with Output(out_file) as out:
        rain = SystemSeries(out).rainfall
        outflow = NodeSeries(out)["O1"].total_inflow

    rain_mm = {}
    for t, v in rain.items():
        rain_mm[t] = v * 25.4

    outflow_cms = {}
    for t, v in outflow.items():
        outflow_cms[t] = v * CFS_TO_CMS

    df = pd.DataFrame({
        "강우강도(mm/hr)": rain_mm,
        "방류구 유량(m³/s)": outflow_cms,
    })

    times = list(df.index)
    step = times[1] - times[0]
    start = times[0] - step
    df.index = [(t - start).total_seconds() / 60 for t in times]
    df.index.name = "경과시간(분)"

    return df


def to_minutes(df):
    times = list(df.index)
    step = times[1] - times[0]
    start = times[0] - step
    df.index = [(t - start).total_seconds() / 60 for t in times]
    df.index.name = "경과시간(분)"
    return df


def load_all(out_file):
    depth, flood, flow, capacity = {}, {}, {}, {}

    with Output(out_file) as out:
        for name in out.nodes:
            series = NodeSeries(out)[name]
            depth[name] = series.invert_depth
            flood[name] = series.flooding_losses

        for name in out.links:
            series = LinkSeries(out)[name]
            flow[name] = series.flow_rate
            capacity[name] = series.capacity

    return {
        "depth": to_minutes(pd.DataFrame(depth) * FT_TO_M),
        "flood": to_minutes(pd.DataFrame(flood) * CFS_TO_CMS),
        "flow": to_minutes(pd.DataFrame(flow) * CFS_TO_CMS),
        "capacity": to_minutes(pd.DataFrame(capacity) * 100),
    }


def node_types(inp_file):
    type_names = {
        "[JUNCTIONS]": "JUNCTION",
        "[OUTFALLS]": "OUTFALL",
        "[STORAGE]": "STORAGE",
        "[DIVIDERS]": "DIVIDER",
    }

    with open(inp_file, encoding="utf-8") as f:
        lines = f.read().splitlines()

    section = ""
    types = {}

    for line in lines:
        text = line.strip()
        if text.startswith("["):
            section = text.upper()
            continue
        if not text or text.startswith(";"):
            continue
        if section in type_names:
            types[line.split()[0]] = type_names[section]

    return types


def minute_label(m):
    m = int(round(m))
    return f"{m // 60:02d}:{m % 60:02d}"


def period_tables(tables, start, end, floods, types):
    depth = tables["depth"].loc[start:end]
    flood = tables["flood"].loc[start:end]
    flow = tables["flow"].loc[start:end]
    capacity = tables["capacity"].loc[start:end]

    if depth.empty:
        return pd.DataFrame(), pd.DataFrame()

    full_index = tables["depth"].index
    full = start <= full_index.min() and end >= full_index.max()
    step_s = (full_index[1] - full_index[0]) * 60

    node_rows = []
    for name in depth.columns:
        if full:
            volume = floods.get(name, 0.0)
        else:
            volume = flood[name].sum() * step_s

        node_rows.append({
            "노드": name,
            "유형": types.get(name, ""),
            "최대수심(m)": round(depth[name].max(), 3),
            "최대수심 시각": minute_label(depth[name].idxmax()),
            "월류량(m³)": round(volume, 1),
            "최대 월류율(m³/s)": round(flood[name].max(), 3),
        })

    link_rows = []
    for name in flow.columns:
        link_rows.append({
            "관로": name,
            "최대유량(m³/s)": round(flow[name].max(), 3),
            "최대유량 시각": minute_label(flow[name].idxmax()),
            "최대충만도(%)": round(capacity[name].max(), 1),
        })

    return pd.DataFrame(node_rows), pd.DataFrame(link_rows)