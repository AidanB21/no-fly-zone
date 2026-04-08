import time
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from parser import load_live_csv, load_sensor_data
from preprocess import preprocess_data, DEFAULT_BASELINE, SENSOR_COLUMNS
from model import predict_row, get_status_text
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LIVE_CSV = str(BASE_DIR / "data" / "sensor_data" / "sensor_log.csv")

st.set_page_config(
    page_title="No-Fly-Zone | Pest Detection",
    layout="wide",
)

if 'paused' not in st.session_state:
    st.session_state.paused = False

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Outfit:wght@300;500;700&display=swap');

    .stApp {
        background-color: #0a0e17;
        color: #c9d1d9;
    }

    .main-title {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        font-size: 2.2rem;
        color: #00ff88;
        letter-spacing: -0.5px;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .sub-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #4a5568;
        margin-top: 0;
        padding-top: 0;
    }

    .metric-card {
        background: linear-gradient(135deg, #111827 0%, #1a2332 100%);
        border: 1px solid #1e2d3d;
        border-radius: 12px;
        padding: 18px 20px;
        text-align: center;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 2rem;
        font-weight: 700;
        color: #00ff88;
        line-height: 1.1;
    }
    .metric-label {
        font-family: 'Outfit', sans-serif;
        font-size: 0.75rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-top: 6px;
    }

    .alert-detected {
        background: linear-gradient(135deg, #2d1117 0%, #3b1219 100%);
        border: 1px solid #f8514966;
        border-radius: 12px;
        padding: 16px 24px;
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        color: #ff6b6b;
        font-weight: 500;
    }
    .alert-clear {
        background: linear-gradient(135deg, #0d1f12 0%, #0f2b16 100%);
        border: 1px solid #00ff8833;
        border-radius: 12px;
        padding: 16px 24px;
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 1.1rem;
        color: #00ff88;
        font-weight: 500;
    }

    .event-tag {
        display: inline-block;
        background: #f851491a;
        border: 1px solid #f8514944;
        border-radius: 6px;
        padding: 4px 12px;
        margin: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.8rem;
        color: #ff6b6b;
    }

    section[data-testid="stSidebar"] {
        background-color: #0d1117;
        border-right: 1px solid #1e2d3d;
    }

    .section-header {
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        font-size: 0.85rem;
        color: #4a5568;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid #1e2d3d;
    }

    .sensor-card {
        background: linear-gradient(135deg, #111827 0%, #1a2332 100%);
        border: 1px solid #1e2d3d;
        border-radius: 12px;
        padding: 16px;
        text-align: center;
    }
    .sensor-name {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .sensor-name.mq3 { color: #00ff88; }
    .sensor-name.mq135 { color: #00b4d8; }
    .sensor-name.mq138 { color: #e0e0e0; }
    .sensor-name.mq131 { color: #ffd166; }
    .sensor-name.tgs2602 { color: #ef476f; }

    .sensor-desc {
        font-family: 'Outfit', sans-serif;
        font-size: 0.65rem;
        color: #4a556888;
        margin-bottom: 10px;
    }

    .stTextInput label, .stSelectbox label,
    .stSlider label, .stNumberInput label, .stCheckbox label {
        color: #c9d1d9 !important;
    }
    .stTextInput input, .stNumberInput input {
        color: #c9d1d9 !important;
        background-color: #0d1117 !important;
        border-color: #1e2d3d !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: #c9d1d9;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

sensor_info = {
    'MQ3': {'css': 'mq3', 'desc': 'Alcohol & Ethanol'},
    'MQ135': {'css': 'mq135', 'desc': 'Air Quality / CO2'},
    'MQ138': {'css': 'mq138', 'desc': 'Organic Gases'},
    'MQ131': {'css': 'mq131', 'desc': 'Ozone'},
    'TGS2602': {'css': 'tgs2602', 'desc': 'VOCs & Odor'},
}

st.markdown('<p class="main-title">NO-FLY-ZONE</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">gas sensor array · ml detection pipeline · live</p>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Detection Settings")
    rolling_window = st.slider("Smoothing window", 1, 20, 5)
    st.markdown("---")
    live_mode = st.toggle("Live mode", value=True)
    st.markdown("---")

# --- Calibration state ---
if "calibrated" not in st.session_state:
    st.session_state.calibrated = False
if "cal_baselines" not in st.session_state:
    st.session_state.cal_baselines = DEFAULT_BASELINE.copy()

st.markdown('<div class="section-header">Sensor Baseline Calibration</div>', unsafe_allow_html=True)

if st.session_state.calibrated:
    st.markdown('<span class="calibrated-badge">✓ CALIBRATED</span>', unsafe_allow_html=True)

active_baselines = st.session_state.cal_baselines if st.session_state.calibrated else DEFAULT_BASELINE

baseline = {}
b1, b2, b3, b4, b5 = st.columns(5)

for col, sensor in zip([b1, b2, b3, b4, b5], SENSOR_COLUMNS):
    with col:
        info = sensor_info[sensor]
        st.markdown(f"""
        <div class="sensor-card">
            <div class="sensor-name {info['css']}">{sensor}</div>
            <div class="sensor-desc">{info['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
        baseline[sensor] = st.number_input(
            "Baseline", value=active_baselines[sensor], step=10,
            key=f"b_{sensor}", label_visibility="collapsed"
        )

st.markdown("<br>", unsafe_allow_html=True)

# --- Load data and run ML pipeline ---
try:
    if live_mode:
        raw_df = load_live_csv(LIVE_CSV)
    else:
        raw_df = load_sensor_data("data/sample_sensorData.txt")
    processed_df = preprocess_data(raw_df, baseline=baseline, window=rolling_window)

    # run ML model on each row
    labels = []
    confidences = []
    for _, row in processed_df.iterrows():
        vals = [row[s] for s in SENSOR_COLUMNS]
        label, conf = predict_row(vals)
        labels.append(label)
        confidences.append(conf)

    processed_df["fly_detected"] = labels
    processed_df["confidence"] = confidences

    # build summary
    total_samples = len(processed_df)
    fly_samples = sum(labels)
    fly_percentage = round((fly_samples / total_samples) * 100, 2) if total_samples > 0 else 0

    # find contiguous detection regions
    regions = []
    in_event = False
    start = 0
    for i, lbl in enumerate(labels):
        if lbl == 1 and not in_event:
            start = i
            in_event = True
        elif lbl == 0 and in_event:
            regions.append((start, i - 1))
            in_event = False
    if in_event:
        regions.append((start, len(labels) - 1))

    summary = {
        'total_samples': total_samples,
        'fly_samples': fly_samples,
        'fly_percentage': fly_percentage,
        'detection_regions': regions,
        'num_events': len(regions),
        'avg_confidence': np.mean(confidences) if confidences else 0,
    }

except FileNotFoundError:
    st.info("Waiting for live data... Start comdata.py to begin streaming.")
    time.sleep(2)
    st.rerun()
except Exception as e:
    st.error(f"Error loading data: {e}")
    time.sleep(2)
    st.rerun()

df = processed_df

sensor_colors = {
    'MQ3': '#00ff88',
    'MQ135': '#00b4d8',
    'MQ138': '#e0e0e0',
    'MQ131': '#ffd166',
    'TGS2602': '#ef476f',
}

# --- Detection Results ---
st.markdown('<div class="section-header">Detection Results</div>', unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
for col, val, label in zip(
    [c1, c2, c3, c4],
    [summary['total_samples'], summary['fly_samples'], f"{summary['fly_percentage']}%", summary['num_events']],
    ["SAMPLES", "DETECTIONS", "FLY %", "EVENTS"]
):
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

if summary['num_events'] > 0:
    avg_conf = summary['avg_confidence']
    events_html = " ".join([f'<span class="event-tag">samples {r[0]}-{r[1]}</span>' for r in summary['detection_regions']])
    st.markdown(f'<div class="alert-detected">FLY ACTIVITY DETECTED ({avg_conf:.0%} avg confidence) &nbsp;·&nbsp; {events_html}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="alert-clear">ALL CLEAR — No fly activity detected</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Sensor Readings Chart ---
fig = make_subplots(rows=1, cols=1)

for sensor in SENSOR_COLUMNS:
    fig.add_trace(go.Scatter(
        y=df[f"{sensor}_rolling"].values,
        mode='lines',
        name=sensor,
        line=dict(color=sensor_colors[sensor], width=1.5),
        hovertemplate=f'{sensor}: %{{y:.0f}}<extra></extra>',
    ))

for region in summary['detection_regions']:
    fig.add_vrect(
        x0=region[0], x1=region[1],
        fillcolor="#ff6b6b", opacity=0.12,
        layer="below", line_width=0,
        annotation_text="FLY", annotation_position="top left",
        annotation=dict(font_size=10, font_color="#ff6b6b"),
    )

fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0a0e17",
    plot_bgcolor="#0d1117",
    height=420,
    margin=dict(l=20, r=20, t=40, b=20),
    title=dict(text="SENSOR READINGS (SMOOTHED)", font=dict(family="Outfit", size=14, color="#4a5568"), x=0),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        font=dict(family="JetBrains Mono", size=11, color="#c9d1d9"),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(title="Sample", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568")),
    yaxis=dict(title="ADC Value", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568")),
    hovermode="x unified",
)

st.plotly_chart(fig, use_container_width=True)

# --- ML Confidence Chart (replaces distance-from-baseline) ---
fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    y=df["confidence"].values,
    mode='lines',
    name='Confidence',
    line=dict(color='#00ff88', width=1.5),
    fill='tozeroy',
    fillcolor='rgba(0, 255, 136, 0.05)',
    hovertemplate='Confidence: %{y:.2f}<extra></extra>',
))

fig2.add_trace(go.Scatter(
    y=df["fly_detected"].values,
    mode='lines',
    name='Fly Detected',
    line=dict(color='#ff6b6b', width=1.2, dash='dot'),
    yaxis='y2',
    hovertemplate='Detected: %{y}<extra></extra>',
))

for region in summary['detection_regions']:
    fig2.add_vrect(
        x0=region[0], x1=region[1],
        fillcolor="#ff6b6b", opacity=0.12,
        layer="below", line_width=0,
    )

fig2.update_layout(
    template="plotly_dark",
    paper_bgcolor="#0a0e17",
    plot_bgcolor="#0d1117",
    height=300,
    margin=dict(l=20, r=20, t=40, b=20),
    title=dict(text="ML DETECTION CONFIDENCE", font=dict(family="Outfit", size=14, color="#4a5568"), x=0),
    legend=dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
        font=dict(family="JetBrains Mono", size=11, color="#c9d1d9"),
        bgcolor="rgba(0,0,0,0)",
    ),
    xaxis=dict(title="Sample", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568")),
    yaxis=dict(title="Confidence", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568"), range=[0, 1]),
    yaxis2=dict(title="Detection", overlaying='y', side='right', gridcolor="#1e2d3d", range=[-0.1, 1.1]),
    hovermode="x unified",
)

st.plotly_chart(fig2, use_container_width=True)

with st.expander("View Raw Data Table"):
    st.dataframe(df[SENSOR_COLUMNS], use_container_width=True, height=300)

# --- Radar section ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">Radar</div>', unsafe_allow_html=True)

RADAR_CSV = str(BASE_DIR / "data" / "sensor_data" / "radar_log.csv")

try:
    radar_df = pd.read_csv(RADAR_CSV)

    r1, r2, r3 = st.columns(3)
    with r1:
        presence_val = int(radar_df["presence"].iloc[-1])
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value" style="color: {'#ff6b6b' if presence_val else '#00ff88'}">
                {'DETECTED' if presence_val else 'CLEAR'}
            </div>
            <div class="metric-label">Presence</div>
        </div>
        """, unsafe_allow_html=True)
    with r2:
        dist_val = radar_df["distance_m"].iloc[-1]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{dist_val:.2f}m</div>
            <div class="metric-label">Distance</div>
        </div>
        """, unsafe_allow_html=True)
    with r3:
        doppler_val = radar_df["micro_doppler"].iloc[-1]
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{doppler_val:.3f}</div>
            <div class="metric-label">Micro-Doppler</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatter(
        y=radar_df["distance_m"].values,
        mode='lines',
        name='Distance (m)',
        line=dict(color='#00b4d8', width=1.5),
    ))
    fig_radar.add_trace(go.Scatter(
        y=radar_df["micro_doppler"].values,
        mode='lines',
        name='Micro-Doppler',
        line=dict(color='#ffd166', width=1.2),
        yaxis='y2',
    ))
    fig_radar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e17",
        plot_bgcolor="#0d1117",
        height=280,
        margin=dict(l=20, r=20, t=40, b=20),
        title=dict(text="RADAR — DISTANCE & MICRO-DOPPLER", font=dict(family="Outfit", size=14, color="#4a5568"), x=0),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(family="JetBrains Mono", size=11, color="#c9d1d9"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(title="Sample", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d"),
        yaxis=dict(title="Distance (m)", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d"),
        yaxis2=dict(title="Micro-Doppler", overlaying='y', side='right', gridcolor="#1e2d3d"),
        hovermode="x unified",
    )
    st.plotly_chart(fig_radar, use_container_width=True)

except FileNotFoundError:
    st.markdown("""
    <div style="text-align:center; padding: 40px 0; color: #2d3748; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;">
        radar not connected
    </div>
    """, unsafe_allow_html=True)

if not st.session_state.paused:
    time.sleep(2)
    st.rerun()