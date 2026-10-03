"""Dataset access (section 3, section 6 decoding). Never called in Stage 1 except for label files (AT-14).

Expected layout under the dataset root (TSF_ROOT):
  CSV/<scenario>.csv           columns FileName, Label (FileName says .png; files on disk are .jpeg)
  IMAGE/<scenario>/<index>.*   one image per frame, index = 1..N_s from the filename stem
"""
import glob
import os
import re

import numpy as np
import pandas as pd

KAGGLE_DEFAULT = "/kaggle/input/datasets/tinonturjamajumder/fabric-defect-dataset/TSfabrics"


def find_root(root=None):
    for cand in (root, os.environ.get("TSF_ROOT"), KAGGLE_DEFAULT):
        if cand and os.path.isdir(os.path.join(cand, "CSV")):
            return cand
    if os.path.isdir("/kaggle/input"):
        for base, dirs, _ in os.walk("/kaggle/input"):
            if "CSV" in dirs and "IMAGE" in dirs:
                return base
            if base.count(os.sep) > 8:
                dirs[:] = []
    return None


def load_labels(root, scenario):
    """Per-frame integer labels, index 0 = frame 1. Raises if frame indices are not exactly 1..N."""
    df = pd.read_csv(os.path.join(root, "CSV", f"{scenario}.csv"), dtype=str)
    df.columns = [c.strip() for c in df.columns]
    idx = df["FileName"].str.strip().str.extract(r"(\d+)")[0].astype(int).to_numpy()
    lab = df["Label"].astype(int).to_numpy()
    order = np.argsort(idx, kind="stable")
    idx, lab = idx[order], lab[order]
    if not np.array_equal(idx, np.arange(1, len(idx) + 1)):
        raise ValueError(f"{scenario}: frame indices are not 1..N")
    return lab


def image_paths(root, scenario):
    files = [f for f in glob.glob(os.path.join(root, "IMAGE", scenario, "**", "*"), recursive=True)
             if os.path.isfile(f)]
    by_idx = {}
    for f in files:
        m = re.fullmatch(r"(\d+)", os.path.splitext(os.path.basename(f))[0])
        if m:
            by_idx[int(m.group(1))] = f
    n = len(by_idx)
    if sorted(by_idx) != list(range(1, n + 1)):
        raise ValueError(f"{scenario}: image indices are not 1..N")
    return [by_idx[i] for i in range(1, n + 1)]


def read_gray(path):
    """Section 6: cv2.imread(path, cv2.IMREAD_GRAYSCALE) -> uint8 [640, 800]."""
    import cv2
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None or img.shape != (640, 800):
        raise ValueError(f"unexpected image {path}: {None if img is None else img.shape}")
    return img


def defect_frames(labels, scenario, override):
    """1-based defect frames (labels 3-9) plus the forensic override (frames labelled 1 with a defect mask)."""
    d = set((np.flatnonzero(labels >= 3) + 1).tolist())
    if scenario in override:
        a, b = override[scenario]
        d |= set(range(a, b + 1))
    return sorted(d)
