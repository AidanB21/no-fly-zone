# # ###########################################################
# # # ICSDefenders – Streamlit GUI (Fully Commented Version)
# # # This version explains EVERYTHING in simple terms.
# # ###########################################################

# # Streamlit: GUI framework that turns Python into a web app
# import streamlit as st

# # Basic Python libraries
# import time
# import random
# import numpy as np
# import pandas as pd
# from datetime import datetime


# ###########################################################
# # PAGE CONFIGURATION
# # This sets the title of the web app and the layout width.
# ###########################################################
# st.set_page_config(
#     page_title="ICSDefenders – Pest Detection Dashboard",
#     layout="wide",
# )


# ###########################################################
# # SESSION STATE
# # This is Streamlit’s way of remembering things (like logs
# # or previous scan results) each time the user presses a button.
# ###########################################################
# if "log" not in st.session_state:
#     st.session_state.log = []   # stores our event log messages

# if "last_result" not in st.session_state:
#     st.session_state.last_result = None  # stores radar/VOC/ML results from last scan


# ###########################################################
# # LOGGING FUNCTION
# # Adds a message with a timestamp to the event log.
# ###########################################################
# def log(msg: str):
#     timestamp = datetime.now().strftime("%H:%M:%S")
#     st.session_state.log.append(f"[{timestamp}] {msg}")


# ###########################################################
# # FAKE DATA GENERATORS (DEMO MODE)
# # These functions create "fake" radar/VOC/model data
# # so you can test the GUI BEFORE integrating real sensors.
# ###########################################################

# def fake_radar_data(num_points: int = 128):
#     """
#     Creates a fake radar signal (sin wave + noise).
#     In the real project, you’ll replace this with:
#     - radar.read_frame()
#     - radar.get_fft()
#     - etc.
#     """
#     x = np.linspace(0, 1, num_points)
#     y = np.sin(10 * 2 * np.pi * x) + 0.3 * np.random.randn(num_points)
#     return x, y


# def fake_voc_data(num_sensors: int = 4):
#     """
#     Generates fake VOC sensor values.
#     Replace with actual:
#     - sensor.read_voc()
#     """
#     labels = [f"VOC {i+1}" for i in range(num_sensors)]
#     values = np.random.uniform(0, 1, size=num_sensors)  # random intensity levels
#     return labels, values


# def fake_ml_decision(model_name: str, threshold: float):
#     """
#     Simulates an ML decision.
#     Replace with REAL:
#     - features = extract_features(radar, voc)
#     - pest_prob = model.predict_proba(features)
#     """
#     pest_prob = random.random()  # number between 0 and 1
#     decision = "Pest Detected" if pest_prob >= threshold else "No Pest"
#     return decision, pest_prob


# ###########################################################
# # GUI STARTS HERE
# ###########################################################

# # Title displayed at the top of the dashboard
# st.title("ICSDefenders – Pest Detection Dashboard")
# st.caption("Prototype GUI for radar + VOC based pest detection system")

# # Divide the top section into 3 columns
# top_left, top_mid, top_right = st.columns([2, 2, 2])

# ###########################################################
# # LEFT PANEL – Connection Status
# ###########################################################
# with top_left:
#     st.subheader("Connection Status (Demo Mode)")
#     # In the real build, these reflect real hardware connection state
#     st.markdown("🟢 Radar Sensor Connected")
#     st.markdown("🟢 VOC Sensor Array Connected")
#     st.markdown("🟢 ML Model Loaded")


# ###########################################################
# # MIDDLE PANEL – Model Settings
# ###########################################################
# with top_mid:
#     st.subheader("Model Settings (Demo)")

#     # Dropdown to select model
#     model_name = st.selectbox(
#         "Select Model",
#         ["Random Forest (demo)", "SVM (demo)", "CatBoost (demo)"],
#         index=0,
#     )

#     # Slider to set probability threshold
#     threshold = st.slider(
#         "Alert Threshold (pest probability)",
#         min_value=0.1,
#         max_value=0.9,
#         value=0.7,
#         step=0.05,
#     )


