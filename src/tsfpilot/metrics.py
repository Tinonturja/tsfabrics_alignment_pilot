"""P1, P2, P3 (sections 13 to 15) in exact integer / Fraction arithmetic.

Grid T: +inf followed by every distinct value of {S(t) : t in N_f} union {q_p}, descending.
q_p = max over W_p of S; z_k = max over the passes of track k of q_p.
FA_env(tau) = running max over T of FA = 1000 x Count / |N_f| (kept as integer counts E_j).
P1: tau* = first T_j with 5 x detected >= 4 x n_passes; P1 = min(FA_env(tau*), 50), censored if > 50.
P2: tau_2 = last T_j with 1000 x E_j <= 2 x |N_f|; P2 = R_track(tau_2).
P3 = (1/10) integral_0^10 R(f) df with R a right-continuous step function, no interpolation.
"""
from dataclasses import dataclass
from fractions import Fraction

import numpy as np

from .events import count_curve, count_curve_units


@dataclass
class Curve:
    T: np.ndarray        # float64 thresholds, T[0] = +inf
    C: np.ndarray        # int64 capped event counts
    E: np.ndarray        # int64 running max of C
    detp: np.ndarray     # int64 #passes with q_p >= T_j
    dett: np.ndarray     # int64 #tracks with z_k >= T_j
    nN: int
    nP: int
    nK: int
    q: np.ndarray
    z: np.ndarray


def pass_scores(score, L):
    q = np.array([float(np.max(score[a:b + 1])) for a, b in zip(L.w_lo, L.w_hi)], np.float64)
    z = np.full(L.n_tracks, -np.inf)
    np.maximum.at(z, L.pass_track, q)
    return q, z


def grid(score, L, q=None):
    if q is None:
        q, _ = pass_scores(score, L)
    vals = np.unique(np.concatenate([np.asarray(score, np.float64)[L.isN], q]))
    return np.concatenate([[np.inf], vals[::-1]])


def _det_counts(vals, T):
    s = np.sort(vals)
    # number of values >= T_j
    return (len(s) - np.searchsorted(s, T, side="left")).astype(np.int64)


def curve(score, L, cap=25):
    score = np.asarray(score, np.float64)
    q, z = pass_scores(score, L)
    T = grid(score, L, q)
    C = count_curve(score, L.scen, L.isN, T, cap=cap)
    return Curve(T=T, C=C, E=np.maximum.accumulate(C), detp=_det_counts(q, T), dett=_det_counts(z, T),
                 nN=L.nN, nP=L.n_passes, nK=L.n_tracks, q=q, z=z)


def p1(c, cap=50):
    j = int(np.flatnonzero(5 * c.detp >= 4 * c.nP)[0])
    fa = Fraction(1000 * int(c.E[j]), c.nN)
    return min(fa, Fraction(cap)), fa > cap


def p2_index(c):
    return int(np.flatnonzero(1000 * c.E <= 2 * c.nN)[-1])


def p2(c):
    return Fraction(int(c.dett[p2_index(c)]), c.nK)


def p3(c):
    """Exact: A = sum_j detp_j * 1000 (E_(j+1) - E_j) over the prefix with 100 E_j <= |N_f|,
    plus detp_last * (10 |N_f| - 1000 E_last); P3 = A / (10 n_passes |N_f|)."""
    ok = np.flatnonzero(100 * c.E <= c.nN)
    J = int(ok[-1]) + 1                 # E is non-decreasing, so the qualifying set is a prefix
    A = 0
    for j in range(J - 1):
        A += int(c.detp[j]) * 1000 * (int(c.E[j + 1]) - int(c.E[j]))
    A += int(c.detp[J - 1]) * (10 * c.nN - 1000 * int(c.E[J - 1]))
    return Fraction(A, 10 * c.nP * c.nN)


def c0a_saturated(c):
    """Section 20: V0's R_pass at V0's own tau_2 >= 0.95 (integer test 20 x detected >= 19 x n_passes)."""
    return 20 * int(c.detp[p2_index(c)]) >= 19 * c.nP


def all_metrics(score, L, cap=25):
    c = curve(score, L, cap)
    P1, cens = p1(c)
    return {"P1": P1, "P1_censored": cens, "P2": p2(c), "P3": p3(c), "curve": c}


def p3_only(score, L, cap=25):
    return p3(curve(score, L, cap))


# ---------- float versions for bootstrap replicates (section 18; floats are allowed for bounds) ----------

def replicate_metrics(E, nN, detp, nP, dett, nK, p1cap=50):
    """Integer inputs for B replicates along the descending grid T:
    E (B, nT) running-max event counts; nN (B,) N_f frames drawn; detp (B, nT) detected passes (with multiplicity);
    nP (B,) passes drawn; dett (B, nT) detected tracks (with multiplicity); nK = n_tracks.
    Every comparison is an integer comparison; only the final values are floats.
    Returns float arrays P1, P2, P3 of shape (B,)."""
    E = np.asarray(E, np.int64); detp = np.asarray(detp, np.int64); dett = np.asarray(dett, np.int64)
    nN = np.asarray(nN, np.int64); nP = np.asarray(nP, np.int64)
    B, nT = E.shape
    rows = np.arange(B)
    j1 = np.argmax(5 * detp >= 4 * nP[:, None], axis=1)              # first index (always exists: last T has all)
    P1 = np.minimum(1000.0 * E[rows, j1] / nN, float(p1cap))
    ok2 = 1000 * E <= 2 * nN[:, None]
    j2 = nT - 1 - np.argmax(ok2[:, ::-1], axis=1)
    P2 = dett[rows, j2] / float(nK)
    ok3 = 100 * E <= nN[:, None]
    last = nT - 1 - np.argmax(ok3[:, ::-1], axis=1)
    nxtE = np.concatenate([E[:, 1:], E[:, -1:]], axis=1)
    inner = np.arange(nT)[None, :] < last[:, None]
    A = (detp * 1000 * (nxtE - E) * inner).sum(1)
    A = A + detp[rows, last] * (10 * nN - 1000 * E[rows, last])
    P3 = A / (10.0 * nP * nN)
    return P1, P2, P3


def unit_curve(score, L, T, unit, n_units, cap=25):
    """Per-unit chunk counts on a fixed grid T (nT x n_units)."""
    _, U = count_curve_units(score, L.scen, L.isN, T, unit, n_units, cap=cap)
    return U
