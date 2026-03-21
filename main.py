"""
PSEUDOCODE
1. Import needed modules (csv, random, datetime, pathlib).
2. Define output path for CSV.
4. Open CSV file and write header: timestamp, sensor_value.
5. Loop for each sample:
   - create timestamp (start time + sample index in seconds)
   - generate fake sensor value (baseline + random noise)
   - keep value in valid ADC range (0-1023)
   - write row to CSV.
6. Print completion message with file path.
"""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt


def generate_single_sensor_csv(
    output_csv: Path,
    sensor_name: str = "mq135",
    num_samples: int = 120,
    baseline: int = 350,
    noise_range: int = 25,
    spike_probability: float = 0.08,
    spike_min_value: int = 650,
    spike_max_value: int = 900,
) -> None:
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    start_time = datetime.now().replace(microsecond=0)

    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", sensor_name])

        for i in range(num_samples):
            timestamp = start_time + timedelta(seconds=i)
            if random.random() < spike_probability:
                value = random.randint(spike_min_value, spike_max_value)
            else:
                value = baseline + random.randint(-noise_range, noise_range)
            value = max(0, min(1023, value))
            writer.writerow([timestamp.isoformat(), value])

    print(f"Saved {num_samples} rows to: {output_csv}")


def detect_spikes_in_csv(
    input_csv: Path,
    sensor_name: str = "mq135",
    spike_threshold: int = 500,
    spike_delta: int = 150,
) -> None:
    if not input_csv.exists():
        raise FileNotFoundError(f"CSV not found: {input_csv}")

    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        previous_value: Optional[int] = None

        for row in reader:
            timestamp = row.get("timestamp", "").strip()
            raw_value = row.get(sensor_name, "")
            if raw_value == "":
                continue

            value = int(raw_value)
            is_spike = value >= spike_threshold
            if previous_value is not None:
                is_spike = is_spike or (value - previous_value >= spike_delta)

            if is_spike:
                print(f"Flies detected at {timestamp} (value={value})")

            previous_value = value


def plot_sensor_csv(input_csv: Path, sensor_name: str = "mq135") -> None:
    if not input_csv.exists():
        raise FileNotFoundError(f"CSV not found: {input_csv}")

    timestamps = []
    values = []

    with input_csv.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_ts = row.get("timestamp", "").strip()
            raw_value = row.get(sensor_name, "")
            if raw_ts == "" or raw_value == "":
                continue
            timestamps.append(datetime.fromisoformat(raw_ts))
            values.append(int(raw_value))

    if not values:
        print(f"No data found in {input_csv}")
        return

    plt.figure(figsize=(10, 4))
    plt.plot(timestamps, values, marker="o", linewidth=1.2)
    plt.title(f"{sensor_name} readings")
    plt.xlabel("Time")
    plt.ylabel("Sensor value")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    random.seed(42)
    output_path = Path("data/single_sensor_fake.csv")
    generate_single_sensor_csv(output_path)
    detect_spikes_in_csv(output_path)
    plot_sensor_csv(output_path)
