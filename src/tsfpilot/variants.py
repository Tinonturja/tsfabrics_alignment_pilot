"""Variants (sections 8, 9, 10). One scenario at a time; float64 temporal sums, float32 before the spatial max.

W(A, U)(r, x) = A(r, x + U) if 0 <= x + U <= 99, else mu0.
V0 = s_t; V1 = (1/K) sum_i s_(t-i); V2 = max (1/K) sum_i a_(t-i);
V4 = max (1/K) sum_i W(a_(t-i), U(t, i)); REV uses -U(t, i); LAG uses a_(t-pi(i)) with U(t, i);
ORA = V4 with oracle dx (diagnostic, non-causal).
At motion-unknown frames V4, REV and LAG output V2; ORA outputs V2 at oracle-unknown frames.
Summation order is i = 0, 1, ..., K-1 for every variant, which makes the AT-07 identities exact.
"""
import numpy as np

from .motion import UNKNOWN, motion_unknown
from .windows import lag_perm, shifts_at

NAMES = ("V0", "V1", "V2", "V4", "REV", "LAG", "ORA")


def warp(A, U, mu0, out=None):
    """W(A, U) for a 2-D map A (rows x columns). Returns float64."""
    H, Wd = A.shape
    if out is None:
        out = np.empty((H, Wd), np.float64)
    out.fill(mu0)
    if U >= 0:
        if U < Wd:
            out[:, :Wd - U] = A[:, U:]
    else:
        if -U < Wd:
            out[:, -U:] = A[:, :Wd + U]
    return out


def fill_count(U, width=100):
    """Number of invalid columns of W(., U)."""
    return min(abs(int(U)), width)


def plan(name, t, K, Us):
    """Terms of an aligned variant at 0-based frame t: list of (source frame index, shift) for i = 0..K-1.
    V4: (t - i, U_i); REV: (t - i, -U_i); LAG: (t - pi(i), U_i)."""
    if name == "V4":
        return [(t - i, Us[i]) for i in range(K)]
    if name == "REV":
        return [(t - i, -Us[i]) for i in range(K)]
    if name == "LAG":
        pi = lag_perm(K)
        return [(t - pi[i], Us[i]) for i in range(K)]
    raise ValueError(name)


def aligned_map(maps, terms, mu0, buf=None):
    """(1/K) sum over terms of W(a_src, shift), float64, before the float32 cast."""
    acc = np.zeros(maps.shape[1:], np.float64)
    for src, sh in terms:
        acc += warp(maps[src], sh, mu0, buf)
    return acc / len(terms)


def unaligned_map(maps, t, K):
    acc = np.zeros(maps.shape[1:], np.float64)
    for i in range(K):
        acc += maps[t - i]
    return acc / K


def _score(m):
    return float(m.astype(np.float32).max())


def scenario_variants(maps, K, dx, status, mu0, dx_oracle=None, with_oracle=True):
    """maps: (N, 80, 100) float32 anomaly maps a_t; K: int K_t per frame; dx, status from motion.statuses;
    mu0: float (fold, seed); dx_oracle: oracle dx (nan where unknown).
    Returns dict name -> float64 array (N,) plus 'mu' (motion-unknown) and 'mu_ora' flags."""
    maps = np.asarray(maps)
    N = maps.shape[0]
    s = maps.reshape(N, -1).max(1).astype(np.float32)          # V0: frame score = map max (section 6)
    known = status != UNKNOWN
    mu = motion_unknown(known, K)
    u = np.asarray(dx, np.float64) / 8.0
    out = {k: np.empty(N, np.float64) for k in NAMES}
    if with_oracle:
        ok_ora = np.isfinite(dx_oracle)
        mu_ora = motion_unknown(ok_ora, K)
        uo = np.asarray(dx_oracle, np.float64) / 8.0
    else:
        mu_ora = np.ones(N, bool)
    buf = np.empty(maps.shape[1:], np.float64)
    for t in range(N):
        Kt = int(K[t])
        if Kt < 1 or Kt > t + 1:
            raise ValueError("K_t must lie in [1, t]")
        out["V0"][t] = float(s[t])
        acc1 = 0.0
        for i in range(Kt):
            acc1 += float(s[t - i])
        out["V1"][t] = acc1 / Kt
        v2 = _score(unaligned_map(maps, t, Kt))
        out["V2"][t] = v2
        if mu[t]:
            out["V4"][t] = out["REV"][t] = out["LAG"][t] = v2
        else:
            Us = shifts_at(u, t, Kt)
            for name in ("V4", "REV", "LAG"):
                out[name][t] = _score(aligned_map(maps, plan(name, t, Kt, Us), mu0, buf))
        if mu_ora[t]:
            out["ORA"][t] = v2
        else:
            out["ORA"][t] = _score(aligned_map(maps, plan("V4", t, Kt, shifts_at(uo, t, Kt)), mu0, buf))
    out["mu"] = mu
    out["mu_ora"] = mu_ora
    return out
