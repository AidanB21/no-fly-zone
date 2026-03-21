import pandas as pd

# Default baseline values - can be updated from GUI later
DEFAULT_BASELINE = {
    'MQ3': 170,
    'MQ135': 1960,
    'MQ138': 3010,
    'MQ131': 1095,
    'TGS2602': 850
}

SENSOR_COLUMNS = ['MQ3', 'MQ135', 'MQ138', 'MQ131', 'TGS2602']


def clean_data(df):
    """Remove rows where sensors are off (zero values)."""
    cleaned = df.copy()
    cleaned = cleaned[(cleaned['MQ3'] > 5) & (cleaned['TGS2602'] > 5)]
    cleaned = cleaned.reset_index(drop=True)
    return cleaned


def add_rolling_average(df, window=5):
    """Smooth out sensor noise using a rolling average."""
    for sensor in SENSOR_COLUMNS:
        col_name = f"{sensor}_rolling"
        df[col_name] = df[sensor].rolling(window=window, min_periods=1).mean()
    return df


def add_rate_of_change(df):
    """Calculate how much each sensor changes between readings."""
    for sensor in SENSOR_COLUMNS:
        col_name = f"{sensor}_roc"
        df[col_name] = df[sensor].diff().fillna(0)
    return df


def add_distance_from_baseline(df, baseline=None):
    """Measure how far each sensor is from its normal baseline."""
    if baseline is None:
        baseline = DEFAULT_BASELINE
    for sensor in SENSOR_COLUMNS:
        col_name = f"{sensor}_dist"
        df[col_name] = df[sensor] - baseline[sensor]
    return df


def preprocess_data(df, baseline=None, window=5):
    """Run all preprocessing steps in order."""
    df = clean_data(df)
    df = add_rolling_average(df, window)
    df = add_rate_of_change(df)
    df = add_distance_from_baseline(df, baseline)
    return df


if __name__ == "__main__":
    from parser import load_sensor_data

    sensor_data_path = "data/sample_sensorData.txt"
    raw_df = load_sensor_data(sensor_data_path)
    print(f"Raw data: {len(raw_df)} rows")

    processed_df = preprocess_data(raw_df)
    print(f"Cleaned data: {len(processed_df)} rows")
    print(f"\nColumns: {list(processed_df.columns)}")
    print(f"\nFirst 5 rows:")
    print(processed_df.head())