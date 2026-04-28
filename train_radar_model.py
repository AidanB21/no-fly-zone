"""
No-Fly-Zone Radar Motion Model
================================
Learns what the radar environment looks like with NO movement (i.e. just
the gas sensors and background clutter sitting still during calibration).
Then flags anything that deviates significantly as motion detected.

Key insight: the radar always sees objects (gas sensors, enclosure, etc.)
so the model is NOT trained on "zero objects = still". It is trained on
the actual baseline readings from the 30-second calibration window, so
it learns *this specific environment's* normal fingerprint and only flags
deviations above that.

Model: IsolationForest (unsupervised, clean-only training).
Features: micro_doppler, peak_velocity, num_objects
Output: radar_model.pkl

Called automatically by gui.py after calibration, passing --since so only
the calibration window rows are used (not the full radar history).

Manual usage:
    python train_radar_model.py --since "2026-04-14 13:00:00"
    python train_radar_model.py  # uses all rows (fallback)
"""

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

BASE_DIR    = Path(__file__).parent
DEFAULT_CSV = BASE_DIR / "data" / "sensor_data" / "radar_log.csv"
MODEL_OUT   = BASE_DIR / "radar_model.pkl"

RADAR_FEATURES = ["micro_doppler", "peak_velocity", "num_objects"]


def load_radar_csv(path, since=None):
    df = pd.read_csv(path)
    if df.empty:
        print(f"[!] {path} is empty — no radar data to train on.")
        sys.exit(1)
    missing = [c for c in RADAR_FEATURES if c not in df.columns]
    if missing:
        print(f"[!] CSV is missing columns: {missing}")
        sys.exit(1)

    # Filter to only the calibration window if a timestamp was provided
    if since and "Timestamp" in df.columns:
        df["Timestamp"] = pd.to_datetime(df["Timestamp"], errors="coerce")
        since_dt = pd.to_datetime(since)
        cal_df = df[df["Timestamp"] >= since_dt]
        if len(cal_df) >= 5:
            print(f"    Using {len(cal_df)} rows from calibration window "
                  f"(since {since}), discarding {len(df) - len(cal_df)} earlier rows")
            return cal_df
        else:
            print(f"    WARNING: Only {len(cal_df)} rows in calibration window — "
                  f"using all {len(df)} rows as fallback")

    return df


def train(df):
    """
    Train an IsolationForest on calibration (still/no-movement) radar frames.

    contamination=0.05 allows up to 5% of the calibration data to be
    treated as noise without polluting the baseline boundary.

    The threshold is derived from the calibration scores themselves:
    mean - 2*std means only readings significantly outside normal variation
    will be flagged — ordinary sensor noise won't trigger a detection.
    """
    X = df[RADAR_FEATURES].fillna(0).values

    model = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42,
    )
    model.fit(X)

    scores    = model.decision_function(X)
    threshold = float(np.mean(scores) - 2 * np.std(scores))

    print(f"  Trained on {len(X)} calibration radar frames")
    print(f"  Baseline µ-doppler: {df['micro_doppler'].mean():+.4f} m/s  "
          f"(std {df['micro_doppler'].std():.4f})")
    print(f"  Baseline objects:   {df['num_objects'].mean():.1f} avg")
    print(f"  Score range: [{scores.min():.4f}, {scores.max():.4f}]")
    print(f"  Motion threshold:   {threshold:.4f}  "
          f"(scores below this = motion detected)")

    return model, threshold


def main():
    ap = argparse.ArgumentParser(description="Train the radar motion baseline model")
    ap.add_argument("--csv",   default=str(DEFAULT_CSV),
                    help=f"Radar CSV path (default: {DEFAULT_CSV})")
    ap.add_argument("--since", default=None,
                    help='Only use rows at or after this timestamp '
                         '(e.g. "2026-04-14 13:00:00"). '
                         'Pass the calibration start time so only the '
                         '30-second window is used, not prior history.')
    ap.add_argument("--out",   default=str(MODEL_OUT),
                    help=f"Output .pkl path (default: {MODEL_OUT})")
    args = ap.parse_args()

    print(f"\n[*] Loading radar data: {args.csv}")
    df = load_radar_csv(args.csv, since=args.since)
    print(f"    {len(df)} frames will be used for training")

    print("[*] Training IsolationForest on calibration radar frames ...")
    model, threshold = train(df)

    out = Path(args.out)
    with open(out, "wb") as f:
        pickle.dump({
            "model":     model,
            "threshold": threshold,
            "features":  RADAR_FEATURES,
        }, f)
    print(f"[*] Radar model saved to: {out}\n")


if __name__ == "__main__":
    main()
