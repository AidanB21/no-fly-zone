# No-Fly-Zone 🪰

A real-time fly detection system that uses a VOC gas sensor array, a DSP microcontroller, and a machine learning classifier to identify fly infestations in produce — before visible damage occurs.

Built as a senior capstone project.

---

## Overview

Flies contaminate produce during early infestation stages that are invisible to the eye. No-Fly-Zone detects the volatile organic compounds (VOCs) emitted by fly activity and classifies produce as clean or infected in real time, using a five-sensor gas array paired with a Random Forest ML model. A mmWave radar module provides complementary motion detection for physical fly presence.

The system is designed around a strict, hardware-validated data pipeline:

```
MCU (TMS320F28379D)
  └─ reads 5 gas sensors + BME280 environmental sensor
       └─ outputs CSV rows over serial (9600 baud)
            └─ Python pipeline reads serial → preprocesses → ML inference
                 └─ Streamlit dashboard displays live results

mmWave Radar (IWR/AWR)
  └─ cfg_port (COM5) + data_port (COM3)
       └─ radar_comdata.py streams radar detections
            └─ fused with VOC pipeline in dashboard
```

No wireless communication. No cloud dependency. Everything runs locally.

---

## Hardware

| Component | Role |
|---|---|
| TI TMS320F28379D (C2000 DSP) | MCU — reads sensors, outputs serial CSV |
| MQ3 | Alcohol / baseline VOC sensor |
| MQ135 | Air quality / ammonia — primary fly indicator |
| MQ138 | Organic solvent VOCs |
| MQ131 | Ozone |
| TGS2602 | Air contaminants / odor — primary fly indicator |
| BME280 | Temperature, humidity, pressure (environmental context) |
| TI mmWave Radar (IWR/AWR series) | Motion detection — physical fly presence |

---

## ML Pipeline

The classifier is a **Random Forest** (scikit-learn) trained on labeled sensor recordings across five categories:

- `clean_air`
- `clean_banana`
- `clean_tomato`
- `infected_banana`
- `infected_tomato`

### Key design decisions

- **Ratio features** (e.g. `MQ135/MQ3`, `TGS2602/MQ3`, `TGS2602/MQ135`) cancel session-to-session environmental drift, making the model more robust across different days and conditions.
- **`class_weight="balanced"`** handles the natural ~10:1 imbalance between clean and infected samples.
- **Leave-one-file-out cross-validation** is used during training to evaluate generalization on a small dataset.
- The trained model is saved as `fly_model.pkl` and tracked in Git so collaborators can run inference without retraining.

### Training

```bash
python train_model.py
```

This auto-discovers all labeled CSVs under `data/training/` and writes `fly_model.pkl` to the project root.

---

## Project Structure

```
no-fly-zone/
├── comdata.py            # Serial reader — streams MCU output to CSV
├── radar_comdata.py      # Radar reader — streams mmWave detections
├── parser.py             # Parses raw serial CSV rows
├── preprocess.py         # Feature engineering (ratios, normalization)
├── model.py              # Loads fly_model.pkl, runs per-row inference
├── train_model.py        # Trains and saves the Random Forest model
├── gui.py                # Streamlit dashboard
├── serial_monitor.py     # Standalone serial debug utility
├── fly_model.pkl         # Trained model (tracked in Git)
├── requirements.txt
├── CLAUDE.md             # Project context for AI-assisted development
└── data/
    └── training/
        ├── clean_air/
        ├── clean_banana/
        ├── clean_tomato/
        ├── infected_banana/
        └── infected_tomato/
```

---

## Setup

### Prerequisites

- Python 3.10+
- TI Code Composer Studio (for firmware, if re-flashing the MCU)
- A connected TMS320F28379D over USB serial
- TI mmWave radar module (IWR/AWR series), flashed and connected over USB

### Install dependencies

```bash
# Windows
py -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

> **Note:** Keep the repo outside OneDrive-synced folders. OneDrive file locking causes permission errors with `venv/`.

The system runs as **three separate terminal windows**.

---

### Terminal 1 — VOC sensor stream

This is the core data pipeline. `comdata.py` reads CSV rows from the MCU over serial and writes them to disk for the ML model to consume. This terminal requires the virtual environment activated.

```bash
# Activate venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

python comdata.py
```

Leave this running. It must be active for the dashboard to receive live data.

---

### Terminal 2 — Streamlit dashboard

```bash
streamlit run gui.py
```

Opens the live dashboard in your browser. Reads from the data file that `comdata.py` is writing.

---

### Terminal 3 — Radar stream

```bash
python radar_comdata.py --cfg_port COM5 --data_port COM3 --no-config
```

- `--cfg_port` — serial port for radar configuration (typically COM5)
- `--data_port` — serial port for radar detections (typically COM3)
- `--no-config` — skips sending the config profile; use if the radar is already configured

> **Flashing the radar:** Use the [TI mmWave Demo Visualizer](https://dev.ti.com/gallery/view/mmwave/mmWave_Demo_Visualizer/ver/3.6.0/) to flash firmware and generate a config profile for your radar module.

---

## Firmware

The embedded VOC firmware runs on the TI TMS320F28379D and is developed in **TI Code Composer Studio** using the C2000 driverlib. It reads all five gas sensors and the BME280 via the configured SCI serial peripheral, then outputs a CSV-formatted row at 9600 baud for each sample. Firmware configuration is managed via `.syscfg`.

The mmWave radar firmware is flashed separately using the TI mmWave Demo Visualizer (see link above).

---

## Branch Structure

| Branch | Owner | Purpose |
|---|---|---|
| `main` | Aidan | Protected — stable releases only |
| `aidan-dev` | Aidan | Primary development branch |
| `kp-branch` | KP | mmWave radar integration |

---

## Roadmap

- [x] Five-sensor VOC array + BME280 environmental sensor
- [x] Serial CSV pipeline (MCU → Python)
- [x] Random Forest classifier with ratio features
- [x] Real-time Streamlit dashboard with confidence display
- [x] mmWave radar data stream (`radar_comdata.py`)
- [ ] Replace synthetic training data with real infected produce recordings
- [ ] Fuse radar detections with VOC classifications in dashboard
- [ ] Expanded produce categories and field validation

---

## Requirements

```
pyserial
pandas
numpy
scikit-learn
streamlit
plotly
```

See `requirements.txt` for pinned versions.

---

## License

For academic and research use. Contact the author for other uses.
