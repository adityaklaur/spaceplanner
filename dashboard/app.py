import os
import shutil
import numpy as np
from dash import Dash, dcc, html, Input, Output
import plotly.graph_objects as go
from astropy.time import Time

from orbit.propagator import propagate_orbit
from orbit.groundtrack import eci_to_latlon
from orbit.tle_loader import load_tle
from orbit.tle_fetcher import fetch_multiple_tles, get_tle_source
from orbit.predict_collision import predict_collisions
from ai.mission_planner import build_mission_plan

# ── Clear stale Dash callback cache to prevent KeyError on restart ──
_here = os.path.dirname(os.path.abspath(__file__))
for _cache in ['.dash_cache']:
    _p = os.path.join(_here, _cache)
    if os.path.isdir(_p):
        shutil.rmtree(_p, ignore_errors=True)

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    update_title=None,
    title="SpacePlanner Mission Control",
)

# Current TLE snapshot fetched at application startup
SATELLITE_LIMIT = max(2, min(15, int(os.getenv("SATELLITE_LIMIT", "5"))))
satellites = fetch_multiple_tles(limit=SATELLITE_LIMIT)
tle_source = get_tle_source()
# Use one common epoch for every object so pairwise distances are time-aligned.
# Current online TLEs are propagated from app startup; bundled demo TLEs use
# the first sample TLE epoch to avoid pretending old fallback elements are current.
if tle_source.startswith("Offline"):
    SIMULATION_EPOCH = load_tle(satellites[0][1], satellites[0][2]).epoch
else:
    SIMULATION_EPOCH = Time.now().utc

COLLISION_THRESHOLD_KM = max(10.0, min(1000.0, float(os.getenv("COLLISION_THRESHOLD_KM", "50"))))
PROPAGATION_STEPS = max(12, min(240, int(os.getenv("PROPAGATION_STEPS", "60"))))
latest_alerts = []

# Orbit cache is keyed by satellite + simulation duration.
orbit_cache = {}

