
import plotly.graph_objects as go
import numpy as np
from orbit.propagator import create_orbit, propagate_orbit
from orbit.groundtrack import eci_to_latlon

# Create orbit
orbit = create_orbit(700)

# Simulate
times, positions = propagate_orbit(orbit, duration_hours=4, steps=500)

# -------- 3D ORBIT --------

fig_3d = go.Figure()

# Satellite orbit line
fig_3d.add_trace(go.Scatter3d(
    x=positions[:, 0],
    y=positions[:, 1],
    z=positions[:, 2],
    mode='lines',
    line=dict(width=4),
    name='Orbit'
))

# Earth sphere
theta = np.linspace(0, 2*np.pi, 50)
phi = np.linspace(0, np.pi, 50)

R = 6371  # Earth radius (km)

x = R * np.outer(np.cos(theta), np.sin(phi))
y = R * np.outer(np.sin(theta), np.sin(phi))
z = R * np.outer(np.ones(50), np.cos(phi))

fig_3d.add_trace(go.Surface(
    x=x, y=y, z=z,
    opacity=0.4,
    showscale=False,
    name='Earth'
))

fig_3d.update_layout(
    title="3D Orbit Around Earth",
    scene=dict(aspectmode='data')
)

fig_3d.show()