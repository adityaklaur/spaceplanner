import numpy as np
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go

from orbit.propagator import propagate_orbit
from orbit.groundtrack import eci_to_latlon
from orbit.tle_loader import load_tle
from orbit.tle_fetcher import fetch_multiple_tles
from orbit.predict_collision import predict_collisions
from orbit.avoidance import suggest_avoidance
from orbit.optimizer import optimize_avoidance

app = Dash(__name__)


# 🔴 TLE fetched once
satellites = fetch_multiple_tles()

# 🔴 Orbit cache
orbit_cache = {}

# ---------------- UI ----------------
app.layout = html.Div([
    html.H2("🛰️ Multi-Satellite Tracker (Optimized System)", style={
        'color': 'white',
        'textAlign': 'center'
    }),

    html.Div([
        html.Label("Simulation Duration (hours)", style={'color': 'white'}),
        dcc.Slider(1, 12, 1, value=4, id='duration',
                   marks={1: '1h', 4: '4h', 8: '8h', 12: '12h'}),
    ], style={'width': '30%', 'padding': '20px'}),

    html.Div(id='alerts-panel', style={
        'padding': '15px',
        'margin': '10px',
        'backgroundColor': '#1e1e1e',
        'border': '1px solid #ff4d4d',
        'borderRadius': '8px',
        'color': 'white',
        'width': '30%'
    }),

    html.Div([
        dcc.Graph(id='map'),
        dcc.Graph(id='orbit3d')
    ], style={'width': '65%'}),

    # 🔴 FIX 4: slower updates
    dcc.Interval(id='interval', interval=4000, n_intervals=0)

], style={
    'backgroundColor': '#0b0f1a',
    'minHeight': '100vh'
})


# ---------------- CALLBACK ----------------
@app.callback(
    Output('map', 'figure'),
    Output('orbit3d', 'figure'),
    Output('alerts-panel', 'children'),
    Input('duration', 'value'),
    Input('interval', 'n_intervals')
)
def update(duration, n_intervals):

    fig_map = go.Figure()
    fig_3d = go.Figure()

    sat_positions = {}
    sat_last_positions = {}
    sat_latlon = {}

    # Earth
    theta = np.linspace(0, 2*np.pi, 40)
    phi = np.linspace(0, np.pi, 40)
    R = 6371

    x = R * np.outer(np.cos(theta), np.sin(phi))
    y = R * np.outer(np.sin(theta), np.sin(phi))
    z = R * np.outer(np.ones(40), np.cos(phi))

    fig_3d.add_trace(go.Surface(
        x=x, y=y, z=z,
        opacity=0.3,
        showscale=False,
        colorscale='Blues'
    ))

    colors = ['cyan', 'magenta', 'lime', 'orange', 'yellow']

    # ---------------- LOOP ----------------
    for i, (name, tle1, tle2) in enumerate(satellites):

        try:
            # 🔴 FIX 3: ORBIT CACHE
            if name not in orbit_cache:
                orbit = load_tle(tle1, tle2)
                times, positions = propagate_orbit(orbit, duration_hours=duration, steps=60)
                epoch = orbit.epoch
                orbit_cache[name] = (times, positions, epoch)
            else:
                times, positions, epoch = orbit_cache[name]

            lats, lons = eci_to_latlon(positions, times, epoch)

            idx = n_intervals % len(positions)

            sat_positions[name] = positions
            sat_last_positions[name] = positions[idx]
            sat_latlon[name] = (lats[idx], lons[idx])

            color = colors[i % len(colors)]

            # MAP
            fig_map.add_trace(go.Scattergeo(
                lat=lats,
                lon=lons,
                mode='lines',
                line=dict(width=3, color=color),
                name=name
            ))

            fig_map.add_trace(go.Scattergeo(
                lat=[lats[idx]],
                lon=[lons[idx]],
                mode='markers+text',
                text=[name],
                textposition="top center",
                marker=dict(size=9, color=color),
                name=f"{name} (Now)"
            ))

            # 3D
            fig_3d.add_trace(go.Scatter3d(
                x=positions[:, 0],
                y=positions[:, 1],
                z=positions[:, 2],
                mode='lines',
                line=dict(width=4, color=color),
                name=name
            ))

            fig_3d.add_trace(go.Scatter3d(
                x=[positions[idx, 0]],
                y=[positions[idx, 1]],
                z=[positions[idx, 2]],
                mode='markers',
                marker=dict(size=6, color=color),
                name=f"{name} (Now)"
            ))

        except Exception as e:
            print(f"❌ Skipping {name}: {e}")

    # ---------------- PREDICTION ----------------
    alerts = predict_collisions(sat_positions)
    suggestions = suggest_avoidance(alerts)
    optimized = optimize_avoidance(alerts, sat_positions)

    collision_pairs = set()
    alert_ui = []

    if alerts:
        alert_ui.append(html.H4("💀 Collision Alerts + AI Optimization", style={'color': '#ff4d4d'}))

        for i, a in enumerate(alerts):
            sat1, sat2, dist, step = a
            collision_pairs.add((sat1, sat2))

            time_sec = step * (duration * 3600 / 60)

            rule_action = suggestions[i][2]
            dv = optimized[i][2]
            opt_action = optimized[i][3]

            alert_ui.append(html.Div([
                html.B(f"{sat1} ↔ {sat2}"),
                html.Br(),
                html.Span(f"Distance: {dist:.2f} km"),
                html.Br(),
                html.Span(f"In ~{time_sec/60:.1f} minutes"),
                html.Br(),
                html.B(rule_action),
                html.Br(),
                html.Span(f"Δv Required: {dv:.2f} m/s"),
                html.Br(),
                html.B(opt_action)
            ], style={
                'marginBottom': '10px',
                'padding': '10px',
                'backgroundColor': '#2a1a1a',
                'borderRadius': '6px'
            }))

        fig_map.update_layout(title="💀 Collision + Optimized Maneuver")

    else:
        alert_ui.append(html.H4("✅ No Collision Risk", style={'color': 'lightgreen'}))
        fig_map.update_layout(title="🌍 Multi-Satellite Ground Track")

    # -------- DARK MAP --------
    fig_map.update_geos(
        showland=True,
        landcolor="#1c1c1c",
        showocean=True,
        oceancolor="#0b3d91",
        coastlinecolor="white",
        bgcolor="#0b0f1a"
    )

    fig_map.update_layout(
        paper_bgcolor="#0b0f1a",
        font=dict(color="white")
    )

    # -------- DARK 3D --------
    fig_3d.update_layout(
        title="🛰️ Multi-Satellite Orbits",
        scene=dict(
            bgcolor="#0b0f1a",
            xaxis=dict(showbackground=False, color="white"),
            yaxis=dict(showbackground=False, color="white"),
            zaxis=dict(showbackground=False, color="white"),
        ),
        paper_bgcolor="#0b0f1a",
        font=dict(color="white")
    )

    return fig_map, fig_3d, alert_ui


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)