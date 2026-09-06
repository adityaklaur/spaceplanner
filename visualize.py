"""Small standalone 3D visualization example using the offline sample TLE."""
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from orbit.propagator import propagate_orbit
from orbit.tle_fetcher import _parse_three_line_tles
from orbit.tle_loader import load_tle


sample_text = Path("orbit/sample_tles.txt").read_text(encoding="utf-8")
name, tle1, tle2 = _parse_three_line_tles(sample_text, limit=1)[0]
orbit = load_tle(tle1, tle2)
_, positions = propagate_orbit(orbit, duration_hours=2, steps=180, start_time=orbit.epoch)

fig = go.Figure()
fig.add_trace(go.Scatter3d(
    x=positions[:, 0], y=positions[:, 1], z=positions[:, 2],
    mode="lines", name=name,
))

radius_km = 6371.0
theta = np.linspace(0, 2 * np.pi, 50)
phi = np.linspace(0, np.pi, 50)
x = radius_km * np.outer(np.cos(theta), np.sin(phi))
y = radius_km * np.outer(np.sin(theta), np.sin(phi))
z = radius_km * np.outer(np.ones(50), np.cos(phi))
fig.add_trace(go.Surface(x=x, y=y, z=z, opacity=0.4, showscale=False, name="Earth"))
fig.update_layout(title=f"3D TLE Orbit — {name}", scene=dict(aspectmode="data"))
fig.show()
