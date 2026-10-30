from pyswmm import Simulation, Nodes, Links

FT_TO_M = 0.3048
CFS_TO_CMS = 0.0283
FT3_TO_M3 = 0.0283


def run_scenario(inp_file):
    with Simulation(inp_file) as sim:
        nodes = Nodes(sim)
        links = Links(sim)

        for step in sim:
            pass

        flood_nodes = 0
        total_flood = 0.0
        max_depth = 0.0

        for node in nodes:
            stats = node.statistics
            volume = stats["flooding_volume"] * FT3_TO_M3
            depth = stats["max_depth"] * FT_TO_M

            if volume > 0:
                flood_nodes += 1
                total_flood += volume

            if depth > max_depth:
                max_depth = depth

        outlet_flow = links["C11"].conduit_statistics["peak_flow"] * CFS_TO_CMS

    return outlet_flow, max_depth, flood_nodes, total_flood


scenarios = [
    ("2년", "models/scenario_2yr.inp"),
    ("10년", "models/scenario_10yr.inp"),
    ("100년", "models/scenario_100yr.inp"),
]

print("빈도    방류유량(m³/s)  최대수심(m)  월류노드수  총월류량(m³)")
for label, inp_file in scenarios:
    flow, depth, n_flood, volume = run_scenario(inp_file)
    print(f"{label:5} {flow:12.3f} {depth:12.2f} {n_flood:10d} {volume:12.1f}")