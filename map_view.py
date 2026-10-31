import plotly.graph_objects as go
from plotly.colors import sample_colorscale

SCALE = [
    [0.0, "rgb(44,123,182)"],
    [0.5, "rgb(255,255,191)"],
    [1.0, "rgb(215,25,28)"],
]


def read_geometry(inp_file):
    with open(inp_file, encoding="utf-8") as f:
        lines = f.read().splitlines()

    geom = {"coords": {}, "vertices": {}, "polygons": {}, "conduits": {}}
    section = ""

    for line in lines:
        text = line.strip()
        if text.startswith("["):
            section = text.upper()
            continue
        if not text or text.startswith(";"):
            continue

        parts = line.split()

        if section == "[COORDINATES]":
            geom["coords"][parts[0]] = (float(parts[1]), float(parts[2]))
        elif section == "[VERTICES]":
            geom["vertices"].setdefault(parts[0], []).append((float(parts[1]), float(parts[2])))
        elif section == "[POLYGONS]":
            geom["polygons"].setdefault(parts[0], []).append((float(parts[1]), float(parts[2])))
        elif section == "[CONDUITS]":
            geom["conduits"][parts[0]] = (parts[1], parts[2])

    return geom


def draw_network(geom, link_pct, node_depth, node_flood, flood_label):
    fig = go.Figure()

    for name, pts in geom["polygons"].items():
        xs = [p[0] for p in pts] + [pts[0][0]]
        ys = [p[1] for p in pts] + [pts[0][1]]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", fill="toself",
            fillcolor="rgba(200,200,200,0.2)",
            line=dict(color="#bbbbbb", width=1),
            hoverinfo="text", text=f"소유역 {name}",
            showlegend=False,
        ))

    for name, (n1, n2) in geom["conduits"].items():
        pts = [geom["coords"][n1]] + geom["vertices"].get(name, []) + [geom["coords"][n2]]
        pct = link_pct.get(name, 0)
        color = sample_colorscale(SCALE, [min(pct, 100) / 100])[0]
        fig.add_trace(go.Scatter(
            x=[p[0] for p in pts], y=[p[1] for p in pts],
            mode="lines", line=dict(color=color, width=5),
            hoverinfo="text", text=f"{name}<br>충만도 {pct:.1f}%",
            showlegend=False,
        ))

    names = list(geom["coords"])
    fig.add_trace(go.Scatter(
        x=[geom["coords"][n][0] for n in names],
        y=[geom["coords"][n][1] for n in names],
        mode="markers", marker=dict(size=8, color="#555555"),
        hoverinfo="text",
        text=[f"{n}<br>수심 {node_depth.get(n, 0):.2f} m" for n in names],
        showlegend=False,
    ))

    flooded = [n for n in names if node_flood.get(n, 0) > 0]
    if flooded:
        vmax = max(node_flood[n] for n in flooded)
        fig.add_trace(go.Scatter(
            x=[geom["coords"][n][0] for n in flooded],
            y=[geom["coords"][n][1] for n in flooded],
            mode="markers",
            marker=dict(
                size=[14 + 30 * node_flood[n] / vmax for n in flooded],
                color="rgba(220,30,30,0.55)",
                line=dict(color="darkred", width=1),
            ),
            hoverinfo="text",
            text=[f"{n}<br>{flood_label} {node_flood[n]:.2f}" for n in flooded],
            name="월류 발생",
        ))

    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode="markers",
        marker=dict(
            colorscale=SCALE, cmin=0, cmax=100, color=[0],
            showscale=True, colorbar=dict(title="충만도(%)"),
        ),
        hoverinfo="none", showlegend=False,
    ))

    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=650, plot_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", x=0, y=1.05),
    )

    return fig