# ─────────────────────────────────────────
# GLOBAL CSS injected via index_string
# ─────────────────────────────────────────
app.index_string = '''
<!DOCTYPE html>
<html>
<head>
    {%metas%}
    <title>SpacePlanner Mission Control</title>
    {%favicon%}
    {%css%}
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap" rel="stylesheet">
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        :root {
            --bg:        #080c14;
            --surface:   #0d1220;
            --surface2:  #111828;
            --border:    rgba(255,255,255,0.07);
            --accent:    #4f8ef7;
            --accent2:   #7c5cfc;
            --danger:    #f75b5b;
            --safe:      #43e89b;
            --text:      #e8edf8;
            --muted:     #6b7a99;
            --radius:    14px;
        }

        html, body { height: 100%; background: var(--bg); }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-track { background: var(--bg); }
        ::-webkit-scrollbar-thumb { background: var(--border); border-radius: 9px; }

        /* ── Layout shell ── */
        .shell {
            display: flex;
            min-height: 100vh;
            font-family: 'DM Sans', sans-serif;
            color: var(--text);
        }

        /* ── Sidebar ── */
        .sidebar {
            width: 220px;
            flex-shrink: 0;
            background: var(--surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 24px 16px;
            gap: 6px;
        }

        .sidebar-logo {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 0 8px 28px;
        }

        .sidebar-logo-icon {
            width: 34px; height: 34px;
            background: linear-gradient(135deg, var(--accent), var(--accent2));
            border-radius: 10px;
            display: flex; align-items: center; justify-content: center;
            font-size: 16px;
        }

        .sidebar-logo-text {
            font-family: 'Space Mono', monospace;
            font-size: 13px;
            font-weight: 700;
            letter-spacing: -0.3px;
            line-height: 1.2;
            color: var(--text);
        }

        .sidebar-logo-text span {
            display: block;
            font-size: 10px;
            font-weight: 400;
            color: var(--muted);
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 10px;
            font-size: 14px;
            font-weight: 500;
            color: var(--muted);
            cursor: pointer;
            transition: all 0.15s;
            border: none; background: none;
            text-decoration: none;
        }

        .nav-item:hover { background: var(--surface2); color: var(--text); }
        .nav-item.active { background: rgba(79,142,247,0.12); color: var(--accent); }

        .nav-icon { font-size: 16px; width: 20px; text-align: center; }

        .sidebar-section-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: var(--muted);
            padding: 18px 12px 6px;
        }

        /* Status badge in sidebar */
        .status-badge {
            margin-top: auto;
            padding: 12px;
            border-radius: var(--radius);
            background: var(--surface2);
            border: 1px solid var(--border);
        }

        .status-badge-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 6px;
        }

        .status-badge-value {
            font-family: 'Space Mono', monospace;
            font-size: 12px;
            font-weight: 700;
        }

        .status-badge-value.ok  { color: var(--safe); }
        .status-badge-value.bad { color: var(--danger); }

        /* ── Main ── */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        /* ── Topbar ── */
        .topbar {
            height: 58px;
            flex-shrink: 0;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 28px;
            border-bottom: 1px solid var(--border);
            background: var(--surface);
        }

        .topbar-title {
            font-size: 15px;
            font-weight: 600;
            color: var(--text);
        }

        .topbar-right {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .live-pill {
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(67,232,155,0.1);
            border: 1px solid rgba(67,232,155,0.25);
            color: var(--safe);
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.5px;
            padding: 4px 10px;
            border-radius: 20px;
        }

        .live-dot {
            width: 6px; height: 6px;
            background: var(--safe);
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }

        .topbar-chip {
            font-size: 12px;
            color: var(--muted);
            background: var(--surface2);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 4px 10px;
        }

        /* ── Content ── */
        .content {
            flex: 1;
            overflow-y: auto;
            padding: 24px 28px;
            display: grid;
            grid-template-columns: 260px 1fr;
            grid-template-rows: auto 1fr;
            gap: 18px;
            align-content: start;
        }

        /* ── Alert Banner ── */
        .alert-banner {
            grid-column: 1 / -1;
            border-radius: var(--radius);
            padding: 14px 18px;
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 13px;
            font-weight: 500;
        }

        .alert-banner.danger {
            background: rgba(247,91,91,0.1);
            border: 1px solid rgba(247,91,91,0.3);
            color: #ffafaf;
        }

        .alert-banner.safe {
            background: rgba(67,232,155,0.08);
            border: 1px solid rgba(67,232,155,0.2);
            color: #9effd5;
        }

        .alert-icon { font-size: 18px; }

        .alert-text-title { font-weight: 700; font-size: 14px; }
        .alert-text-sub   { font-size: 12px; opacity: 0.7; margin-top: 2px; }

        /* ── Left Panel ── */
        .left-panel {
            display: flex;
            flex-direction: column;
            gap: 16px;
        }

        /* Slider card */
        .card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            padding: 18px;
        }

        .card-label {
            font-size: 10px;
            font-weight: 600;
            letter-spacing: 1.2px;
            text-transform: uppercase;
            color: var(--muted);
            margin-bottom: 14px;
        }

        /* Dash slider overrides */
        .rc-slider-track { background: var(--accent2) !important; }
        .rc-slider-handle {
            border-color: var(--accent2) !important;
            background: var(--accent2) !important;
            box-shadow: 0 0 0 5px rgba(124,92,252,0.25) !important;
            width: 20px !important;
            height: 20px !important;
            margin-top: -8px !important;
        }
        .rc-slider-rail {
            background: rgba(255,255,255,0.12) !important;
            height: 4px !important;
        }
        .rc-slider-track { height: 4px !important; }
        .rc-slider-mark-text,
        .rc-slider-mark-text-active,
        .rc-slider .rc-slider-mark .rc-slider-mark-text,
        .rc-slider .rc-slider-mark .rc-slider-mark-text-active,
        ._dash-undo-redo ~ div .rc-slider-mark-text,
        div .rc-slider-mark span,
        .dash-graph .rc-slider-mark-text {
            color: #ffffff !important;
            font-size: 12px !important;
            font-family: 'Space Mono', monospace !important;
            font-weight: 700 !important;
            opacity: 1 !important;
            visibility: visible !important;
        }

        /* Alerts scrollable card */
        .alerts-card {
            flex: 1;
            overflow-y: auto;
            min-height: 0;
        }

        .alert-item {
            background: var(--surface2);
            border: 1px solid rgba(247,91,91,0.2);
            border-radius: 10px;
            padding: 12px 14px;
            margin-bottom: 10px;
        }

        .alert-item-header {
            display: flex;
            align-items: center;
            gap: 6px;
            font-family: 'Space Mono', monospace;
            font-size: 12px;
            font-weight: 700;
            color: var(--danger);
            margin-bottom: 8px;
        }

        .alert-item-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            color: var(--muted);
            margin-bottom: 3px;
        }

        .alert-item-row span:last-child {
            color: var(--text);
            font-weight: 500;
        }

        .dv-chip {
            display: inline-block;
            background: rgba(124,92,252,0.15);
            border: 1px solid rgba(124,92,252,0.3);
            color: #b89fff;
            font-size: 10px;
            font-family: 'Space Mono', monospace;
            border-radius: 6px;
            padding: 3px 8px;
            margin-top: 6px;
        }

        .maneuver-text {
            font-size: 11px;
            color: var(--accent);
            margin-top: 4px;
        }

        /* ── Right Panel ── */
        .right-panel {
            display: flex;
            flex-direction: column;
            gap: 18px;
        }

        .graph-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius);
            overflow: hidden;
        }

        .graph-card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 14px 18px;
            border-bottom: 1px solid var(--border);
        }

        .graph-card-title {
            font-size: 13px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .graph-card-badge {
            font-size: 10px;
            font-weight: 600;
            background: rgba(79,142,247,0.12);
            color: var(--accent);
            border-radius: 6px;
            padding: 2px 7px;
        }
    </style>
</head>
<body>
    {%app_entry%}
    <footer>
        {%config%}
        {%scripts%}
        {%renderer%}
    </footer>
</body>
</html>
'''

