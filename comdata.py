import os
import serial
import csv
import sys
from datetime import datetime
from collections import deque
import matplotlib.pyplot as plt
import matplotlib.animation as animation


# ── Configuration ──────────────────────────────────────────────────
COM_PORT = "COM4"              # change to match your system (e.g., COM4, /dev/ttyUSB0)
BAUD_RATE = 9600
TIMEOUT = 1                    # seconds to wait for a line before giving up

SENSOR_COLUMNS = ["MQ3", "MQ135", "MQ138", "MQ131", "TGS2602"]

BUFFER_SIZE = 200              # number of recent readings shown on the plot
UPDATE_INTERVAL_MS = 100       # how often the plot refreshes


# ── CSV Log Setup ──────────────────────────────────────────────────
os.makedirs("data/sensor_data", exist_ok=True)
log_filename = "data/sensor_data/sensor_log.csv"
log_file = open(log_filename, "w", newline="")
log_writer = csv.writer(log_file)
log_writer.writerow(["Timestamp"] + SENSOR_COLUMNS)
print(f"Logging to: {log_filename}")


# ── Serial Port ────────────────────────────────────────────────────
try:
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
    print(f"Connected to {COM_PORT} at {BAUD_RATE} baud")
except serial.SerialException as e:
    print(f"Could not open {COM_PORT}: {e}")
    log_file.close()
    sys.exit(1)


# ── Data Buffers ───────────────────────────────────────────────────
# one deque per column — oldest values drop off automatically
buffers = {col: deque(maxlen=BUFFER_SIZE) for col in SENSOR_COLUMNS}
time_axis = deque(maxlen=BUFFER_SIZE)  # x-axis: sequential sample index
sample_count = 0


# ── Parse One CSV Line ─────────────────────────────────────────────
def parse_line(raw_line):
    """Convert a raw serial line into a list of floats.
    Returns None if the line is malformed or has the wrong number of fields."""
    raw_line = raw_line.strip()
    if not raw_line:
        return None

    parts = raw_line.split(",")
    if len(parts) < len(SENSOR_COLUMNS):
        return None

    try:
        return [float(v) for v in parts[:len(SENSOR_COLUMNS)]]
    except ValueError:
        return None


# ── Read All Waiting Lines ─────────────────────────────────────────
def read_available_lines():
    """Read and parse every complete line currently in the serial buffer."""
    global sample_count
    while ser.in_waiting:
        try:
            raw = ser.readline().decode("utf-8", errors="replace")
        except serial.SerialException:
            break

        values = parse_line(raw)
        if values is None:
            continue

        # log to CSV with a timestamp
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_writer.writerow([now] + values)
        log_file.flush()

        # push into plot buffers
        sample_count += 1
        time_axis.append(sample_count)
        for col, val in zip(SENSOR_COLUMNS, values):
            buffers[col].append(val)


# ── Plot Setup ─────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
fig.suptitle("No-Fly-Zone — Live Gas Sensor Monitor", fontsize=14, fontweight="bold")

gas_lines = {}
for name in SENSOR_COLUMNS:
    line, = ax.plot([], [], label=name, linewidth=1.2)
    gas_lines[name] = line

ax.set_xlabel("Sample")
ax.set_ylabel("ADC / Sensor Value")
ax.legend(loc="upper left", fontsize=8)
ax.grid(True, alpha=0.3)

plt.tight_layout()


# ── Animation Callback ─────────────────────────────────────────────
def update(frame):
    """Called every UPDATE_INTERVAL_MS — reads new data and redraws lines."""
    read_available_lines()

    if len(time_axis) == 0:
        return

    x = list(time_axis)

    for name, line in gas_lines.items():
        line.set_data(x, list(buffers[name]))

    ax.relim()
    ax.autoscale_view()


# ── Run ────────────────────────────────────────────────────────────
ani = animation.FuncAnimation(fig, update, interval=UPDATE_INTERVAL_MS, cache_frame_data=False)

try:
    print("Monitoring... press Ctrl+C to stop.")
    plt.show()
except KeyboardInterrupt:
    pass
finally:
    ser.close()
    log_file.close()
    print(f"\nStopped. Log saved to {log_filename}")