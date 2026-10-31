from map_view import read_geometry

geom = read_geometry("models/base.inp")
print("맨홀 좌표:", len(geom["coords"]), "개")
print("관로:", len(geom["conduits"]), "개")
print("관로 꺾인점:", len(geom["vertices"]), "개 관로")
print("소유역 경계:", len(geom["polygons"]), "개")
print()
print("J1 좌표:", geom["coords"]["J1"])
print("C1 연결:", geom["conduits"]["C1"])