# ─────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────
app.layout = html.Div(className='shell', children=[

    # ── Sidebar ──
    html.Div(className='sidebar', children=[
        html.Div(className='sidebar-logo', children=[
            html.Div('🛰', className='sidebar-logo-icon'),
            html.Div(children=[
                'SatTrack',
                html.Span('Mission Control')
            ], className='sidebar-logo-text')
        ]),

        html.Div('Navigation', className='sidebar-section-label'),
        html.Div([html.Span('⊞', className='nav-icon'), 'Dashboard'],
                 className='nav-item active', id='nav-dashboard', n_clicks=0),
        html.Div([html.Span('◉', className='nav-icon'), 'Satellites'],
                 className='nav-item', id='nav-satellites', n_clicks=0),
        html.Div([html.Span('⚠', className='nav-icon'), 'Alerts'],
                 className='nav-item', id='nav-alerts', n_clicks=0),
        html.Div([html.Span('⚙', className='nav-icon'), 'Settings'],
                 className='nav-item', id='nav-settings', n_clicks=0),

        # System status
        html.Div(id='sidebar-status', className='status-badge'),
    ]),

    # ── Main ──
    html.Div(className='main', children=[

        # Topbar
        html.Div(className='topbar', children=[
            html.Div(id='topbar-title', className='topbar-title', children='Dashboard'),
            html.Div(className='topbar-right', children=[
                html.Div(className='live-pill', children=[
                    html.Div(className='live-dot'),
                    'SIMULATION'
                ]),
                html.Div(f'TLE: {tle_source}', className='topbar-chip'),
                html.Div(id='sat-count-chip', className='topbar-chip'),
            ])
        ]),

        # Page content area (swapped by nav callbacks)
        html.Div(id='page-content'),
    ]),

    dcc.Interval(id='interval', interval=4000, n_intervals=0),
    dcc.Store(id='current-page', data='dashboard'),
])

# ─────────────────────────────────────────
# NAV + PAGE CALLBACKS
# ─────────────────────────────────────────

