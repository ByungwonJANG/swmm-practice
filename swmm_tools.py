from pyswmm import Simulation, Nodes, Links

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