# ICSDefenders - Pest Detection Dashboard

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

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

    /* section headers */
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

    /* sensor config cards */
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
for key in ["log", "processed_data", "detections", "summary", "raw_data"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "log" else None


def log(msg: str):
    timestamp = datetime.now().strftime("%H:%M:%S")
    st.session_state.log.append(f"[{timestamp}] {msg}")


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

# sidebar - just detection settings now
with st.sidebar:
    st.markdown("### ⚙ Detection Settings")

    with st.expander("Thresholds", expanded=False):
        thresholds = {}
        for sensor in SENSOR_COLUMNS:
            thresholds[sensor] = st.number_input(
                sensor, value=DEFAULT_THRESHOLDS[sensor], step=10, key=f"t_{sensor}"
            )

    st.markdown("---")
    min_sensors = st.slider("Min sensors to trigger", 1, 5, 2)
    rolling_window = st.slider("Smoothing window", 1, 20, 5)

# baseline values section - styled cards
st.markdown('<div class="section-header">⬡ Sensor Baseline Calibration</div>', unsafe_allow_html=True)

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
            "Baseline", value=DEFAULT_BASELINE[sensor], step=10,
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

    except Exception as e:
        st.error(f"Error: {e}")
        log(f"Error: {e}")

# display results if we have them
if st.session_state.summary is not None:
    summary = st.session_state.summary
    df = st.session_state.processed_data
    detections = st.session_state.detections

    # results header
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

    # color for each sensor line
    sensor_colors = {
        'MQ3': '#00ff88',
        'MQ135': '#00b4d8',
        'MQ138': '#e0e0e0',
        'MQ131': '#ffd166',
        'TGS2602': '#ef476f',
    }

    # main chart - all sensors smoothed with detection zones highlighted
    fig = make_subplots(rows=1, cols=1)

    for sensor in SENSOR_COLUMNS:
        fig.add_trace(go.Scatter(
            y=df[f"{sensor}_rolling"].values,
            mode='lines',
            name=sensor,
            line=dict(color=sensor_colors[sensor], width=1.5),
            hovertemplate=f'{sensor}: %{{y:.0f}}<extra></extra>',
        ))

    # red shading where flies were detected
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

    # second chart - how far each sensor is from normal
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

    # collapsible raw data and log
    with st.expander("📋 View Raw Data Table"):
        st.dataframe(df[SENSOR_COLUMNS], use_container_width=True, height=300)

    if st.session_state.log:
        with st.expander("📝 Event Log"):
            log_text = "\n".join(reversed(st.session_state.log))
            st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)

# empty state before any data is loaded
else:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; padding: 60px 0;">
        <p style="font-family: 'Outfit', sans-serif; font-size: 1.3rem; color: #2d3748;">
            Load sensor data and hit <b style="color: #00ff88;">▶ ANALYZE</b> to begin
        </p>
        <p style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #1e2d3d;">
            parser → preprocessing → model → visualization
        </p>
    </div>
    """, unsafe_allow_html=True)