"""
No-Fly-Zone ML Training Pipeline
Reads all .txt files from data/training/ subfolders.
Folder name determines the label:
  clean_air, clean_banana, clean_tomato -> class 0 (no fly)
  infected_banana, infected_tomato      -> class 1 (fly present)

Run:  py train_model.py
Output: fly_model.pkl
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import LeaveOneGroupOut, cross_val_predict
from sklearn.metrics import classification_report, confusion_matrix
import pickle

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data" / "training"
SENSORS = ["MQ3", "MQ135", "MQ138", "MQ131", "TGS2602"]

CLEAN_FOLDERS = ["clean_air", "clean_banana", "clean_tomato"]
INFECTED_FOLDERS = ["infected_banana", "infected_tomato"]


def parse_file(filepath):
    rows = []
    for line in filepath.read_text().splitlines():
        line = line.strip().replace("\r", "")
        if not line or line.startswith("=~"):
            continue
        parts = line.split(",")
        if len(parts) >= 5:
            try:
                rows.append([int(parts[i]) for i in range(5)])
            except ValueError:
                continue
    return rows


def build_dataset():
    all_rows = []
    for folder_name in CLEAN_FOLDERS + INFECTED_FOLDERS:
        folder = DATA_DIR / folder_name
        if not folder.exists():
            print(f"  WARNING: {folder} not found, skipping")
            continue
        label = 0 if folder_name in CLEAN_FOLDERS else 1
        for f in sorted(folder.glob("*.txt")):
            parsed = parse_file(f)
            for vals in parsed:
                all_rows.append(vals + [folder_name, label, f.name])
            print(f"  {folder_name}/{f.name}: {len(parsed)} rows (class {label})")
    return pd.DataFrame(all_rows, columns=SENSORS + ["condition", "label", "source"])


def add_features(df):
    df = df.copy()
    df["MQ135_MQ3"] = df["MQ135"] / df["MQ3"]
    df["TGS_MQ3"] = df["TGS2602"] / df["MQ3"]
    df["TGS_MQ135"] = df["TGS2602"] / df["MQ135"]
    return df


def train_and_evaluate(df):
    feat_cols = SENSORS + ["MQ135_MQ3", "TGS_MQ3", "TGS_MQ135"]
    X = df[feat_cols].values
    y = df["label"].values
    groups = df["source"].astype("category").cat.codes.values

    rf = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
    )

    logo = LeaveOneGroupOut()
    y_pred = cross_val_predict(rf, X, y, groups=groups, cv=logo)

    print("\n=== Leave-One-File-Out CV ===\n")
    print(classification_report(y, y_pred, target_names=["Clean", "Infected"]))
    cm = confusion_matrix(y, y_pred)
    print(f"  TN={cm[0,0]}  FP={cm[0,1]}")
    print(f"  FN={cm[1,0]}  TP={cm[1,1]}")

    rf.fit(X, y)
    print("\nFeature Importances:")
    for name, imp in sorted(zip(feat_cols, rf.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name:12s} {imp:.3f}")
    return rf, feat_cols


if __name__ == "__main__":
    print("Scanning data/training/ ...\n")
    df = build_dataset()
    clean = (df["label"] == 0).sum()
    infected = (df["label"] == 1).sum()
    print(f"\nTotal: {len(df)} rows  |  Clean: {clean}  |  Infected: {infected}")

    df = add_features(df)
    model, feat_cols = train_and_evaluate(df)

    out = BASE_DIR / "fly_model.pkl"
    with open(out, "wb") as f:
        pickle.dump({"model": model, "features": feat_cols}, f)
    print(f"\nModel saved to {out}")