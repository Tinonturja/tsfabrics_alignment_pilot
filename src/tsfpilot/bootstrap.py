"""Paired cluster bootstrap (section 18).

Defect unit: candidate track (carries all its passes). FA units: rotation-phase clusters (scheme P, primary)
and 1,200-frame blocks (scheme B). Folds are bootstrapped separately. 2,000 replicates per fold.
RNG: numpy.random.default_rng(20260924); order fold A-G1 then A-G4; within each replicate: tracks
(n_tracks draws), then blocks (n_blocks), then phase clusters (n_clusters), all with replacement via
rng.integers(0, n, n). The same draws are used for every variant and every coreset seed.

Per replicate and scheme: P1, P2, P3 of each variant on the original grid T, recall from the resampled passes with
multiplicity, FA = 1000 x (sum of attributed event chunks over drawn units) / (sum of their N_f frames), envelope
rebuilt. CI = numpy percentile 2.5 / 97.5 (method 'linear') of replicate differences.
Decision bound for C3: LB_f = min(q9(lower bound, P), q9(lower bound, B)) of dP3.
"""
import numpy as np

from .exact import q9
from .metrics import curve, replicate_metrics, unit_curve

CONTROLS = ("V2", "REV", "LAG")


def draws(layouts, cfg):
    """layouts: dict fold -> FoldLayout. Returns dict fold -> dict of multiplicity matrices (B x n_units)."""
    bc = cfg["bootstrap"]
    rng = np.random.default_rng(bc["seed"])
    B = bc["replicates"]
    out = {}
    for fold in ("A-G1", "A-G4"):
        L = layouts[fold]
        nK, nB, nP = L.n_tracks, L.n_B, L.n_P
        Wt = np.zeros((B, nK), np.int64); Wb = np.zeros((B, nB), np.int64); Wp = np.zeros((B, nP), np.int64)
        for b in range(B):
            Wt[b] = np.bincount(rng.integers(0, nK, nK), minlength=nK)
            Wb[b] = np.bincount(rng.integers(0, nB, nB), minlength=nB)
            Wp[b] = np.bincount(rng.integers(0, nP, nP), minlength=nP)
        out[fold] = {"tracks": Wt, "B": Wb, "P": Wp}
    return out


def _imat(A, Bm):
    """Exact integer matrix product via float64 BLAS (all entries and sums are far below 2**53)."""
    R = np.asarray(A, np.float64) @ np.asarray(Bm, np.float64)
    if R.size and np.abs(R).max() >= 2 ** 52:
        raise OverflowError("integer product too large for exact float64")
    return np.rint(R).astype(np.int64)


def variant_replicates(score, L, W, cap=25, chunk=100):
    """Replicate P1, P2, P3 of one variant for both schemes. Returns {'P': (P1, P2, P3), 'B': (...)}."""
    c = curve(score, L, cap)
    T = c.T
    npass = np.bincount(L.pass_track, minlength=L.n_tracks).astype(np.int64)
    # D[k, j] = #passes of track k with q_p >= T_j ; Z[k, j] = [z_k >= T_j]
    D = np.zeros((L.n_tracks, len(T)), np.int64)
    for k in range(L.n_tracks):
        qs = np.sort(c.q[L.pass_track == k])
        D[k] = len(qs) - np.searchsorted(qs, T, side="left")
    Z = (c.z[:, None] >= T[None, :]).astype(np.int64)
    res = {}
    for scheme, unit, n_units, nN_u in (("P", L.unit_P, L.n_P, L.nN_P), ("B", L.unit_B, L.n_B, L.nN_B)):
        U = unit_curve(score, L, T, unit, n_units, cap)          # (nT, n_units)
        Wu = W[scheme]; Wt = W["tracks"]
        outs = [[], [], []]
        for a in range(0, Wu.shape[0], chunk):
            wu, wt = Wu[a:a + chunk], Wt[a:a + chunk]
            cnt = _imat(wu, U.T)
            E = np.maximum.accumulate(cnt, axis=1)
            nN = _imat(wu, nN_u[:, None])[:, 0]
            detp = _imat(wt, D); dett = _imat(wt, Z); nP = _imat(wt, npass[:, None])[:, 0]
            if np.any(nN == 0):
                raise ValueError("a replicate drew no N_f frames")
            for o, v in zip(outs, replicate_metrics(E, nN, detp, nP, dett, L.n_tracks)):
                o.append(v)
        res[scheme] = tuple(np.concatenate(o) for o in outs)
    return res


def _ci(x, cfg):
    bc = cfg["bootstrap"]
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return None
    lo, hi = np.percentile(x, [bc["ci_low_pct"], bc["ci_high_pct"]], method="linear")
    return float(lo), float(hi)


def fold_cis(rep, cfg):
    """rep: dict variant -> {'P': (P1, P2, P3), 'B': (...)}. Returns CIs per scheme and LB_f for dP3."""
    out = {}
    for scheme in ("P", "B"):
        v4, v1 = rep["V4"][scheme], rep["V1"][scheme]
        with np.errstate(divide="ignore", invalid="ignore"):
            logr = np.where((v4[0] > 0) & (v1[0] > 0), np.log(v4[0] / v1[0]), np.nan)
        d = {"dP3": _ci(v4[2] - v1[2], cfg), "dP2": _ci(v4[1] - v1[1], cfg), "logP1ratio": _ci(logr, cfg),
             "logP1ratio_undefined": int(np.sum(~np.isfinite(logr)))}
        for ctl in CONTROLS:
            d[f"m_{ctl}"] = _ci(v4[2] - rep[ctl][scheme][2], cfg)
        out[scheme] = d
    out["LB_f"] = min(q9(out["P"]["dP3"][0]), q9(out["B"]["dP3"][0]))
    return out
