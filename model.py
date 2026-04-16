"""
No-Fly-Zone ML Inference
Loads fly_model.pkl and classifies live sensor readings.
Called by the pipeline (gui.py / main.py) for each new sensor row.
"""

import pickle
import numpy as np
from pathlib import Path

BASE_DIR = Path(__file__).parent
MODEL_PATH = BASE_DIR / "fly_model.pkl"

# Load model once at import time
_model_data = None
_model = None
_features = None

def _load_model():
    global _model_data, _model, _features
    if _model is not None:
        return
    if not MODEL_PATH.exists():
        print(f"WARNING: {MODEL_PATH} not found. Run train_model.py first.")
        return
    with open(MODEL_PATH, "rb") as f:
        _model_data = pickle.load(f)
    _model = _model_data["model"]
    _features = _model_data["features"]
    print(f"Model loaded from {MODEL_PATH}")

_load_model()


def predict(mq3, mq135, mq138, mq131, tgs2602):
    """
    Classify a single sensor reading.
    Returns: (label, confidence)
        label: 0 = clean, 1 = infected (fly detected)
        confidence: probability of the predicted class (0.0 to 1.0)
    """
    if _model is None:
        return 0, 0.0

    # Build feature array with ratios (must match train_model.py's add_features())
    mq135_mq3 = mq135 / mq3 if mq3 > 0 else 0
    tgs_mq3 = tgs2602 / mq3 if mq3 > 0 else 0
    tgs_mq135 = tgs2602 / mq135 if mq135 > 0 else 0
    sensor_max = max(mq3, mq135, mq138, mq131, tgs2602)
    sensor_sum = mq3 + mq135 + mq138 + mq131 + tgs2602
    tgs_share = tgs2602 / sensor_sum if sensor_sum > 0 else 0

    X = np.array([[mq3, mq135, mq138, mq131, tgs2602,
                   mq135_mq3, tgs_mq3, tgs_mq135,
                   sensor_max, sensor_sum, tgs_share]])

    proba = _model.predict_proba(X)[0]
    fly_prob = proba[1]

    # Lower threshold (0.3) so borderline VOC spikes still trigger detection
    label = 1 if fly_prob >= 0.3 else 0
    confidence = fly_prob if label == 1 else proba[0]

    return int(label), float(confidence)


def predict_row(row_values):
    """
    Classify from a list/array of 5 raw sensor values.
    Convenience wrapper for predict().
    """
    if len(row_values) < 5:
        return 0, 0.0
    return predict(row_values[0], row_values[1], row_values[2],
                   row_values[3], row_values[4])


def predict_batch(df, sensor_cols):
    """
    Classify an entire DataFrame in one vectorized call.
    Much faster than calling predict_row() in a loop.
    Returns: (labels list, confidences list)
    """
    if _model is None:
        n = len(df)
        return [0] * n, [0.0] * n

    mq3    = df[sensor_cols[0]].values.astype(float)
    mq135  = df[sensor_cols[1]].values.astype(float)
    mq138  = df[sensor_cols[2]].values.astype(float)
    mq131  = df[sensor_cols[3]].values.astype(float)
    tgs    = df[sensor_cols[4]].values.astype(float)

    mq135_mq3  = np.where(mq3  > 0, mq135 / mq3,  0)
    tgs_mq3    = np.where(mq3  > 0, tgs   / mq3,  0)
    tgs_mq135  = np.where(mq135 > 0, tgs  / mq135, 0)
    sensor_max = np.stack([mq3, mq135, mq138, mq131, tgs], axis=1).max(axis=1)
    sensor_sum = mq3 + mq135 + mq138 + mq131 + tgs
    tgs_share  = np.where(sensor_sum > 0, tgs / sensor_sum, 0)

    X = np.column_stack([mq3, mq135, mq138, mq131, tgs,
                         mq135_mq3, tgs_mq3, tgs_mq135,
                         sensor_max, sensor_sum, tgs_share])

    proba       = _model.predict_proba(X)
    fly_probs   = proba[:, 1]
    labels      = (fly_probs >= 0.3).astype(int).tolist()
    confidences = np.where(fly_probs >= 0.3, fly_probs, proba[:, 0]).tolist()

    return labels, confidences


def reload_model():
    """Re-read fly_model.pkl from disk (call after retraining)."""
    global _model, _features, _model_data
    _model = None
    _features = None
    _model_data = None
    _load_model()


def get_status_text(label, confidence):
    """Return a human-readable status string for the GUI."""
    if label == 1:
        return f"FLY DETECTED ({confidence:.0%} confidence)"
    return f"Clean ({confidence:.0%} confidence)"