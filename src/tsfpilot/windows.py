"""Adaptive window and cell shifts (section 7 item 6, section 8).

k_t: 10 while fewer than 5 reliable estimates exist; 25 if m_t = 0; else min(25, max(3, floor(800 / m_t + 0.5))),
where m_t is the numpy median of |dx| over the last up to 15 reliable estimates at or before t.
K_t = min(k_t, t), t 1-based.

U(t, 0) = 0; U(t, i) = floor(-(u_(t-i+1) + ... + u_t) + 0.5) with u_j = dx_j / 8 (float64).
The sum is accumulated sequentially in ascending j (documented choice; it fixes the float rounding order).
"""
import math

import numpy as np

from .motion import RELIABLE


def k_series(dx, status, wcfg):
    n = len(dx)
    k = np.zeros(n, np.int64)
    rel = []
    for i in range(n):
        if status[i] == RELIABLE:
            rel.append(abs(float(dx[i])))
        if len(rel) < wcfg["reliable_for_k"]:
            k[i] = wcfg["k_initial"]
            continue
        m = float(np.median(rel[-wcfg["median_window"]:]))
        if m == 0.0:
            k[i] = wcfg["k_stopped"]
        else:
            k[i] = min(wcfg["k_max"], max(wcfg["k_min"], math.floor(wcfg["span_px"] / m + 0.5)))
    K = np.minimum(k, np.arange(1, n + 1))
    return k, K


def shifts_at(u, t_idx, K):
    """u: float64 array of dx/8 per frame (0-based index); t_idx: 0-based index of frame t.
    Returns list of int U(t, i) for i = 0..K-1 using only u[t-K+2 .. t] (all must be finite)."""
    out = [0]
    for i in range(1, K):
        acc = 0.0
        for j in range(t_idx - i + 1, t_idx + 1):      # ascending j
            acc += u[j]
        out.append(math.floor(-acc + 0.5))
    return out


def lag_perm(K):
    """Section 9: pi(0) = 0; for K >= 3, pi(i) = (i mod (K - 1)) + 1 for i >= 1; identity for K <= 2."""
    if K <= 2:
        return list(range(K))
    return [0] + [(i % (K - 1)) + 1 for i in range(1, K)]
