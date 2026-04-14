# No-Fly-Zone 🪰

A real-time fly detection system that uses a VOC gas sensor array, a DSP microcontroller, and a machine learning classifier to identify fly infestations in produce — before visible damage occurs.
Built as a senior capstone project.


## Overview

//Coming Soon

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
├── comdata.py          # Serial reader — streams MCU output to CSV
├── parser.py           # Parses raw serial CSV rows
├── preprocess.py       # Feature engineering (ratios, normalization)
├── model.py            # Loads fly_model.pkl, runs per-row inference
├── train_model.py      # Trains and saves the Random Forest model
├── gui.py              # Streamlit dashboard
├── serial_monitor.py   # Standalone serial debug utility
├── fly_model.pkl       # Trained model (tracked in Git)
├── requirements.txt
├── CLAUDE.md           # Project context for AI-assisted development
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

### Run the dashboard

```bash
streamlit run gui.py
```

### Stream live sensor data

```bash
python comdata.py
```

This opens the serial port, reads CSV rows from the MCU at 9600 baud, and appends them to the active data file.

---

## Firmware

The embedded firmware runs on the TI TMS320F28379D and is developed in **TI Code Composer Studio** using the C2000 driverlib. It reads all five gas sensors and the BME280 via the configured SCI serial peripheral, then outputs a CSV-formatted row at 9600 baud for each sample.

Firmware configuration is managed via `.syscfg`.



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
