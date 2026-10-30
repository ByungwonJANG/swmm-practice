from pyswmm import Simulation, Nodes, Links, Output, LinkSeries, SystemSeries

CFS_TO_CMS = 0.0283
FT3_TO_M3 = 0.0283


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
    }