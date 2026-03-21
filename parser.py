import pandas as pd

sensor_data_path = "data/sample_sensorData.txt"
def load_sensor_data(filepath):
    sensor_readings = []
    
    with open(filepath, 'r') as file:
        for line in file:
            line = line.strip()
            if not line:
                continue
            row = {}
            pairs = line.split(', ')
            for pair in pairs:
                name, value = pair.split(':')
                row[name] = int(value)
            sensor_readings.append(row)
            df = pd.DataFrame(sensor_readings)
    return df

if __name__ == "__main__":
    df = load_sensor_data(sensor_data_path)
    print(df.head())
    print(f"\nTotal readings: {len(df)}")