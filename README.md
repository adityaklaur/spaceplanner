# 🛰️ SpacePlanner — Multi-Satellite Conjunction Screening Dashboard

SpacePlanner is an educational mission-control dashboard that loads a current TLE snapshot, propagates several Earth-orbiting satellites with SGP4, visualizes their ground tracks and 3D trajectories, and screens satellite pairs for close approaches.

## What is implemented

- Current TLE snapshot from **CelesTrak GP data** with an offline fallback
- Direct **SGP4** propagation from a common simulation epoch (current UTC for online TLEs)
- TEME → ITRS → geodetic latitude/longitude conversion with **Astropy**
- Interactive **Dash + Plotly** mission-control interface
- 2D ground tracks and 3D orbital paths
- Pairwise closest-approach screening using interpolation between propagation samples
- Interactive screening-threshold control (10–1000 km)
- Risk prioritisation score using miss distance, lead time, and relative speed
- Transparent autonomous decision layer (WATCH / MONITOR / PREPARE / ESCALATE)
- First-order maneuver screening / estimated Δv guidance
- `/health` endpoint for deployment health checks
- Docker deployment configuration suitable for Railway

> **Important:** The conjunction and maneuver outputs are educational screening estimates. They are not operational collision probability (Pc) calculations and do not replace covariance-based conjunction assessment or flight-dynamics review.

## Architecture

```text
CelesTrak GP TLE snapshot
          │
          ▼
      TLE parser
          │
          ▼
   SGP4 propagation
          │
    ┌─────┴─────┐
    ▼           ▼
TEME → ITRS   Pairwise trajectory screening
    │           │
    ▼           ▼
Ground track  Closest approach / risk score
    │           │
    └─────┬─────┘
          ▼
      Dash / Plotly
          │
          ▼
  Mission-control UI
```

## Project structure

```text
spaceplanner/
├── ai/
│   └── mission_planner.py       # autonomous decision/prioritisation layer
├── dashboard/
│   └── app.py                  # Dash application + /health endpoint
├── orbit/
│   ├── tle_fetcher.py          # CelesTrak + offline fallback
│   ├── tle_loader.py           # TLE → SGP4 wrapper
│   ├── propagator.py           # SGP4 propagation
│   ├── groundtrack.py          # TEME → ITRS → lat/lon
│   ├── predict_collision.py    # closest-approach screening
│   ├── avoidance.py            # response guidance
│   ├── optimizer.py            # linearized maneuver estimate
│   └── sample_tles.txt         # offline demo TLEs
├── tests/
│   ├── test_collision.py
│   └── test_tle.py
├── Dockerfile
├── requirements.txt
└── main.py
```

## Run locally

Python 3.12 is recommended.

```bash
python3.12 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Open `http://127.0.0.1:8050`.

### Production-style local run

```bash
gunicorn dashboard.app:server --bind 0.0.0.0:8050 --workers 1 --threads 4 --timeout 120
```

## Tests

```bash
python -m unittest discover -s tests -v
```

## Configuration

Optional environment variables:

| Variable | Default | Purpose |
|---|---:|---|
| `PORT` | `8050` locally | Web server port; Railway injects its own value |
| `TLE_GROUP` | `weather` | CelesTrak GP group to fetch |
| `TLE_OFFLINE` | `0` | Set to `1` to skip network fetching and use bundled sample TLEs |
| `COLLISION_THRESHOLD_KM` | `50` | Screening threshold in km |
| `PROPAGATION_STEPS` | `60` | Samples per simulation window |
| `SATELLITE_LIMIT` | `5` | Number of TLE objects to load (2–15) |

## Deploy to Railway

The repository includes a `Dockerfile`; Railway can build directly from GitHub. A GitHub Actions workflow also compiles the project and runs the unit/smoke tests on each push.

1. Push this completed version to the GitHub repository.
2. In Railway, choose **New Project → Deploy from GitHub repo**.
3. Select the `spaceplanner` repository.
4. Railway will detect the `Dockerfile` and build the service.
5. In **Settings → Healthcheck**, set the path to `/health`.
6. In **Networking**, click **Generate Domain**.
7. Open the generated public URL.

The Docker command listens on Railway's injected `$PORT` value.

## Scientific notes

- TLEs are intended to be propagated with SGP4; SpacePlanner therefore uses SGP4 directly rather than converting TLE state vectors into another two-body propagation model.
- SGP4 output is in the TEME frame. Ground-track conversion uses Astropy's TEME → ITRS transformation.
- Closest approach is estimated by linearly interpolating the relative position between adjacent sampled trajectory points instead of checking only the discrete sample positions.
- The autonomous decision layer is a transparent expert system; it is **not a trained ML model**.
- The displayed risk score is a **prioritisation score**, not a probability of collision.
- The displayed Δv is a **linearized screening estimate** intended to compare response urgency. A real maneuver plan requires high-fidelity propagation, spacecraft constraints, covariance data, and operator review.

## Future upgrades

For a research/production-grade extension, the next steps would be covariance-aware probability of collision, higher-fidelity force models, maneuver candidate re-propagation, conjunction data message ingestion, persistent alert history, authentication, and a validated ML model trained on real conjunction outcomes rather than synthetic labels.
