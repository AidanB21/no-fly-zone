"""
No-Fly-Zone Radar Motion Inference
====================================
Loads radar_model.pkl and classifies individual radar frames as
"still" (0) or "motion detected" (1).

Called by gui.py for each new radar frame, alongside the gas sensor model.
"""

import pickle
from pathlib import Path

import numpy as np

BASE_DIR   = Path(__file__).parent
MODEL_PATH = BASE_DIR / "radar_model.pkl"

_model     = None
_threshold = None
_features  = None


def _load_model():
    global _model, _threshold, _features
    if _model is not None:
        return
    if not MODEL_PATH.exists():
        return
    with open(MODEL_PATH, "rb") as f:
        data = pickle.load(f)
    _model     = data["model"]
    _threshold = data["threshold"]
    _features  = data["features"]


_load_model()


def predict_radar(micro_doppler, peak_velocity, num_objects):
    """
    Classify a single radar frame.

    Returns: (label, score)
        label: 0 = still/no motion, 1 = motion detected
        score: IsolationForest anomaly score (lower = more anomalous)
    """
    if _model is None:
        return 0, 0.0

    X     = np.array([[micro_doppler, peak_velocity, num_objects]])
    score = float(_model.decision_function(X)[0])
    label = 1 if score < _threshold else 0

    return label, score


def radar_model_loaded():
    """Returns True if radar_model.pkl has been loaded successfully."""
    return _model is not None


def reload_model():
    """Re-read radar_model.pkl from disk (call after retraining)."""
    global _model, _threshold, _features
    _model = _threshold = _features = None
    _load_model()
