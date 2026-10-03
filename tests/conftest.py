"""Shared fixtures. Tests may import reference/ and calibration/ (src/ never does)."""
import math
import os
import sys

import numpy as np
import pandas as pd
import pytest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(REPO, "src"))
REF = os.path.join(REPO, "reference")
CAL = os.path.join(REPO, "calibration", "c0b")

from tsfpilot import config as C            # noqa: E402
from tsfpilot.passes import build_layout     # noqa: E402

CFG = C.load()
PASSES = pd.read_csv(C.repo_path(CFG["data"]["passes_csv"]))
SUMMARY = pd.read_csv(C.repo_path(CFG["data"]["forensic_summary_csv"]))
NS = dict(zip(SUMMARY.scenario, SUMMARY.n_csv.astype(int)))
DXMED = dict(zip(SUMMARY.scenario, SUMMARY.dx_med.astype(float)))


def import_ref(name):
    if REF not in sys.path:
        sys.path.insert(0, REF)
    return __import__(name)


def median_k(scenario):
    """Scenario-median k used by the v1.2 estimates (sections 11, 19); not the Stage 3 K_t."""
    return min(25, max(3, math.floor(800 / abs(DXMED[scenario]) + 0.5)))


def synthetic_labels(scenario):
    """Label 4 inside every pass's [start, end], label 1 elsewhere. Gives the same N_f as the real labels for the
    pilot test scenarios (every defect frame lies inside a pass; labels 1 and 2 are both normal)."""
    lab = np.ones(NS[scenario], np.int64)
    for r in PASSES[PASSES.scenario == scenario].itertuples():
        lab[r.pass_start - 1:r.pass_end] = 4
    return lab


def synthetic_layout(fold, k_mode="median"):
    names = CFG["folds"][fold]["test"]
    labels = {s: synthetic_labels(s) for s in names}
    K = {}
    for s in names:
        k = median_k(s)
        K[s] = np.minimum(np.full(NS[s], k), np.arange(1, NS[s] + 1))
    return build_layout(fold, CFG, PASSES, labels, K)


@pytest.fixture(scope="session")
def cfg():
    return CFG


@pytest.fixture(scope="session")
def layouts():
    return {f: synthetic_layout(f) for f in ("A-G1", "A-G4")}
