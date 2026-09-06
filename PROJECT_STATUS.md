# SpacePlanner Project Status

## Completed phases

### Phase 1 — Orbital simulation engine
- TLE parsing and SGP4 propagation
- Common time-aligned simulation epoch
- 3D Cartesian position tracking

### Phase 2 — Real-data integration
- Current CelesTrak GP/TLE fetching
- TLS certificate verification enabled
- Retry handling and bundled offline fallback
- Configurable TLE group and satellite count

### Phase 3 — Visualization
- Interactive Dash dashboard
- 2D geographic ground tracks
- 3D Earth/orbit visualization
- Simulation-duration and screening-threshold controls

### Phase 4 — Collision / conjunction logic
- Pairwise future-window screening
- Interpolated closest approach between time samples
- Miss distance, time-to-closest-approach, relative speed, risk score

### Phase 5 — Event and status layer
- Safe/alert system state
- Prioritized alert cards
- Dedicated alert log page
- Health endpoint for cloud deployment

### Phase 6 — Intelligent decision layer
- Transparent expert-system states: WATCH, MONITOR, PREPARE, ESCALATE
- Priority levels P1–P4
- Human-readable rationale and response guidance

This is an explainable rule/decision system, not a trained machine-learning model.

### Phase 7 — Avoidance optimization screening
- First-order Δv screening estimate
- Target miss-distance logic
- Maneuver urgency guidance

The displayed Δv is intentionally labelled as a screening estimate. It is not an executable spacecraft command.

### Phase 8 — Scalability and deployment
- Configurable tracking count (2–15 objects)
- Orbit caching by satellite and simulation duration
- Minimal dependency stack
- Dockerfile for Railway
- `/health` endpoint
- GitHub Actions CI configuration

## Future research-grade upgrades

- Covariance-aware probability of collision (Pc)
- Conjunction Data Message (CDM) ingestion
- High-fidelity perturbation/force models
- Candidate maneuver re-propagation and constraint checking
- Persistent event history / database
- Validated ML model trained on real conjunction outcomes
- Genetic/RL maneuver optimization only after a defensible training/simulation environment exists
- Space-weather inputs and drag sensitivity
- Authentication and multi-user mission workspaces

## Deployment target

Railway is the recommended deployment platform for the current Dash/Gunicorn/Docker architecture.
