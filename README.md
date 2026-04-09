# No-Fly-Zone

A fly detection system using an array of gas sensors connected to a TI TMS320F283790 C2000 DSP. Sensor data is read over serial, processed through a Python pipeline, and displayed on a real-time Streamlit dashboard.

## Requirements

- Python 3.10+
- MCU connected via USB (note your COM port)

## Setup

1. Clone the repository:
git clone https://github.com/AidanB21/no-fly-zone.git |
cd no-fly-zone

2. Create a virtual environment and activate it:
py -m venv venv |
venv\Scripts\activate

3. Install dependencies:
pip install -r requirements.txt

### Terminal 1 — Start the serial data logger
python comdata.py

### Terminal 2 — Launch the dashboard
streamlit run gui.py