# ###########################################################
# # RIGHT PANEL – Buttons
# ###########################################################
# with top_right:
#     st.subheader("Controls")
#     # When user clicks this button, GUI triggers a fake scan
#     run_demo = st.button("Run Demo Scan")


# # Horizontal line across the GUI
# st.markdown("---")


# ###########################################################
# # MIDDLE SECTION – Radar and VOC plots
# ###########################################################
# radar_col, voc_col = st.columns(2)

# with radar_col:
#     st.subheader("Radar Signal Visualization (Demo)")
#     radar_placeholder = st.empty()  # empty area for dynamic radar plot

# with voc_col:
#     st.subheader("VOC Sensor Intensity (Demo)")
#     voc_placeholder = st.empty()    # empty area for VOC bar plot


# ###########################################################
# # BOTTOM SECTION – ML RESULTS + EVENT LOG
# ###########################################################
# bottom_left, bottom_right = st.columns([1, 2])

# ###########################
# # ML Result Box
# ###########################
# with bottom_left:
#     st.subheader("Detection Result")

#     # When button clicked → generate fake data
#     if run_demo:
#         # Generate fake radar data
#         x, radar_y = fake_radar_data()

#         # Generate fake VOC data
#         labels, voc_values = fake_voc_data()

#         # Fake ML classifier result
#         decision, pest_prob = fake_ml_decision(model_name, threshold)

#         # Save the results
#         st.session_state.last_result = {
#             "x": x,
#             "radar_y": radar_y,
#             "labels": labels,
#             "voc_values": voc_values,
#             "decision": decision,
#             "pest_prob": pest_prob,
#         }

#         # Add log entry
#         log(f"Scan run: Model={model_name}, Decision={decision}, p={pest_prob:.2f}")

#     # Display the last scan result
#     if st.session_state.last_result is not None:
#         result = st.session_state.last_result
#         decision = result["decision"]
#         pest_prob = result["pest_prob"]

#         # Error box for pest detection, success for no pest
#         if decision == "Pest Detected":
#             st.error(f"🚨 {decision} (p = {pest_prob:.2f})")
#         else:
#             st.success(f"✅ {decision} (p = {pest_prob:.2f})")

#         st.write("Model:", model_name)
#         st.write("Threshold:", threshold)

#     else:
#         st.info("Click 'Run Demo Scan' to simulate a detection.")


# ###########################
# # Log + Plots
# ###########################
# with bottom_right:
#     st.subheader("Event Log + Visualizations")

#     # Show radar plot if we have previous data
#     if st.session_state.last_result is not None:

#         # Radar signal plot
#         rad_df = pd.DataFrame({"Radar Signal": st.session_state.last_result["radar_y"]})
#         radar_placeholder.line_chart(rad_df)

#         # VOC bar chart
#         voc_df = pd.DataFrame(
#             {"VOC": st.session_state.last_result["voc_values"]},
#             index=st.session_state.last_result["labels"],
#         )
#         voc_placeholder.bar_chart(voc_df)

#     # Display event log text box
#     if st.session_state.log:
#         st.text_area("Log", "\n".join(st.session_state.log), height=200)
#     else:
#         st.info("No events yet.")

# # ##########################################################
# # ICSDefenders – Streamlit GUI (Slightly More Advanced)
# # Still simple, but with:
# # - Sidebar configuration
# # - Basic "feature" stats
# # - Scan history + download
# # ##########################################################

###########################################################
# ICSDefenders – Streamlit GUI (Polished UI Version)
# Same logic as your version, just a nicer layout:
# - Styled header banner
# - Sidebar for model & threshold
# - Cleaner top row
# - Event log in expander
###########################################################

###########################################################
# ICSDefenders – Streamlit GUI (Polished, Non-Truncating UI)
###########################################################

import streamlit as st
import random
import numpy as np
import pandas as pd
from datetime import datetime

