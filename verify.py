from pyswmm import Simulation, Nodes, Links

inp_file = "models/scenario_100yr.inp"

with Simulation(inp_file) as sim:
    nodes = Nodes(sim)
    links = Links(sim)

    for step in sim:
        pass

    print("=== 맨홀 최대수심 (ft) ===")
    for node in nodes:
        print(f"{node.nodeid:6} {node.statistics['max_depth']:8.2f}")

    print()
    print("=== 관로 최대유량 (CFS) ===")
    for link in links:
        print(f"{link.linkid:6} {link.conduit_statistics['peak_flow']:8.2f}")