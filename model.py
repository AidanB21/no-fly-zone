import pandas as pd

SENSOR_COLUMNS = ['MQ3', 'MQ135', 'MQ138', 'MQ131', 'TGS2602']

DEFAULT_THRESHOLDS = {
    'MQ3': 50,
    'MQ135': 100,
    'MQ138': 20,
    'MQ131': 50,
    'TGS2602': 100
}


def threshold_detect(df, thresholds=None, min_sensors=2):
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    detections = pd.DataFrame()
    detections['sample'] = df.index

    sensor_flags = pd.DataFrame()
    for sensor in SENSOR_COLUMNS:
        dist_col = f"{sensor}_dist"
        if dist_col in df.columns:
            sensor_flags[sensor] = df[dist_col] > thresholds[sensor]

    detections['sensors_triggered'] = sensor_flags.sum(axis=1)
    detections['fly_detected'] = detections['sensors_triggered'] >= min_sensors

    detections['MQ3_value'] = df['MQ3'].values
    detections['MQ131_value'] = df['MQ131'].values
    detections['TGS2602_value'] = df['TGS2602'].values

    return detections


def get_detection_summary(detections):
    total_samples = len(detections)
    fly_samples = detections['fly_detected'].sum()
    fly_percentage = (fly_samples / total_samples) * 100 if total_samples > 0 else 0

    if fly_samples == 0:
        regions = []
    else:
        regions = []
        in_event = False
        start = 0
        for i, row in detections.iterrows():
            if row['fly_detected'] and not in_event:
                start = row['sample']
                in_event = True
            elif not row['fly_detected'] and in_event:
                end = detections.iloc[i - 1]['sample']
                regions.append((start, end))
                in_event = False
        if in_event:
            regions.append((start, detections.iloc[-1]['sample']))

    summary = {
        'total_samples': total_samples,
        'fly_samples': fly_samples,
        'fly_percentage': round(fly_percentage, 2),
        'detection_regions': regions,
        'num_events': len(regions)
    }
    return summary


def predict(df, thresholds=None, min_sensors=2):
    detections = threshold_detect(df, thresholds, min_sensors)
    summary = get_detection_summary(detections)
    return detections, summary


if __name__ == "__main__":
    from parser import load_sensor_data
    from preprocess import preprocess_data

    sensor_data_path = "data/sample_sensorData.txt"
    raw_df = load_sensor_data(sensor_data_path)
    processed_df = preprocess_data(raw_df)

    detections, summary = predict(processed_df)

    print(f"Total samples: {summary['total_samples']}")
    print(f"Fly detected in: {summary['fly_samples']} samples ({summary['fly_percentage']}%)")
    print(f"Number of events: {summary['num_events']}")
    print(f"Detection regions: {summary['detection_regions']}")