"""Validation constants per fold and coreset seed (section 8 "Per-seed constants"; sections 9, 10, 16; DL-0013).

maps: the (1212, 80, 100) float32 anomaly maps of T1_S164_I199_1 under one (fold, seed) coreset.

  mu0       mean of a_t over all cells of all validation frames (section 9), accumulated in float64
  b1, b3    per-cell means of a_t and of its 3 x 3 border-clipped maximum (section 16)
  tau_cell  99.9th percentile of a_t over all cells of all validation frames, numpy 'linear' (v1.1 A12; DL-0013)
  profile   column means of b1, the label-free left-right check of section 10
  deployment thresholds  per variant, the section 14 tau_2 rule on the validation timeline (v1.1 A10; DL-0013)
"""
import numpy as np

from .decomposition import baselines
from .events import count_curve
from .variants import NAMES, scenario_variants

TAU_CELL_PERCENTILE = 99.9


def map_constants(maps):
    maps = np.asarray(maps)
    if maps.dtype != np.float32 or maps.ndim != 3 or not np.all(np.isfinite(maps)):
        raise ValueError("validation maps must be finite float32 (N, 80, 100)")
    mu0 = float(np.sum(maps, dtype=np.float64) / maps.size)
    b1, b3 = baselines(maps)
    tau_cell = float(np.percentile(maps.astype(np.float64).ravel(), TAU_CELL_PERCENTILE, method="linear"))
    return {"mu0": mu0, "b1": b1, "b3": b3, "tau_cell": tau_cell, "b1_column_profile": b1.mean(axis=0)}


def tau2_threshold(score, is_normal, fa_max=2, fa_per=1000, cap=25, gap=2):
    """Section 14 on one timeline without passes: the smallest tau in T = (+inf, distinct normal scores descending)
    with FA_env(tau) <= fa_max, tested as fa_per x Count_env <= fa_max x |N|. Returns (tau, Count_env at tau, |T|)."""
    score = np.asarray(score, np.float64)
    is_normal = np.asarray(is_normal, bool)
    T = np.concatenate([[np.inf], np.unique(score[is_normal])[::-1]])
    counts = count_curve(score, np.zeros(len(score), np.int32), is_normal, T, cap=cap, gap=gap)
    env = np.maximum.accumulate(counts)
    j = int(np.flatnonzero(fa_per * env <= fa_max * int(is_normal.sum()))[-1])
    return float(T[j]), int(env[j]), int(len(T))


def deployment_thresholds(maps, labels, vmotion, mu0, cfg):
    """One threshold per variant (V0, V1, V2, V4, REV, LAG, ORA) on the validation timeline of one (fold, seed).
    vmotion: stage2_motion.scenario_motion() of the validation scenario under the fold's tau_r."""
    is_normal = np.isin(labels, cfg["data"]["normal_labels"])
    if not is_normal.all():
        raise ValueError("the validation scenario should contain no defect frames (forensic table: 0)")
    v = scenario_variants(maps, vmotion["K"], vmotion["dx"], vmotion["status"], mu0, vmotion["dx_oracle"])
    out = {}
    for name in NAMES:
        tau, count, n_grid = tau2_threshold(v[name], is_normal, cfg["metrics"]["p2_fa"], cfg["events"]["fa_per"],
                                            cfg["events"]["duration_cap"], cfg["events"]["merge_gap"])
        out[name] = {"threshold": tau, "event_count_env": count, "grid_size": n_grid}
    out["motion_unknown_frames"] = int(np.sum(v["mu"]))
    return out
