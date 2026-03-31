import numpy as np
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

from orbit.propagator import propagate_orbit
from orbit.groundtrack import eci_to_latlon
from orbit.tle_loader import load_tle
from orbit.tle_fetcher import fetch_multiple_tles
from orbit.collision import detect_collisions

app = Dash(__name__)

# ---------------- UI ----------------
app.layout = html.Div([
    html.H2("🛰️ Multi-Satellite Tracker (Live Data + Visual Collision)"),

    html.Div([
        html.Label("Simulation Duration (hours)"),
        dcc.Slider(1, 12, 1, value=4, id='duration',
                   marks={1: '1h', 4: '4h', 8: '8h', 12: '12h'}),
    ], style={'width': '30%', 'padding': '20px'}),

    html.Div([
        dcc.Graph(id='map'),
        dcc.Graph(id='orbit3d')
    ], style={'width': '65%'})
])


# ---------------- CALLBACK ----------------
@app.callback(
    Output('map', 'figure'),
    Output('orbit3d', 'figure'),
    Input('duration', 'value')
)
def update(duration):

    satellites = fetch_multiple_tles()

    fig_map = go.Figure()
    fig_3d = go.Figure()

    sat_positions = {}
    sat_last_positions = {}
    sat_latlon = {}

    # Earth sphere
    theta = np.linspace(0, 2*np.pi, 40)
    phi = np.linspace(0, np.pi, 40)
    R = 6371

    x = R * np.outer(np.cos(theta), np.sin(phi))
    y = R * np.outer(np.sin(theta), np.sin(phi))
    z = R * np.outer(np.ones(40), np.cos(phi))

    fig_3d.add_trace(go.Surface(x=x, y=y, z=z, opacity=0.3, showscale=False))

    colors = ['blue', 'red', 'green', 'orange', 'purple']

    # ---------------- LOOP ----------------
    for i, (name, tle1, tle2) in enumerate(satellites):

        try:
            orbit = load_tle(tle1, tle2)

            times, positions = propagate_orbit(orbit, duration_hours=duration, steps=150)
            lats, lons = eci_to_latlon(positions, times, orbit.epoch)

            # Store for collision detection
            sat_positions[name] = positions
            sat_last_positions[name] = positions[-1]
            sat_latlon[name] = (lats[-1], lons[-1])

            color = colors[i % len(colors)]

            # -------- MAP PATH --------
            fig_map.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode='lines',
                line=dict(width=2, color=color),
                name=name
            ))

            # -------- CURRENT POSITION --------
            fig_map.add_trace(go.Scattergeo(
                lat=[lats[-1]],
                lon=[lons[-1]],
                mode='markers+text',
                text=[name],
                textposition="top center",
                marker=dict(size=8, color=color),
                name=f"{name} (Now)"
            ))

            # -------- 3D PATH --------
            fig_3d.add_trace(go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode='lines',
                line=dict(width=3, color=color),
                name=name
            ))

            # -------- 3D CURRENT --------
            fig_3d.add_trace(go.Scatter3d(
                x=[positions[-1, 0]],
                y=[positions[-1, 1]],
                z=[positions[-1, 2]],
                mode='markers',
                marker=dict(size=5, color=color),
                name=f"{name} (Now)"
            ))

        except Exception as e:
            print(f"❌ Skipping {name}: {e}")

    # ---------------- COLLISION DETECTION ----------------
    alerts = detect_collisions(sat_positions)

    collision_pairs = set()
    for a in alerts:
        sat1, sat2, dist = a
        collision_pairs.add((sat1, sat2))

    # -------- VISUAL COLLISION (MAP) --------
    for (sat1, sat2) in collision_pairs:
        if sat1 in sat_latlon and sat2 in sat_latlon:

            lat1, lon1 = sat_latlon[sat1]
            lat2, lon2 = sat_latlon[sat2]

            fig_map.add_trace(go.Scattergeo(
                lat=[lat1, lat2],
                lon=[lon1, lon2],
                mode='lines',
                line=dict(width=4, color='red'),
                name=f"⚠️ {sat1}-{sat2}"
            ))

    # -------- VISUAL COLLISION (3D) --------
    for (sat1, sat2) in collision_pairs:
        if sat1 in sat_last_positions and sat2 in sat_last_positions:

            p1 = sat_last_positions[sat1]
            p2 = sat_last_positions[sat2]

            fig_3d.add_trace(go.Scatter3d(
                x=[p1[0], p2[0]],
                y=[p1[1], p2[1]],
                z=[p1[2], p2[2]],
                mode='lines',
                line=dict(width=6, color='red'),
                name=f"⚠️ {sat1}-{sat2}"
            ))

    # -------- ALERT TITLE --------
    if alerts:
        print("\n⚠️ COLLISION WARNING:")
        for a in alerts:
            print(f"{a[0]} ↔ {a[1]} | distance = {a[2]:.2f} km")

        fig_map.update_layout(title="⚠️ Collision Risk Detected!")
    else:
        fig_map.update_layout(title="🌍 Multi-Satellite Ground Track")

    fig_map.update_geos(showland=True, showocean=True)

    fig_3d.update_layout(
        title="🛰️ Multi-Satellite Orbits",
        scene=dict(aspectmode='data')
    )

    return fig_map, fig_3d


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)