def _dashboard_content():
    return html.Div(className='content', children=[
        html.Div(id='alert-banner', className='alert-banner safe',
                 style={'gridColumn': '1 / -1'}),
        html.Div(className='left-panel', children=[
            html.Div(className='card', children=[
                html.Div('Simulation Duration', className='card-label'),
                dcc.Slider(1, 12, 1, value=4, id='duration',
                           marks={
                               1:  {'label': '1h',  'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               4:  {'label': '4h',  'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               8:  {'label': '8h',  'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               12: {'label': '12h', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                           },
                           tooltip={"placement": "bottom", "always_visible": False}),
            ]),
            html.Div(className='card', children=[
                html.Div('Screening Threshold', className='card-label'),
                dcc.Slider(10, 1000, 10, value=COLLISION_THRESHOLD_KM, id='threshold',
                           marks={
                               10: {'label': '10', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               50: {'label': '50', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               250: {'label': '250', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               500: {'label': '500', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                               1000: {'label': '1000 km', 'style': {'color': '#ffffff', 'fontWeight': '700'}},
                           },
                           tooltip={"placement": "bottom", "always_visible": False}),
                html.Div('Educational closest-approach screening radius', style={
                    'fontSize': '10px', 'color': 'var(--muted)', 'marginTop': '12px'
                }),
            ]),
            html.Div(id='alerts-panel', className='card alerts-card'),
        ]),
        html.Div(className='right-panel', children=[
            html.Div(className='graph-card', children=[
                html.Div(className='graph-card-header', children=[
                    html.Div(className='graph-card-title', children=[
                        '\U0001f30d Ground Track',
                        html.Span('TLE PROPAGATION', className='graph-card-badge')
                    ]),
                ]),
                dcc.Graph(id='map', config={'displayModeBar': False}, style={'height': '360px'}),
            ]),
            html.Div(className='graph-card', children=[
                html.Div(className='graph-card-header', children=[
                    html.Div(className='graph-card-title', children=[
                        '\U0001f6f0\ufe0f Orbital Paths',
                        html.Span('3D', className='graph-card-badge')
                    ]),
                ]),
                dcc.Graph(id='orbit3d', config={'displayModeBar': False}, style={'height': '340px'}),
            ]),
        ]),
    ])


def _satellites_content():
    colors = ['#4f8ef7', '#f75b9e', '#43e89b', '#f7a843', '#b89fff']
    rows = []
    for i, (name, tle1, tle2) in enumerate(satellites):
        color = colors[i % len(colors)]
        rows.append(html.Div(style={
            'display': 'flex', 'alignItems': 'center', 'gap': '14px',
            'padding': '14px 16px', 'borderRadius': '10px',
            'background': 'var(--surface2)', 'border': '1px solid var(--border)',
            'marginBottom': '10px',
        }, children=[
            html.Div(style={
                'width': '10px', 'height': '10px', 'borderRadius': '50%',
                'background': color, 'flexShrink': '0', 'boxShadow': f'0 0 6px {color}'
            }),
            html.Div(children=[
                html.Div(name, style={
                    'fontFamily': "'Space Mono', monospace",
                    'fontSize': '13px', 'fontWeight': '700', 'color': 'var(--text)'
                }),
                html.Div('Active \u00b7 TLE loaded', style={
                    'fontSize': '11px', 'color': 'var(--muted)', 'marginTop': '3px'
                }),
            ]),
            html.Div('\u25cf TRACKING', style={
                'marginLeft': 'auto', 'fontSize': '10px', 'fontWeight': '700',
                'color': 'var(--safe)', 'letterSpacing': '0.5px'
            }),
        ]))
    return html.Div(style={'padding': '24px 28px'}, children=[
        html.Div('Active Satellites', style={
            'fontSize': '10px', 'fontWeight': '600', 'letterSpacing': '1.2px',
            'textTransform': 'uppercase', 'color': 'var(--muted)', 'marginBottom': '16px'
        }),
        *rows
    ])


def _alerts_content():
    if latest_alerts:
        rows = []
        for alert in latest_alerts[:20]:
            rows.append(html.Div(style={
                'padding': '14px 16px', 'borderRadius': '10px',
                'background': 'var(--surface2)', 'border': '1px solid rgba(247,91,91,0.2)',
                'marginBottom': '10px',
            }, children=[
                html.Div(f"{alert['sat1']}  ↔  {alert['sat2']}", style={
                    'fontFamily': "'Space Mono', monospace", 'fontSize': '12px',
                    'fontWeight': '700', 'color': 'var(--danger)'
                }),
                html.Div(
                    f"{alert['risk_level']} · score {alert['risk_score']:.0f}/100 · "
                    f"miss {alert['miss_distance_km']:.2f} km · "
                    f"TCA {alert['time_to_closest_s']/60:.1f} min",
                    style={'fontSize': '11px', 'color': 'var(--muted)', 'marginTop': '5px'}
                ),
            ]))
        body = rows
    else:
        body = [html.Div(
            '✅  No conjunctions are currently inside the screening threshold.',
            style={'fontSize': '13px', 'color': 'var(--safe)', 'padding': '16px',
                   'background': 'var(--surface2)', 'borderRadius': '10px',
                   'border': '1px solid var(--border)'}
        )]

    return html.Div(style={'padding': '24px 28px'}, children=[
        html.Div('Conjunction Screening Log', style={
            'fontSize': '10px', 'fontWeight': '600', 'letterSpacing': '1.2px',
            'textTransform': 'uppercase', 'color': 'var(--muted)', 'marginBottom': '16px'
        }),
        *body,
        html.Div(
            'Screening output is educational decision support, not an operational collision probability.',
            style={'fontSize': '11px', 'color': 'var(--muted)', 'marginTop': '10px'}
        )
    ])


def _settings_content():
    def row(label, value, note=''):
        return html.Div(style={
            'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center',
            'padding': '14px 16px', 'borderRadius': '10px',
            'background': 'var(--surface2)', 'border': '1px solid var(--border)',
            'marginBottom': '10px',
        }, children=[
            html.Div(children=[
                html.Div(label, style={'fontSize': '13px', 'color': 'var(--text)', 'fontWeight': '500'}),
                html.Div(note, style={'fontSize': '11px', 'color': 'var(--muted)', 'marginTop': '3px'}) if note else None,
            ]),
            html.Div(value, style={
                'fontFamily': "'Space Mono', monospace",
                'fontSize': '12px', 'color': 'var(--accent)', 'fontWeight': '700'
            }),
        ])
    sat_names = [s[0] for s in satellites]
    return html.Div(style={'padding': '24px 28px'}, children=[
        html.Div('System Configuration', style={
            'fontSize': '10px', 'fontWeight': '600', 'letterSpacing': '1.2px',
            'textTransform': 'uppercase', 'color': 'var(--muted)', 'marginBottom': '16px'
        }),
        row('Animation Interval', '4 seconds', 'Moves through the propagated simulation window'),
        row('Orbit Propagation Steps', f'{PROPAGATION_STEPS} steps', 'Per simulation window'),
        row('TLE Data Source', tle_source, 'Offline fallback enabled'),
        row('Simulation Epoch', SIMULATION_EPOCH.utc.iso, 'Common time origin for all propagated objects'),
        row('Satellites Loaded', str(len(sat_names)), ', '.join(sat_names[:3]) + ('...' if len(sat_names) > 3 else '')),
        row('Autonomous Decision Layer', 'Enabled', 'Prioritises monitor / prepare / escalate states'),
        row('Maneuver Screening', 'Enabled', 'Linearized Δv estimates for decision support'),
        row('Conjunction Threshold', f'{COLLISION_THRESHOLD_KM:.0f} km', 'Closest-approach screening threshold'),
    ])


@app.callback(
    Output('page-content', 'children'),
    Output('topbar-title', 'children'),
    Output('nav-dashboard', 'className'),
    Output('nav-satellites', 'className'),
    Output('nav-alerts', 'className'),
    Output('nav-settings', 'className'),
    Input('nav-dashboard', 'n_clicks'),
    Input('nav-satellites', 'n_clicks'),
    Input('nav-alerts', 'n_clicks'),
    Input('nav-settings', 'n_clicks'),
)
def switch_page(n_dash, n_sat, n_alert, n_set):
    from dash import ctx
    triggered = ctx.triggered_id or 'nav-dashboard'
    pages = {
        'nav-dashboard':  (_dashboard_content(), 'Dashboard'),
        'nav-satellites': (_satellites_content(), 'Satellites'),
        'nav-alerts':     (_alerts_content(),     'Alerts'),
        'nav-settings':   (_settings_content(),   'Settings'),
    }
    content, title = pages[triggered]
    def cls(nid): return 'nav-item active' if nid == triggered else 'nav-item'
    return (content, title,
            cls('nav-dashboard'), cls('nav-satellites'),
            cls('nav-alerts'),    cls('nav-settings'))


# ─────────────────────────────────────────
# MAIN DATA CALLBACK
# ─────────────────────────────────────────
@app.callback(
    Output('map', 'figure'),
    Output('orbit3d', 'figure'),
    Output('alerts-panel', 'children'),
    Output('alert-banner', 'children'),
    Output('alert-banner', 'className'),
    Output('sidebar-status', 'children'),
    Output('sat-count-chip', 'children'),
    Input('duration', 'value'),
    Input('threshold', 'value'),
    Input('interval', 'n_intervals')
)
def update(duration, threshold, n_intervals):

    fig_map = go.Figure()
    fig_3d  = go.Figure()

    sat_positions      = {}
    sat_last_positions = {}
    sat_latlon         = {}

    # ── Earth — textured sphere with lat/lon grid + continent outlines ──
    R = 6371

    # 1. Ocean base sphere (high res for smooth look)
    N = 80
    theta_e = np.linspace(0, 2 * np.pi, N)
    phi_e   = np.linspace(0, np.pi, N)
    xe = R * np.outer(np.cos(theta_e), np.sin(phi_e))
    ye = R * np.outer(np.sin(theta_e), np.sin(phi_e))
    ze = R * np.outer(np.ones(N),      np.cos(phi_e))

    fig_3d.add_trace(go.Surface(
        x=xe, y=ye, z=ze,
        colorscale=[
            [0.0,  '#04111f'],
            [0.3,  '#061a30'],
            [0.6,  '#0a2a50'],
            [1.0,  '#0d3a6e'],
        ],
        opacity=1.0,
        showscale=False,
        lighting=dict(ambient=0.7, diffuse=0.5, specular=0.1),
        hoverinfo='skip',
        name='Earth'
    ))

    # helper: lat/lon → ECI xyz (always returns numpy arrays)
    def latlon_to_xyz(lat_deg, lon_deg, r=R):
        la = np.radians(np.atleast_1d(np.asarray(lat_deg, dtype=float)))
        lo = np.radians(np.atleast_1d(np.asarray(lon_deg, dtype=float)))
        return (r * np.cos(la) * np.cos(lo),
                r * np.cos(la) * np.sin(lo),
                r * np.sin(la))

    # 2. Latitude grid lines (every 30°)
    for lat in range(-60, 90, 30):
        lons_g = np.linspace(-180, 180, 120)
        gx, gy, gz = latlon_to_xyz(lat, lons_g)
        fig_3d.add_trace(go.Scatter3d(
            x=gx, y=gy, z=gz, mode='lines',
            line=dict(width=1, color='rgba(100,160,255,0.18)'),
            hoverinfo='skip', showlegend=False, name=''
        ))

    # 3. Longitude grid lines (every 30°)
    for lon in range(-180, 180, 30):
        lats_g = np.linspace(-90, 90, 90)
        gx, gy, gz = latlon_to_xyz(lats_g, lon)
        fig_3d.add_trace(go.Scatter3d(
            x=gx, y=gy, z=gz, mode='lines',
            line=dict(width=1, color='rgba(100,160,255,0.18)'),
            hoverinfo='skip', showlegend=False, name=''
        ))

    # 4. Equator highlight
    lons_eq = np.linspace(-180, 180, 200)
    ex, ey, ez = latlon_to_xyz(0, lons_eq)
    fig_3d.add_trace(go.Scatter3d(
        x=ex, y=ey, z=ez, mode='lines',
        line=dict(width=2, color='rgba(100,200,255,0.35)'),
        hoverinfo='skip', showlegend=False, name=''
    ))

    # 5. Simplified continent outlines (key coastline segments as lat/lon polylines)
    #    Each entry: list of (lat, lon) pairs — None = pen-up
    continents = [
        # North America west coast
        [(72,-141),(65,-168),(60,-147),(55,-133),(49,-124),(40,-124),(32,-117),(22,-106),(15,-92),(8,-77)],
        # North America east coast
        [(8,-77),(10,-83),(15,-87),(20,-87),(22,-80),(25,-80),(30,-81),(35,-76),(40,-74),(45,-67),(47,-53),(50,-56),(52,-56),(55,-60),(60,-65),(65,-61),(70,-68),(72,-73),(72,-96),(72,-141)],
        # South America
        [(12,-72),(10,-62),(8,-60),(5,-52),(0,-50),(-5,-35),(-10,-37),(-15,-39),(-20,-41),(-23,-44),(-30,-50),(-33,-53),(-35,-58),(-40,-62),(-45,-66),(-50,-69),(-55,-67),(-55,-64),(-53,-58),(-50,-65),(-45,-75),(-40,-73),(-30,-71),(-20,-70),(-15,-76),(-5,-81),(0,-80),(5,-77),(10,-72),(12,-72)],
        # Europe west
        [(36,-9),(38,-9),(40,-8),(44,-2),(47,2),(51,2),(53,5),(55,8),(58,5),(58,8),(62,5),(65,14),(70,20),(70,28),(65,26),(60,25),(55,21),(55,18),(50,14),(48,17),(45,14),(42,18),(40,18),(36,14),(36,10),(36,-9)],
        # Africa
        [(36,10),(37,10),(37,12),(32,32),(28,33),(15,42),(12,44),(10,42),(5,40),(0,42),(-5,40),(-10,40),(-15,35),(-20,35),(-25,33),(-30,30),(-35,28),(-35,18),(-30,18),(-25,15),(-20,12),(-15,12),(-10,14),(-5,10),(0,8),(5,2),(5,-5),(10,-15),(15,-17),(20,-17),(25,-15),(30,-10),(30,-5),(32,10),(36,10)],
        # Asia outline (simplified)
        [(70,28),(70,60),(70,100),(70,140),(65,143),(60,143),(55,135),(50,140),(45,135),(40,122),(35,120),(30,120),(25,119),(20,110),(15,108),(10,104),(5,100),(5,103),(1,104),(5,100),(10,99),(15,100),(20,93),(20,88),(25,89),(25,92),(28,97),(25,95),(20,93),(15,80),(10,79),(8,77),(15,75),(20,73),(22,69),(25,63),(25,57),(28,50),(25,57),(20,60),(15,52),(12,50),(8,45),(10,42),(15,42),(28,33),(32,32),(37,37),(40,36),(42,35),(42,28),(45,30),(50,30),(55,38),(60,28),(65,28),(70,28)],
        # Australia
        [(-15,130),(-12,136),(-14,136),(-12,142),(-15,145),(-20,148),(-25,153),(-30,153),(-35,150),(-38,147),(-38,140),(-35,137),(-32,133),(-32,115),(-28,114),(-22,113),(-20,118),(-15,124),(-15,130)],
        # Greenland
        [(83,-45),(80,-20),(75,-18),(70,-22),(65,-38),(63,-42),(63,-52),(68,-55),(72,-55),(75,-60),(78,-68),(80,-68),(83,-45)],
    ]

    for segment in continents:
        lats_c = [p[0] for p in segment]
        lons_c = [p[1] for p in segment]
        cx, cy, cz = latlon_to_xyz(np.array(lats_c), np.array(lons_c), r=R+8)
        fig_3d.add_trace(go.Scatter3d(
            x=cx, y=cy, z=cz, mode='lines',
            line=dict(width=1.5, color='rgba(160,210,255,0.55)'),
            hoverinfo='skip', showlegend=False, name=''
        ))

    # 6. North/South pole caps (ice-white dots)
    for pole_lat in [90, -90]:
        px, py, pz = latlon_to_xyz(pole_lat, 0)
        fig_3d.add_trace(go.Scatter3d(
            x=px, y=py, z=pz, mode='markers',
            marker=dict(size=4, color='rgba(220,240,255,0.6)'),
            hoverinfo='skip', showlegend=False, name=''
        ))

    colors = ['#4f8ef7', '#f75b9e', '#43e89b', '#f7a843', '#b89fff']
    active_count = 0

    # ── Satellite loop ──
    for i, (name, tle1, tle2) in enumerate(satellites):
        try:
            cache_key = (name, float(duration), PROPAGATION_STEPS)
            if cache_key not in orbit_cache:
                orbit = load_tle(tle1, tle2)
                times, positions = propagate_orbit(
                    orbit, duration_hours=duration, steps=PROPAGATION_STEPS,
                    start_time=SIMULATION_EPOCH,
                )
                epoch = SIMULATION_EPOCH
                orbit_cache[cache_key] = (times, positions, epoch)
            else:
                times, positions, epoch = orbit_cache[cache_key]

            lats, lons = eci_to_latlon(positions, times, epoch)
            idx = n_intervals % len(positions)

            sat_positions[name]      = positions
            sat_last_positions[name] = positions[idx]
            sat_latlon[name]         = (lats[idx], lons[idx])

            color = colors[i % len(colors)]
            active_count += 1

            # MAP — orbit trail
            fig_map.add_trace(go.Scattergeo(
                lat=lats, lon=lons,
                mode='lines',
                line=dict(width=2, color=color),
                name=name,
                opacity=0.6
            ))
            # MAP — simulated position within the propagation window
            fig_map.add_trace(go.Scattergeo(
                lat=[lats[idx]], lon=[lons[idx]],
                mode='markers+text',
                text=[name],
                textfont=dict(size=10, color=color),
                textposition='top center',
                marker=dict(
                    size=10, color=color,
                    line=dict(width=2, color='white')
                ),
                name=f"{name} (Sim)"
            ))

            # 3D orbit
            fig_3d.add_trace(go.Scatter3d(
                x=positions[:, 0], y=positions[:, 1], z=positions[:, 2],
                mode='lines',
                line=dict(width=3, color=color),
                name=name,
                opacity=0.7
            ))
            fig_3d.add_trace(go.Scatter3d(
                x=[positions[idx, 0]],
                y=[positions[idx, 1]],
                z=[positions[idx, 2]],
                mode='markers',
                marker=dict(
                    size=7, color=color,
                    line=dict(width=1, color='white')
                ),
                name=f"{name} (Sim)"
            ))

        except Exception as e:
            print(f"❌ Skipping {name}: {e}")

    # ── Conjunction screening ──
    global latest_alerts
    time_step_seconds = (float(duration) * 3600.0) / max(PROPAGATION_STEPS - 1, 1)
    alerts = predict_collisions(
        sat_positions,
        threshold_km=float(threshold),
        time_step_seconds=time_step_seconds,
    )
    mission_plan = build_mission_plan(
        alerts,
        target_miss_distance_km=max(75.0, float(threshold) * 1.5),
    )
    latest_alerts = mission_plan

    # ── Build alerts panel ──
    alerts_panel_children = []
    alert_banner_children  = []
    alert_banner_class     = 'alert-banner safe'
    sidebar_status         = []

    if alerts:
        alert_banner_class = 'alert-banner danger'
        alert_banner_children = [
            html.Span('⚠️', className='alert-icon'),
            html.Div([
                html.Div('Conjunction Screening Alert', className='alert-text-title'),
                html.Div('Review closest-approach and maneuver screening estimates', className='alert-text-sub'),
            ])
        ]

        alerts_panel_children.append(
            html.Div('⚠ Conjunction Alerts', className='card-label',
                     style={'color': '#f75b5b'})
        )

        for alert in mission_plan:
            sat1 = alert['sat1']
            sat2 = alert['sat2']
            dist = alert['miss_distance_km']
            time_min = alert['time_to_closest_s'] / 60.0
            rule_action = alert['recommendation']
            dv = alert['estimated_delta_v_m_s']
            opt_action = alert['maneuver_guidance']

            alerts_panel_children.append(html.Div(className='alert-item', children=[
                html.Div(className='alert-item-header', children=[
                    '⚡ ', f'{sat1}  ↔  {sat2}'
                ]),
                html.Div(className='alert-item-row', children=[
                    html.Span('Risk'),
                    html.Span(f"{alert['risk_level']} · {alert['risk_score']:.0f}/100")
                ]),
                html.Div(className='alert-item-row', children=[
                    html.Span('Decision'),
                    html.Span(f"{alert['priority']} · {alert['decision']}")
                ]),
                html.Div(className='alert-item-row', children=[
                    html.Span('Closest approach'),
                    html.Span(f'{dist:.2f} km')
                ]),
                html.Div(className='alert-item-row', children=[
                    html.Span('Time to closest'),
                    html.Span(f'~{time_min:.1f} min')
                ]),
                html.Div(className='alert-item-row', children=[
                    html.Span('Relative speed'),
                    html.Span(f"{alert['relative_speed_km_s']:.2f} km/s")
                ]),
                html.Div(html.B(rule_action),
                         style={'fontSize': '11px', 'color': '#f7a843', 'marginTop': '6px'}),
                html.Div(f'Estimated Δv  {dv:.2f} m/s', className='dv-chip'),
                html.Div(opt_action, className='maneuver-text'),
            ]))

        sidebar_status = [
            html.Div('System Status', className='status-badge-label'),
            html.Div(f'⚠ {len(alerts)} Conjunction Alert{"s" if len(alerts)>1 else ""}',
                     className='status-badge-value bad')
        ]

        fig_map.update_layout(title=None)

    else:
        alert_banner_children = [
            html.Span('✅', className='alert-icon'),
            html.Div([
                html.Div('All Clear — No Threshold Conjunction', className='alert-text-title'),
                html.Div('No pair falls inside the current screening threshold', className='alert-text-sub'),
            ])
        ]
        alerts_panel_children = [
            html.Div('Status', className='card-label'),
            html.Div(
                '✅  No threshold conjunction detected',
                style={'fontSize': '13px', 'color': '#43e89b', 'fontWeight': '500',
                       'padding': '8px 0'}
            ),
            html.Div(
                f'Tracking {active_count} satellites',
                style={'fontSize': '11px', 'color': '#6b7a99', 'marginTop': '4px'}
            )
        ]
        sidebar_status = [
            html.Div('System Status', className='status-badge-label'),
            html.Div('● All Clear', className='status-badge-value ok')
        ]
        fig_map.update_layout(title=None)

    # ── Map style ──
    fig_map.update_geos(
        showland=True,  landcolor='#141e30',
        showocean=True, oceancolor='#0b2545',
        showlakes=True, lakecolor='#0b2545',
        showcountries=True, countrycolor='rgba(255,255,255,0.08)',
        coastlinecolor='rgba(255,255,255,0.2)',
        bgcolor='#080c14',
        showframe=False,
    )
    fig_map.update_layout(
        paper_bgcolor='#080c14',
        plot_bgcolor='#080c14',
        margin=dict(l=0, r=0, t=0, b=0),
        legend=dict(
            bgcolor='rgba(13,18,32,0.85)',
            bordercolor='rgba(255,255,255,0.1)',
            borderwidth=1,
            font=dict(color='#e8edf8', size=10),
            x=1, xanchor='right', y=1
        ),
        font=dict(color='#e8edf8', family='DM Sans'),
    )

    # ── 3D style ──
    fig_3d.update_layout(
        paper_bgcolor='#080c14',
        margin=dict(l=0, r=0, t=0, b=0),
        scene=dict(
            bgcolor='#080c14',
            xaxis=dict(showbackground=False, color='#6b7a99', showticklabels=False,
                       title='', showgrid=False, zeroline=False),
            yaxis=dict(showbackground=False, color='#6b7a99', showticklabels=False,
                       title='', showgrid=False, zeroline=False),
            zaxis=dict(showbackground=False, color='#6b7a99', showticklabels=False,
                       title='', showgrid=False, zeroline=False),
        ),
        legend=dict(
            bgcolor='rgba(13,18,32,0.85)',
            bordercolor='rgba(255,255,255,0.1)',
            borderwidth=1,
            font=dict(color='#e8edf8', size=10),
            x=1, xanchor='right', y=1
        ),
        font=dict(color='#e8edf8', family='DM Sans'),
    )

    sat_count_chip = f'{active_count} Satellites'

    return (fig_map, fig_3d,
            alerts_panel_children,
            alert_banner_children,
            alert_banner_class,
            sidebar_status,
            sat_count_chip)


# ─────────────────────────────────────────
# RUN
# ─────────────────────────────────────────
server = app.server


@server.get('/health')
def health():
    return {
        'status': 'ok',
        'service': 'spaceplanner',
        'satellites_loaded': len(satellites),
        'tle_source': tle_source,
    }, 200


if __name__ == '__main__':
    port = int(os.getenv('PORT', '8050'))
    app.run(host='0.0.0.0', port=port, debug=False)