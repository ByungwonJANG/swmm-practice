from pyswmm import Simulation, Nodes, Links

inp_file = "models/base.inp"

FT_TO_M = 0.3048
CFS_TO_CMS = 0.0283
FT3_TO_M3 = 0.0283
with Simulation(inp_file) as sim:
    nodes = Nodes(sim)
    links = Links(sim)

    for step in sim:
        pass

    print("=== 맨홀 결과 ===")
    print("맨홀    최대수심(m)    월류량(㎥)")
    for node in nodes:
        stats = node.statistics
        print(f"{node.nodeid:6} {stats['max_depth'] * FT_TO_M:8.2f} {stats['flooding_volume'] * FT3_TO_M3:10.2f}")

    print()
    print("=== 관로 결과 ===")
    print("관로    최대유량(㎥.s)")
    for link in links:
        stats = link.conduit_statistics
        print(f"{link.linkid:6} {stats['peak_flow'] * CFS_TO_CMS:8.3f}")