###########################################################
# PAGE CONFIGURATION
###########################################################
st.set_page_config(
    page_title="ICSDefenders – Pest Detection Dashboard",
    page_icon="🪲",
    layout="wide",
)

###########################################################
# SESSION STATE
###########################################################
if "log" not in st.session_state:
    st.session_state.log = []   # stores our event log messages

if "last_result" not in st.session_state:
    st.session_state.last_result = None  # stores radar/VOC/ML results from last scan


###########################################################
# LOGGING FUNCTION
###########################################################
def log(msg: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.log.append(f"[{timestamp}] {msg}")



# Fake Data Generation

def fake_radar_data(num_points: int = 128):
    """Creates a fake radar signal (sin wave + noise)."""
    x = np.linspace(0, 1, num_points)
    y = np.sin(10 * 2 * np.pi * x) + 0.3 * np.random.randn(num_points)
    return x, y


def fake_voc_data(num_sensors: int = 4):
    """Generates fake VOC sensor values."""
    labels = [f"VOC {i+1}" for i in range(num_sensors)]
    values = np.random.uniform(0, 1, size=num_sensors)
    return labels, values


def fake_ml_decision(model_name: str, threshold: float):
    """
    Simulates an ML decision.
    Later you can replace this with a real model.predict_proba().
    """
    pest_prob = random.random()  # 0–1
    decision = "Pest Detected" if pest_prob >= threshold else "No Pest"
    return decision, pest_prob


###########################################################
# SIDEBAR – MODEL & SCAN SETTINGS
###########################################################
st.sidebar.markdown("### Model & Scan Settings")

model_name = st.sidebar.selectbox(
    "Select Model (demo / future ML)",
    ["Random Forest (demo)", "SVM (demo)", "CatBoost (demo)"],
    index=0,
)

threshold = st.sidebar.slider(
    "Alert Threshold (pest probability)",
    min_value=0.1,
    max_value=0.9,
    value=0.7,
    step=0.05,
)

st.sidebar.markdown("---")
if st.sidebar.button("Clear Log & Last Result"):
    st.session_state.log.clear()
    st.session_state.last_result = None
    st.sidebar.success("Cleared log and last result.")

###########################################################
# HEADER – GRADIENT BANNER
###########################################################
st.markdown(
    """
    <div style="
        padding: 1.0rem 1.5rem;
        border-radius: 0.9rem;
        background: linear-gradient(90deg, #0f766e, #059669, #22c55e);
        color: white;
        margin-bottom: 1.2rem;
    ">
      <h1 style="margin: 0; font-size: 1.9rem;">
        ICSDefenders – Pest Detection Dashboard
      </h1>
      <p style="margin: 0.3rem 0 0; font-size: 0.95rem;">
        Streamlit prototype for radar + VOC based pest detection (simulation mode)
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

###########################################################
# TOP ROW – STATUS • CONFIG SUMMARY • CONTROLS
###########################################################
top_left, top_mid, top_right = st.columns([2, 2, 1.3])

# LEFT: Status "card"
with top_left:
    st.markdown("#### System Status")
    st.markdown(
        """
        <div style="
            padding: 0.85rem 1rem;
            border-radius: 0.8rem;
            background-color: #020617;
            color: #e5e7eb;
            border: 1px solid #1f2937;
            font-size: 0.92rem;
        ">
          <p style="margin: 0.15rem 0;">🟢 Radar Sensor Connected (demo)</p>
          <p style="margin: 0.15rem 0;">🟢 VOC Sensor Array Connected (demo)</p>
          <p style="margin: 0.15rem 0;">🟢 Decision Engine Available (simulated model)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# MIDDLE: Config summary (no truncation)
with top_mid:
    st.markdown("#### Current Configuration")
    st.markdown(f"**Model:** {model_name}")
    st.markdown(f"**Alert Threshold:** {threshold:.2f}")

    st.markdown(
        """
        <span style="font-size:0.8rem; color:#9ca3af;">
        The GUI is already wired to support multiple models.
        Once a trained model is available, this dropdown can select
        the active classifier used for decisions.
        </span>
        """,
        unsafe_allow_html=True,
    )

# RIGHT: Controls
with top_right:
    st.markdown("#### Controls")
    run_demo = st.button("▶ Run Demo Scan", use_container_width=True)
    st.caption("Runs one simulated radar + VOC scan and computes a decision.")

st.markdown("---")

###########################################################
# MIDDLE – PLOTS
###########################################################
radar_col, voc_col = st.columns(2)

with radar_col:
    st.markdown("### Radar Signal")
    st.caption("Time-domain plot of the simulated radar return.")
    radar_placeholder = st.empty()

with voc_col:
    st.markdown("### VOC Sensor Intensities")
    st.caption("Relative VOC levels across simulated sensors.")
    voc_placeholder = st.empty()

###########################################################
# BOTTOM – DETECTION RESULT • VISUALS • EVENT LOG
###########################################################
bottom_left, bottom_right = st.columns([1.2, 2])

# LEFT: Detection result
with bottom_left:
    st.markdown("### Detection Result")

    if run_demo:
        # 1) Fake radar & VOC data
        x, radar_y = fake_radar_data()
        labels, voc_values = fake_voc_data()

        # 2) Fake model decision
        decision, pest_prob = fake_ml_decision(model_name, threshold)

        # 3) Save to session_state
        st.session_state.last_result = {
            "x": x,
            "radar_y": radar_y,
            "labels": labels,
            "voc_values": voc_values,
            "decision": decision,
            "pest_prob": pest_prob,
            "model_name": model_name,
            "threshold": threshold,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

        log(f"Scan run: model={model_name}, decision={decision}, p={pest_prob:.2f}")

    # Show last result if it exists
    if st.session_state.last_result is not None:
        result = st.session_state.last_result
        decision = result["decision"]
        pest_prob = result["pest_prob"]

        # Detection card (no truncation)
        if decision == "Pest Detected":
            st.markdown(
                f"""
                <div style="
                    padding: 0.75rem 1rem;
                    border-radius: 0.8rem;
                    background-color: #7f1d1d;
                    border: 1px solid #b91c1c;
                    color: #fee2e2;
                    margin-bottom: 0.6rem;
                ">
                  <strong>🚨 {decision}</strong><br>
                  Pest probability: {pest_prob:.2f}
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div style="
                    padding: 0.75rem 1rem;
                    border-radius: 0.8rem;
                    background-color: #064e3b;
                    border: 1px solid #10b981;
                    color: #d1fae5;
                    margin-bottom: 0.6rem;
                ">
                  <strong>✅ {decision}</strong><br>
                  Pest probability: {pest_prob:.2f}
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(f"**Model:** {result['model_name']}")
        st.markdown(f"**Threshold:** {result['threshold']:.2f}")
        st.markdown(f"**Timestamp:** {result['timestamp']}")
    else:
        st.info("Click **Run Demo Scan** to simulate a detection.")

# RIGHT: Plots + Log
with bottom_right:
    st.markdown("### Visualizations & Log")

    # Show plots for last result
    if st.session_state.last_result is not None:
        rad_df = pd.DataFrame(
            {"Radar Signal": st.session_state.last_result["radar_y"]}
        )
        radar_placeholder.line_chart(rad_df)

        voc_df = pd.DataFrame(
            {"VOC": st.session_state.last_result["voc_values"]},
            index=st.session_state.last_result["labels"],
        )
        voc_placeholder.bar_chart(voc_df)

    # Event log inside expander
    with st.expander("Event Log", expanded=False):
        if st.session_state.log:
            st.text_area(
                "Log entries",
                "\n".join(st.session_state.log),
                height=200,
            )
        else:
            st.info("No events yet.")

###########################################################
# FOOTER
###########################################################
st.markdown(
    """
    <hr>
    <div style="font-size: 0.8rem; color: #9ca3af; margin-top: 0.3rem;">
      ICSDefenders • Streamlit prototype • Radar + VOC → simulated ML decision
    </div>
    """,
    unsafe_allow_html=True,
)

