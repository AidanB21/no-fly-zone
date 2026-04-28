import time
import subprocess
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

from parser import load_live_csv, load_sensor_data
from preprocess import preprocess_data, DEFAULT_BASELINE, SENSOR_COLUMNS
from model import predict_row, predict_batch, get_status_text
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
LIVE_CSV = str(BASE_DIR / "data" / "sensor_data" / "sensor_log.csv")

st.set_page_config(
    page_title="No-Fly-Zone | Pest Detection",
    layout="wide",
)

# --- Session state ---
if 'paused' not in st.session_state:
    st.session_state.paused = False
if 'cal_start_time' not in st.session_state:
    st.session_state.cal_start_time = None
if 'show_test' not in st.session_state:
    st.session_state.show_test = (BASE_DIR / "fly_model.pkl").exists()
if 'testing' not in st.session_state:
    st.session_state.testing = False
if 'test_start_time' not in st.session_state:
    st.session_state.test_start_time = None
if 'test_result' not in st.session_state:
    st.session_state.test_result = None

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
        font-size: 3.2rem;
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
        border: 2px solid #f85149;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 1.4rem;
        color: #ff6b6b;
        font-weight: 700;
    }
    .alert-clear {
        background: linear-gradient(135deg, #0d1f12 0%, #0f2b16 100%);
        border: 2px solid #00ff88;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 1.4rem;
        color: #00ff88;
        font-weight: 700;
        opacity: 0.9;
    }
    .split-alerts {
        display: flex;
        gap: 20px;
        margin-bottom: 20px;
    }
    .alert-box {
        flex: 1;
        border-radius: 12px;
        padding: 24px 20px;
        text-align: center;
        font-family: 'Outfit', sans-serif;
        font-size: 1.5rem;
        font-weight: 700;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        gap: 8px;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0.4); }
        70% { box-shadow: 0 0 0 20px rgba(248, 81, 73, 0); }
        100% { box-shadow: 0 0 0 0 rgba(248, 81, 73, 0); }
    }
    .alert-box.detected {
        background: linear-gradient(135deg, #2d1117 0%, #3b1219 100%);
        border: 2px solid #f85149;
        color: #ff6b6b;
        animation: pulse-red 1.5s infinite;
    }
    .alert-box.clear {
        background: linear-gradient(135deg, #0d1f12 0%, #0f2b16 100%);
        border: 2px solid #00ff88;
        color: #00ff88;
        opacity: 0.9;
    }
    .alert-subtitle {
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
        font-weight: 400;
        opacity: 0.9;
    }

    .event-tag {
        display: inline-block;
        background: #f851491a;
        border: 1px solid #f8514944;
        border-radius: 6px;
        padding: 4px 12px;
        margin: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
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
        font-size: 0.8rem;
        color: #ffffff;
        margin-bottom: 10px;
    }

    .stTextInput label, .stSelectbox label,
    .stSlider label, .stNumberInput label, .stCheckbox label {
        color: #c9d1d9 !important;
    }
    .stRadio label, .stRadio div[role="radiogroup"] label p {
        color: #ffffff !important;
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

colA, colB = st.columns([4, 1])
with colA:
    st.markdown('<p class="main-title">No-Fly-Zone | ICS Defenders</p>', unsafe_allow_html=True)
with colB:
    logo_path = BASE_DIR / "assets" / "ics_logo1.png"
    if logo_path.exists():
        st.image(str(logo_path), width=180)
st.markdown("<br>", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.markdown("### Detection Settings")
    rolling_window = st.slider("Smoothing window", 1, 20, 5)
    conf_thresh = st.slider("Detection Threshold", 0.1, 0.9, 0.3, 0.05, 
                            help="Increase to ensure higher accuracy (fewer false alarms). Decrease to detect faster.")
    st.markdown("---")
    live_mode = st.toggle("Live mode", value=True)

# --- Calibrate ---
if st.session_state.cal_start_time is not None:
    elapsed = time.time() - st.session_state.cal_start_time
    if elapsed < 15:
        st.write(f"Calibrating... {int(elapsed)}s / 15s")
        # Do NOT sleep+rerun here — that aborts the rest of the script and
        # freezes the radar chart. The page's own 2-second rerun loop at the
        # bottom will drive the countdown refresh without blocking rendering.
    else:  # elapsed >= 15
        # Capture the start time BEFORE clearing it from session state
        cal_start_ts   = st.session_state.cal_start_time
        cal_start_dt   = datetime.fromtimestamp(cal_start_ts)
        cal_since_str  = cal_start_dt.strftime("%Y-%m-%d %H:%M:%S")

        # Save gas sensor data from calibration window
        try:
            cal_df   = load_live_csv(LIVE_CSV)
            cal_rows = cal_df[cal_df["Timestamp"] >= cal_start_dt]
            if cal_rows.empty:
                cal_rows = cal_df.tail(60)
            cal_dir = BASE_DIR / "data" / "training" / "clean_air"
            cal_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            with open(cal_dir / f"calibration_{ts}.txt", "w") as f:
                for _, row in cal_rows.iterrows():
                    f.write(",".join(str(int(row[s])) for s in SENSOR_COLUMNS) + "\n")
            subprocess.Popen(["python", str(BASE_DIR / "train_model.py")], cwd=str(BASE_DIR))
        except Exception as e:
            st.error(f"Calibration save error: {e}")

        # Snapshot the radar calibration baseline — just save the
        # micro_doppler values from the 30s calibration window into a
        # separate CSV. The test phase will compare against this directly.
        try:
            radar_csv = BASE_DIR / "data" / "sensor_data" / "radar_log.csv"
            radar_baseline_csv = BASE_DIR / "data" / "sensor_data" / "radar_baseline.csv"
            if radar_csv.exists():
                r_df = pd.read_csv(radar_csv)
                if not r_df.empty and "Timestamp" in r_df.columns:
                    r_df["Timestamp"] = pd.to_datetime(r_df["Timestamp"], errors="coerce")
                    cal_window = r_df[r_df["Timestamp"] >= cal_start_dt]
                    if cal_window.empty:
                        cal_window = r_df.tail(60)
                    cal_window.to_csv(radar_baseline_csv, index=False)
        except Exception as e:
            st.warning(f"Radar baseline snapshot failed: {e}")

        st.session_state.cal_start_time = None
        st.session_state.show_test = True
        st.success("Calibration complete! Gas + radar models training in background.")
else:
    st.markdown('<p style="font-family:Outfit,sans-serif;font-size:2rem;font-weight:700;color:#00ff88;margin-bottom:8px;">Calibrate</p>', unsafe_allow_html=True)
    _produce_choice = st.radio(
        "Produce type",
        ["🍌 Banana", "🍅 Tomato"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if st.button("Start Calibration", type="primary"):
        st.session_state.cal_start_time = time.time()
        st.session_state.test_result = None
        st.rerun()

# --- Test for Flies ---
if st.session_state.show_test and st.session_state.cal_start_time is None:
    if st.session_state.test_start_time is not None:
        elapsed = time.time() - st.session_state.test_start_time
        if elapsed < 60:
            st.write(f"Testing for flies... {int(elapsed)}s / 60s")
            # Same as calibration — don't sleep+rerun here or the radar
            # chart freezes. The bottom rerun loop drives the refresh.
        else:
            # Run gas sensor model on the test window
            try:
                test_df = load_live_csv(LIVE_CSV)
                test_start_dt = datetime.fromtimestamp(st.session_state.test_start_time)
                test_rows = test_df[test_df["Timestamp"] >= test_start_dt]
                if test_rows.empty:
                    test_rows = test_df.tail(60)
                preds = [predict_row([row[s] for s in SENSOR_COLUMNS], threshold=conf_thresh) for _, row in test_rows.iterrows()]
                labels = [p[0] for p in preds]
                confs = [p[1] for p in preds]
                fly_count = sum(labels)
                avg_conf = sum(confs) / len(confs) if confs else 0.0

                # Radar motion check — flag if ANY reading during the test window
                # spiked above baseline_avg + DOPPLER_THRESHOLD, so a brief
                # burst of activity (e.g. seconds 5-8) is never missed.
                DOPPLER_THRESHOLD = 0.015  # m/s — delta above baseline noise
                radar_detected    = False
                radar_available   = False
                baseline_avg      = 0.0
                test_avg          = 0.0
                spike_count       = 0
                spike_threshold   = 0.0
                try:
                    radar_baseline_csv = BASE_DIR / "data" / "sensor_data" / "radar_baseline.csv"
                    radar_live_csv     = BASE_DIR / "data" / "sensor_data" / "radar_log.csv"
                    if radar_baseline_csv.exists() and radar_live_csv.exists():
                        baseline_df = pd.read_csv(radar_baseline_csv)
                        live_df     = pd.read_csv(radar_live_csv)
                        if not baseline_df.empty and not live_df.empty:
                            baseline_avg    = float(baseline_df["micro_doppler"].abs().mean())
                            spike_threshold = baseline_avg + DOPPLER_THRESHOLD
                            live_df["Timestamp"] = pd.to_datetime(live_df["Timestamp"], errors="coerce")
                            test_window = live_df[live_df["Timestamp"] >= test_start_dt]
                            if test_window.empty:
                                test_window = live_df.tail(60)
                            test_avg    = float(test_window["micro_doppler"].abs().mean())
                            spike_count = int((test_window["micro_doppler"].abs() > spike_threshold).sum())
                            radar_detected  = spike_count > 0
                            radar_available = True
                except Exception:
                    pass

                st.session_state.test_result = {
                    "detected":         fly_count > 0,
                    "fly_pct":          round(fly_count / len(labels) * 100, 1),
                    "avg_conf":         avg_conf,
                    "radar_detected":   bool(radar_detected),
                    "radar_available":  radar_available,
                    "baseline_avg":     round(baseline_avg, 4),
                    "test_avg":         round(test_avg, 4),
                    "spike_count":      spike_count,
                    "spike_threshold":  round(spike_threshold, 4),
                    "test_start_dt":    test_start_dt.isoformat(),
                }
            except Exception as e:
                st.error(f"Test error: {e}")
            st.session_state.test_start_time = None
    else:
        if st.button("Test for Flies", type="primary"):
            st.session_state.test_start_time = time.time()
            st.session_state.test_result = None
            st.rerun()

# --- Live radar motion check (runs every refresh, independent of test button) ---
# Compares the AVERAGE absolute micro-doppler of the latest radar frames
# against the calibration baseline. Any delta above DOPPLER_LIVE_THRESHOLD
# (m/s) immediately flags motion.
LIVE_RADAR_WINDOW    = 20      # frames — most recent radar samples to average
DOPPLER_LIVE_THRESHOLD = 0.005 # m/s — any movement above baseline noise trips it

live_radar_motion   = False
live_radar_available = False
live_base_avg       = 0.0
live_test_avg       = 0.0
try:
    radar_baseline_csv = BASE_DIR / "data" / "sensor_data" / "radar_baseline.csv"
    radar_live_csv     = BASE_DIR / "data" / "sensor_data" / "radar_log.csv"
    if radar_baseline_csv.exists() and radar_live_csv.exists():
        _bdf = pd.read_csv(radar_baseline_csv)
        _ldf = pd.read_csv(radar_live_csv)
        if not _bdf.empty and not _ldf.empty:
            live_base_avg = float(_bdf["micro_doppler"].abs().mean())
            recent        = _ldf.tail(LIVE_RADAR_WINDOW)
            live_test_avg = float(recent["micro_doppler"].abs().mean())
            live_radar_motion    = (live_test_avg - live_base_avg) > DOPPLER_LIVE_THRESHOLD
            live_radar_available = True
except Exception:
    pass

# --- Helper for Dual Banners ---
def render_dual_banners(voc_det, voc_text, rad_det, rad_text):
    vc = "detected" if voc_det else "clear"
    rc = "detected" if rad_det else "clear"
    st.markdown(f'''
    <div class="split-alerts">
        <div class="alert-box {vc}">
            <div>{"🚨 VOCs INDICATE FLIES 🚨" if voc_det else "✅ VOCs Clear ✅"}</div>
            <div class="alert-subtitle">{voc_text}</div>
        </div>
        <div class="alert-box {rc}">
            <div>{"🚨 RADAR INDICATES FLIES 🚨" if rad_det else "✅ Radar Clear ✅"}</div>
            <div class="alert-subtitle">{rad_text}</div>
        </div>
    </div><br>
    ''', unsafe_allow_html=True)

# --- Test result / pre-calibration default ---
if st.session_state.cal_start_time is not None:
    pass  # silent during calibration — countdown shown above
elif st.session_state.test_start_time is not None:
    # Test is actively running — hold both banners neutral until complete
    elapsed_t = time.time() - st.session_state.test_start_time
    render_dual_banners(False, "Test in progress...", False,
                        f"Collecting radar data... {int(elapsed_t)}s / 60s")
elif st.session_state.test_result is None:
    # Before the user has hit "Test", use the live radar check as the banner
    radar_det = live_radar_available and live_radar_motion
    vt = "Pending formal test..."
    rt = f"live µ-doppler {live_test_avg:.3f} m/s" if live_radar_available else "Radar offline"
    render_dual_banners(False, vt, radar_det, rt)
else:
    r = st.session_state.test_result
    gas_detected    = r["detected"]
    radar_motion    = r.get("radar_detected", False)
    radar_available = r.get("radar_available", False)
    base_avg        = r.get("baseline_avg", 0.0)
    test_avg        = r.get("test_avg", 0.0)
    spike_count     = r.get("spike_count", 0)

    if gas_detected:
        vt = f"AI Certainty: {r['avg_conf']:.1%} sure it's INFECTED ({r['fly_pct']}% of samples)"
    else:
        vt = f"AI Certainty: {r['avg_conf']:.1%} sure it's CLEAN"

    if radar_available:
        rt = (f"⚡ {spike_count} spike(s) above threshold — motion detected"
              if radar_motion else
              f"avg µ-doppler {test_avg:.3f} m/s vs baseline {base_avg:.3f} — no motion")
    else:
        rt = "Radar offline"
    render_dual_banners(gas_detected, vt, radar_motion, rt)

# --- Sensor labels ---
baseline = DEFAULT_BASELINE
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

st.markdown("<br>", unsafe_allow_html=True)

# --- Load data and run ML pipeline ---
DISPLAY_ROWS = 300   # cap for chart rendering and ML — no need to process full history

try:
    if live_mode:
        raw_df = load_live_csv(LIVE_CSV)
    else:
        raw_df = load_sensor_data("data/sample_sensorData.txt")

    # Only keep the most recent rows — older data adds no value to the live view
    raw_df = raw_df.tail(DISPLAY_ROWS)
    processed_df = preprocess_data(raw_df, baseline=baseline, window=rolling_window)

    # Batch predict entire DataFrame in one call
    labels, confidences = predict_batch(processed_df, SENSOR_COLUMNS, threshold=conf_thresh)

    processed_df["fly_detected"] = labels
    processed_df["confidence"] = confidences

    total_samples = len(processed_df)
    fly_samples = sum(labels)
    fly_percentage = round((fly_samples / total_samples) * 100, 2) if total_samples > 0 else 0

    # Only compute and show detection regions if a test has been explicitly run.
    # Before calibration / during calibration, suppress all detection output
    # so the chart doesn't show red highlights and false "DETECTED" states.
    test_has_run = st.session_state.test_result is not None
    is_calibrating = st.session_state.cal_start_time is not None

    if test_has_run and not is_calibrating:
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
    else:
        regions = []   # suppress highlights until a test is explicitly run

    summary = {
        'total_samples': total_samples,
        'fly_samples': fly_samples if test_has_run else 0,
        'fly_percentage': fly_percentage if test_has_run else 0,
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

# --- Detection Results (only when testing) ---
if st.session_state.testing:
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
        st.markdown(f'<div class="alert-detected">🚨 FLY ACTIVITY DETECTED 🚨<br><span style="font-size:1.1rem; opacity:0.9;">({avg_conf:.0%} avg confidence) &nbsp;·&nbsp; {events_html}</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="alert-clear">✅ ALL CLEAR — No fly activity detected ✅</div>', unsafe_allow_html=True)

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

# --- ML Confidence Chart ---
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

with st.expander("🧠 Machine Learning Feature Analytics"):
    st.markdown("""
    The Random Forest model does not rely on raw gas readings because they drift based on temperature 
    and humidity. Instead, the preprocessing pipeline computes realtime sensor **ratios** to isolate 
    the unique volatile organic compound fingerprint associated with fruit flies. 
    """)
    st.markdown("<br>", unsafe_allow_html=True)
    
    last_row = df.iloc[-1]
    mq3_val = last_row["MQ3_rolling"]
    r_mq135_mq3 = last_row["MQ135_rolling"] / mq3_val if mq3_val > 0 else 0
    r_tgs_mq3 = last_row["TGS2602_rolling"] / mq3_val if mq3_val > 0 else 0
    sensor_sum = sum(last_row[f"{s}_rolling"] for s in SENSOR_COLUMNS)
    tgs_share = last_row["TGS2602_rolling"] / sensor_sum if sensor_sum > 0 else 0

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(label="Primary Infestation Marker (MQ135 / MQ3)", value=f"{r_mq135_mq3:.2f}")
    with c2:
        st.metric(label="Rot & Odor Profile (TGS2602 / MQ3)", value=f"{r_tgs_mq3:.2f}")
    with c3:
        st.metric(label="Total Air Odor Context (TGS Share)", value=f"{tgs_share:.1%}")

with st.expander("View Raw Data Table"):
    st.dataframe(df[SENSOR_COLUMNS], use_container_width=True, height=300)

# --- Radar section ---
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">Radar</div>', unsafe_allow_html=True)

RADAR_CSV = str(BASE_DIR / "data" / "sensor_data" / "radar_log.csv")

try:
    radar_df = pd.read_csv(RADAR_CSV)

    if radar_df.empty:
        raise FileNotFoundError("Radar log is empty — no data yet.")

    # ── Range vs Doppler scatter (full width) ───────────────────────────
    if True:
        # Use recent rows that have objects to reconstruct a point cloud.
        # radar_log.csv stores per-frame summaries (not per-object XY), so
        # we plot distance_m as Y and approximate X=0 (radial only) while
        # colouring by micro_doppler — this gives a range-velocity picture.
        # Plot ALL recent frames — the sensors are always in view so every
        # frame has objects. Filtering by presence==1 would always be true.
        # Colour by micro_doppler so movement stands out against the still
        # sensor background which clusters near zero on the X axis.
        recent = radar_df.tail(60).copy()

        DOPPLER_SCALE = 0.15   # ±0.15 m/s colour range (tuned for micro-motion)

        fig_xy = go.Figure()

        # Radar position marker at origin
        fig_xy.add_trace(go.Scatter(
            x=[0], y=[0],
            mode='markers',
            marker=dict(symbol='triangle-up', size=14, color='#00ff88'),
            name='Radar',
            hoverinfo='skip',
        ))

        if not recent.empty:
            fig_xy.add_trace(go.Scatter(
                x=recent["micro_doppler"].values,
                y=recent["distance_m"].values,
                mode='markers',
                marker=dict(
                    size=10,
                    color=recent["micro_doppler"].values,
                    colorscale='RdBu',
                    cmin=-DOPPLER_SCALE,
                    cmax=DOPPLER_SCALE,
                    colorbar=dict(
                        title=dict(text="Doppler (m/s)", font=dict(color="#c9d1d9")),
                        tickfont=dict(color="#c9d1d9"),
                        x=1.02,
                        thickness=12,
                    ),
                    line=dict(width=0.5, color='white'),
                ),
                name='All frames',
                hovertemplate=(
                    'Range: %{y:.3f} m<br>'
                    'µ-Doppler: %{x:+.4f} m/s<br>'
                    '<extra></extra>'
                ),
            ))

        fig_xy.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0a0e17",
            plot_bgcolor="#0d1117",
            height=380,
            margin=dict(l=20, r=60, t=40, b=40),
            title=dict(
                text="RADAR — RANGE vs DOPPLER  (recent 60 frames)",
                font=dict(family="Outfit", size=13, color="#4a5568"), x=0,
            ),
            xaxis=dict(
                title="Doppler velocity (m/s)",
                gridcolor="#1e2d3d", zerolinecolor="#4a5568",
                range=[-DOPPLER_SCALE * 2, DOPPLER_SCALE * 2],
                title_font=dict(size=11, color="#4a5568"),
            ),
            yaxis=dict(
                title="Range (m)",
                gridcolor="#1e2d3d", zerolinecolor="#1e2d3d",
                rangemode="tozero",
                title_font=dict(size=11, color="#4a5568"),
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
                font=dict(family="JetBrains Mono", size=10, color="#c9d1d9"),
                bgcolor="rgba(0,0,0,0)",
            ),
            hovermode="closest",
        )
        st.plotly_chart(fig_xy, use_container_width=True)

    # ── Micro-doppler time-series (test window) ─────────────────────────
    test_running   = st.session_state.test_start_time is not None
    test_done      = st.session_state.test_result is not None
    r_res          = st.session_state.test_result or {}

    if test_running or test_done:
        try:
            _ldf = pd.read_csv(RADAR_CSV)
            _ldf["Timestamp"] = pd.to_datetime(_ldf["Timestamp"], errors="coerce")

            if test_running:
                _t0 = datetime.fromtimestamp(st.session_state.test_start_time)
                _spk_thresh = None
                _chart_title = "RADAR — MICRO-DOPPLER  (test in progress)"
            else:
                _t0 = datetime.fromisoformat(r_res.get("test_start_dt", ""))
                _spk_thresh = r_res.get("spike_threshold")
                _chart_title = "RADAR — MICRO-DOPPLER  (test window)"

            _win = _ldf[_ldf["Timestamp"] >= _t0].copy()
            if _win.empty:
                _win = _ldf.tail(120)

            _win = _win.reset_index(drop=True)
            _abs_dop = _win["micro_doppler"].abs()

            fig_td = go.Figure()

            # Shade spikes red when test is done and threshold is known
            if _spk_thresh is not None:
                _spike_mask = _abs_dop > _spk_thresh
                for i, (is_spike, val) in enumerate(zip(_spike_mask, _abs_dop)):
                    if is_spike:
                        fig_td.add_vrect(
                            x0=i - 0.5, x1=i + 0.5,
                            fillcolor="#ff6b6b", opacity=0.2,
                            layer="below", line_width=0,
                        )

            fig_td.add_trace(go.Scatter(
                y=_abs_dop.values,
                mode='lines',
                name='|µ-Doppler|',
                line=dict(color='#00b4d8', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(0,180,216,0.07)',
                hovertemplate='|µ-Doppler|: %{y:.4f} m/s<extra></extra>',
            ))

            if _spk_thresh is not None:
                fig_td.add_hline(
                    y=_spk_thresh,
                    line=dict(color='#ff6b6b', width=1.5, dash='dash'),
                    annotation_text=f"threshold {_spk_thresh:.4f} m/s",
                    annotation_position="top right",
                    annotation_font=dict(color="#ff6b6b", size=10),
                )
            elif r_res.get("baseline_avg") is not None:
                _live_thresh = r_res.get("baseline_avg", 0) + 0.015
                fig_td.add_hline(
                    y=_live_thresh,
                    line=dict(color='#ffd166', width=1, dash='dot'),
                    annotation_text="est. threshold",
                    annotation_position="top right",
                    annotation_font=dict(color="#ffd166", size=10),
                )

            fig_td.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0a0e17",
                plot_bgcolor="#0d1117",
                height=280,
                margin=dict(l=20, r=20, t=40, b=20),
                title=dict(text=_chart_title,
                           font=dict(family="Outfit", size=13, color="#4a5568"), x=0),
                xaxis=dict(title="Frame", gridcolor="#1e2d3d", zerolinecolor="#1e2d3d",
                           title_font=dict(size=11, color="#4a5568")),
                yaxis=dict(title="|µ-Doppler| (m/s)", gridcolor="#1e2d3d",
                           zerolinecolor="#1e2d3d", rangemode="tozero",
                           title_font=dict(size=11, color="#4a5568")),
                hovermode="x unified",
            )
            st.plotly_chart(fig_td, use_container_width=True)

            if test_done and r_res.get("radar_detected"):
                spk = r_res.get("spike_count", 0)
                st.markdown(
                    f'<div class="alert-detected">🚨 RADAR MOTION DETECTED — {spk} frame(s) above threshold 🚨</div>',
                    unsafe_allow_html=True,
                )
            elif test_done:
                st.markdown(
                    '<div class="alert-clear">✅ Radar — No motion detected ✅</div>',
                    unsafe_allow_html=True,
                )
        except Exception:
            pass

except FileNotFoundError:
    st.markdown("""
    <div class="alert-clear">No flies detected</div>
    """, unsafe_allow_html=True)

if not st.session_state.paused:
    time.sleep(0.5)
    st.rerun()
