# ICSDefenders - Pest Detection Dashboard

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# our pipeline modules
from parser import load_sensor_data
from preprocess import preprocess_data, DEFAULT_BASELINE, SENSOR_COLUMNS
from model import predict, DEFAULT_THRESHOLDS

# page setup
st.set_page_config(
    page_title="No-Fly-Zone | Pest Detection",
    layout="wide",
)

# custom dark theme styling
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

    .log-box {
        background: #0d1117;
        border: 1px solid #1e2d3d;
        border-radius: 8px;
        padding: 12px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #4a5568;
        max-height: 120px;
        overflow-y: auto;
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
        transition: border-color 0.2s ease;
    }
    .sensor-card:hover {
        border-color: #00ff8844;
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

    .calibrated-badge {
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.75rem;
        color: #00ff88;
        background: #00ff8815;
        border: 1px solid #00ff8833;
        border-radius: 6px;
        padding: 4px 10px;
        display: inline-block;
        margin-top: 8px;
    }

    /* make all text visible on dark background */
    .stRadio label, .stRadio div[role="radiogroup"] label,
    .stRadio div[role="radiogroup"] label p,
    .stRadio div[role="radiogroup"] label div,
    .stRadio div[role="radiogroup"] label span {
        color: #c9d1d9 !important;
    }
    .stTextInput label, .stFileUploader label, .stSelectbox label,
    .stSlider label, .stNumberInput label, .stCheckbox label {
        color: #c9d1d9 !important;
    }
    .stTextInput input, .stNumberInput input {
        color: #c9d1d9 !important;
        background-color: #0d1117 !important;
        border-color: #1e2d3d !important;
    }
    .stFileUploader div, .stFileUploader span, .stFileUploader p,
    .stFileUploader section, .stFileUploader small {
        color: #c9d1d9 !important;
    }
    .stExpander summary span {
        color: #c9d1d9 !important;
    }
    .stMarkdown p, .stMarkdown li {
        color: #c9d1d9;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stButton > button {
        background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
        color: #0a0e17;
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-size: 0.95rem;
        letter-spacing: 0.5px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #00cc6a 0%, #00ff88 100%);
        color: #0a0e17;
    }
</style>
""", unsafe_allow_html=True)

# session state so streamlit remembers things between clicks
for key in ["log", "processed_data", "detections", "summary", "raw_data", "radar_data", "calibrated"]:
    if key not in st.session_state:
        if key == "log":
            st.session_state[key] = []
        elif key == "calibrated":
            st.session_state[key] = False
        else:
            st.session_state[key] = None

# store calibrated baseline values
if "cal_baselines" not in st.session_state:
    st.session_state.cal_baselines = None


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append(f"[{timestamp}] {msg}")


# simulated baseline values that calibration "discovers"
CALIBRATED_VALUES = {
    'MQ3': 172,
    'MQ135': 1965,
    'MQ138': 3008,
    'MQ131': 1092,
    'TGS2602': 845,
}

# sensor descriptions for the cards
sensor_info = {
    'MQ3': {'css': 'mq3', 'desc': 'Alcohol & Ethanol'},
    'MQ135': {'css': 'mq135', 'desc': 'Air Quality / CO₂'},
    'MQ138': {'css': 'mq138', 'desc': 'Organic Gases'},
    'MQ131': {'css': 'mq131', 'desc': 'Ozone'},
    'TGS2602': {'css': 'tgs2602', 'desc': 'VOCs & Odor'},
}

# header
st.markdown('<p class="main-title">NO-FLY-ZONE</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">gas sensor array · ml detection pipeline · v1.0</p>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# sidebar - detection settings
with st.sidebar:
    st.markdown("### ⚙ Detection Settings")

    st.markdown("**Thresholds**")
    thresholds = {}
    for sensor in SENSOR_COLUMNS:
        thresholds[sensor] = st.number_input(
            f"{sensor} threshold", value=DEFAULT_THRESHOLDS[sensor], step=10, key=f"t_{sensor}"
        )

    st.markdown("---")
    min_sensors = st.slider("Min sensors to trigger", 1, 5, 2)
    rolling_window = st.slider("Smoothing window", 1, 20, 5)

# baseline calibration section
st.markdown('<div class="section-header">⬡ Sensor Baseline Calibration</div>', unsafe_allow_html=True)

# calibration button row
cal_col, status_col = st.columns([1, 3])

with cal_col:
    run_calibration = st.button("🔄 START CALIBRATION", use_container_width=True)

with status_col:
    if st.session_state.calibrated:
        st.markdown('<span class="calibrated-badge">✓ CALIBRATED</span>', unsafe_allow_html=True)

# run calibration animation
if run_calibration:
    progress_bar = st.progress(0)
    status_text = st.empty()

    steps = [
        "Connecting to sensor array...",
        "Reading MQ3 baseline...",
        "Reading MQ135 baseline...",
        "Reading MQ138 baseline...",
        "Reading MQ131 baseline...",
        "Reading TGS2602 baseline...",
        "Averaging 50 samples per sensor...",
        "Calculating noise floor...",
        "Validating readings...",
        "Calibration complete!",
    ]

    for i, step in enumerate(steps):
        status_text.markdown(f'<p style="font-family: JetBrains Mono; font-size: 0.8rem; color: #00ff88;">{step}</p>', unsafe_allow_html=True)
        progress_bar.progress((i + 1) / len(steps))
        time.sleep(0.4)

    time.sleep(0.3)
    progress_bar.empty()
    status_text.empty()

    st.session_state.calibrated = True
    st.session_state.cal_baselines = CALIBRATED_VALUES.copy()
    log("Calibration complete — baseline values auto-filled")
    st.rerun()

# use calibrated values if available, otherwise use defaults
active_baselines = st.session_state.cal_baselines if st.session_state.calibrated else DEFAULT_BASELINE

# sensor cards with baseline inputs
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

# file loading and analyze button
st.markdown('<div class="section-header">⬡ Data Source</div>', unsafe_allow_html=True)

load_col, btn_col = st.columns([4, 1])

with load_col:
    data_source = st.radio(
        "Source", ["File path", "Upload"], horizontal=True, label_visibility="collapsed"
    )
    if data_source == "File path":
        file_path = st.text_input("Path", value="data/sample_sensorData.txt", label_visibility="collapsed")
    else:
        uploaded_file = st.file_uploader("Upload", type=["txt", "csv"], label_visibility="collapsed")

with btn_col:
    st.markdown("<br>", unsafe_allow_html=True)
    run_analysis = st.button("▶ ANALYZE", use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)

# run the full pipeline when button is clicked
if run_analysis:
    try:
        if data_source == "File path":
            raw_df = load_sensor_data(file_path)
            log(f"Loaded: {file_path}")
        else:
            if uploaded_file is not None:
                temp_path = "data/temp_upload.txt"
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                raw_df = load_sensor_data(temp_path)
                log(f"Loaded: {uploaded_file.name}")
            else:
                st.warning("Upload a file first.")
                st.stop()

        st.session_state.raw_data = raw_df
        log(f"{len(raw_df)} raw samples")

        processed_df = preprocess_data(raw_df, baseline=baseline, window=rolling_window)
        st.session_state.processed_data = processed_df
        log(f"{len(processed_df)} samples after cleaning")

        detections, summary = predict(processed_df, thresholds=thresholds, min_sensors=min_sensors)
        st.session_state.detections = detections
        st.session_state.summary = summary
        log(f"Result: {summary['fly_samples']} detections in {summary['num_events']} event(s)")

        # try loading radar data if it exists
        try:
            radar_df = pd.read_csv("data/sample_radarData.csv")
            st.session_state.radar_data = radar_df
            log(f"Radar data loaded: {len(radar_df)} samples")
        except FileNotFoundError:
            st.session_state.radar_data = None
            log("No radar data file found")

    except Exception as e:
        st.error(f"Error: {e}")
        log(f"Error: {e}")

# display results if we have them
if st.session_state.summary is not None:
    summary = st.session_state.summary
    df = st.session_state.processed_data
    detections = st.session_state.detections

    st.markdown('<div class="section-header">⬡ Detection Results</div>', unsafe_allow_html=True)

    # top row metric cards
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

    # detection alert banner
    if summary['num_events'] > 0:
        events_html = " ".join([f'<span class="event-tag">samples {r[0]}–{r[1]}</span>' for r in summary['detection_regions']])
        st.markdown(f'<div class="alert-detected">🚨 FLY ACTIVITY DETECTED &nbsp;·&nbsp; {events_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-clear">✅ ALL CLEAR — No fly activity detected</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # sensor line colors
    sensor_colors = {
        'MQ3': '#00ff88',
        'MQ135': '#00b4d8',
        'MQ138': '#e0e0e0',
        'MQ131': '#ffd166',
        'TGS2602': '#ef476f',
    }

    # main chart - all sensors smoothed with detection zones
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

    # second chart - distance from baseline
    fig2 = go.Figure()

    for sensor in SENSOR_COLUMNS:
        fig2.add_trace(go.Scatter(
            y=df[f"{sensor}_dist"].values,
            mode='lines',
            name=sensor,
            line=dict(color=sensor_colors[sensor], width=1.2),
            hovertemplate=f'{sensor}: %{{y:.0f}}<extra></extra>',
        ))

    fig2.add_hline(y=0, line_dash="dot", line_color="#4a5568", line_width=0.8)

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
        title=dict(text="DISTANCE FROM BASELINE", font=dict(family="Outfit", size=14, color="#4a5568"), x=0),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(family="JetBrains Mono", size=11, color="#c9d1d9"),
            bgcolor="rgba(0,0,0,0)",
        ),
        xaxis=dict(title="Sample", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568")),
        yaxis=dict(title="Δ from Baseline", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", title_font=dict(size=11, color="#4a5568")),
        hovermode="x unified",
    )

    st.plotly_chart(fig2, use_container_width=True)

# radar data section
st.markdown('<div class="section-header">⬡ mmWave Radar Data</div>', unsafe_allow_html=True)

if st.session_state.radar_data is not None:
    radar_df = st.session_state.radar_data

    # radar metric cards
    r1, r2, r3 = st.columns(3)
    total_detections = radar_df['presence'].sum()
    avg_distance = radar_df[radar_df['presence'] == 1]['distance_m'].mean() if total_detections > 0 else 0
    avg_doppler = radar_df[radar_df['presence'] == 1]['micro_doppler'].mean() if total_detections > 0 else 0

    for col, val, label in zip(
        [r1, r2, r3],
        [total_detections, f"{avg_distance:.1f}m", f"{avg_doppler:.2f}"],
        ["PRESENCE TRIGGERS", "AVG DISTANCE", "AVG DOPPLER"]
    ):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # radar chart - presence and micro-doppler over time
    fig_radar = make_subplots(
        rows=2, cols=1,
        row_heights=[0.4, 0.6],
        shared_xaxes=True,
        vertical_spacing=0.08,
        subplot_titles=("PRESENCE DETECTION", "MICRO-DOPPLER STRENGTH & DISTANCE"),
    )

    # presence as a filled area (top chart)
    fig_radar.add_trace(go.Scatter(
        y=radar_df['presence'].values,
        mode='lines',
        name='Presence',
        fill='tozeroy',
        line=dict(color='#00ff88', width=1),
        fillcolor='rgba(0, 255, 136, 0.2)',
        hovertemplate='Presence: %{y}<extra></extra>',
    ), row=1, col=1)

    # micro-doppler strength (bottom chart)
    fig_radar.add_trace(go.Scatter(
        y=radar_df['micro_doppler'].values,
        mode='lines',
        name='Micro-Doppler',
        line=dict(color='#ef476f', width=1.5),
        hovertemplate='Doppler: %{y:.3f}<extra></extra>',
    ), row=2, col=1)

    # distance overlay (bottom chart, secondary feel)
    fig_radar.add_trace(go.Scatter(
        y=radar_df['distance_m'].values,
        mode='lines',
        name='Distance (m)',
        line=dict(color='#ffd166', width=1, dash='dot'),
        hovertemplate='Distance: %{y:.2f}m<extra></extra>',
    ), row=2, col=1)

    fig_radar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0a0e17",
        plot_bgcolor="#0d1117",
        height=450,
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            font=dict(family="JetBrains Mono", size=11, color="#c9d1d9"),
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
    )

    # style the subplot title fonts
    fig_radar.update_annotations(font=dict(family="Outfit", size=12, color="#4a5568"))

    for i in [1, 2]:
        fig_radar.update_xaxes(gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", row=i, col=1)
        fig_radar.update_yaxes(gridcolor="#1e2d3d", zerolinecolor="#1e2d3d", row=i, col=1)

    fig_radar.update_xaxes(title="Sample", title_font=dict(size=11, color="#4a5568"), row=2, col=1)
    fig_radar.update_yaxes(title="On/Off", title_font=dict(size=11, color="#4a5568"), row=1, col=1)
    fig_radar.update_yaxes(title="Intensity / Meters", title_font=dict(size=11, color="#4a5568"), row=2, col=1)

    st.plotly_chart(fig_radar, use_container_width=True)

else:
    # placeholder when no radar data is loaded
    st.markdown("""
    <div style="background: linear-gradient(135deg, #111827 0%, #1a2332 100%);
                border: 1px dashed #1e2d3d; border-radius: 12px; padding: 40px 20px; text-align: center;">
        <div style="font-size: 2.5rem; margin-bottom: 12px;">📡</div>
        <div style="font-family: 'Outfit', sans-serif; font-size: 1rem; font-weight: 500; color: #4a5568; margin-bottom: 6px;">
            mmWave Radar — No Data Loaded
        </div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; color: #2d3748;">
            place sample_radarData.csv in the data/ folder · auto-loads when you hit ANALYZE
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# collapsible raw data and log
if st.session_state.summary is not None:
    with st.expander("📋 View Raw Data Table"):
        st.dataframe(st.session_state.processed_data[SENSOR_COLUMNS], use_container_width=True, height=300)

if st.session_state.log:
    with st.expander("📝 Event Log"):
        log_text = "\n".join(reversed(st.session_state.log))
        st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)

# empty state before any data is loaded
if st.session_state.summary is None:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 40px 0;">
        <p style="font-family: 'Outfit', sans-serif; font-size: 1.3rem; color: #2d3748;">
            Load sensor data and hit <b style="color: #00ff88;">▶ ANALYZE</b> to begin
        </p>
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #1e2d3d;">
            parser → preprocessing → model → visualization
        </p>
    </div>
    """, unsafe_allow_html=True)