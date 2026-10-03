"""False-alarm events (section 12).

At threshold tau, an alarm frame is a frame t in N_f with S(t) >= tau. Two alarm frames u < w of the same scenario
are linked if w - u <= 3 and every frame strictly between them is in N_f. A run is a connected component of the
link relation with span L = last - first + 1, and contributes ceil(L / 25) events.

All thresholds are processed in one descending sweep with a union-find that keeps each component's span.
For the bootstrap (section 12 item 7, section 18), a run [a, b] is split into chunks starting at a, a + 25, ...;
each chunk is one event attributed to the resampling unit containing its first frame, so per-unit counts sum
exactly to the total.

Inputs describe one fold timeline: test scenarios concatenated in the fold's scenario order.
  score : float64 per frame
  scen  : int32 scenario index per frame (runs never cross scenarios)
  isN   : bool, True for frames in N_f
"""
import numpy as np
from numba import njit

GAP = 2
CAP = 25


@njit(cache=True)
def _find(parent, x):
    root = x
    while parent[root] != root:
        root = parent[root]
    while parent[x] != root:
        nxt = parent[x]
        parent[x] = root
        x = nxt
    return root


@njit(cache=True)
def _nchunks(a, b, cap):
    return (b - a + cap) // cap          # ceil((b - a + 1) / cap)


@njit(cache=True)
def _attr(unit, unit_cnt, a, b, cap, sign):
    c = a
    while c <= b:
        unit_cnt[unit[c]] += sign
        c += cap


@njit(cache=True)
def _sweep(order, score, scen, isN, excl, T, cap, gap, unit, n_units, want_units):
    n = score.shape[0]
    nT = T.shape[0]
    parent = np.arange(n)
    lo = np.arange(n)
    hi = np.arange(n)
    active = np.zeros(n, np.bool_)
    counts = np.zeros(nT, np.int64)
    if want_units:
        ucounts = np.zeros((nT, n_units), np.int32)
        unit_cnt = np.zeros(n_units, np.int32)
    else:
        ucounts = np.zeros((1, 1), np.int32)
        unit_cnt = np.zeros(1, np.int32)
    total = 0
    k = 0
    m = order.shape[0]
    for j in range(nT):
        tau = T[j]
        while k < m and score[order[k]] >= tau:
            t = order[k]
            k += 1
            active[t] = True
            total += 1
            if want_units:
                unit_cnt[unit[t]] += 1
            for u in range(t - gap - 1, t + gap + 2):
                if u == t or u < 0 or u >= n:
                    continue
                if not active[u] or scen[u] != scen[t]:
                    continue
                a = min(u, t)
                b = max(u, t)
                if excl[b - 1] - excl[a] != 0:      # an excluded frame lies strictly between a and b
                    continue
                ru = _find(parent, u)
                rt = _find(parent, t)
                if ru == rt:
                    continue
                total -= _nchunks(lo[ru], hi[ru], cap) + _nchunks(lo[rt], hi[rt], cap)
                if want_units:
                    _attr(unit, unit_cnt, lo[ru], hi[ru], cap, -1)
                    _attr(unit, unit_cnt, lo[rt], hi[rt], cap, -1)
                parent[ru] = rt
                if lo[ru] < lo[rt]:
                    lo[rt] = lo[ru]
                if hi[ru] > hi[rt]:
                    hi[rt] = hi[ru]
                total += _nchunks(lo[rt], hi[rt], cap)
                if want_units:
                    _attr(unit, unit_cnt, lo[rt], hi[rt], cap, 1)
        counts[j] = total
        if want_units:
            for q in range(n_units):
                ucounts[j, q] = unit_cnt[q]
    return counts, ucounts


def _prep(score, scen, isN):
    score = np.ascontiguousarray(score, dtype=np.float64)
    if not np.all(np.isfinite(score)):
        raise ValueError("non-finite score: Stage 3 must abort (section 20)")
    scen = np.ascontiguousarray(scen, dtype=np.int32)
    isN = np.ascontiguousarray(isN, dtype=np.bool_)
    excl = np.cumsum(~isN).astype(np.int64)
    idx = np.flatnonzero(isN)
    order = idx[np.argsort(-score[idx], kind="stable")].astype(np.int64)
    return score, scen, isN, excl, order


def count_curve(score, scen, isN, T, cap=CAP, gap=GAP):
    """Capped event count at every threshold of the descending grid T (T[0] may be +inf). Returns int64 array."""
    score, scen, isN, excl, order = _prep(score, scen, isN)
    T = np.asarray(T, dtype=np.float64)
    if np.any(np.diff(T) >= 0):
        raise ValueError("T must be strictly descending")
    dummy = np.zeros(1, np.int32)
    counts, _ = _sweep(order, score, scen, isN, excl, T, int(cap), int(gap), dummy, 1, False)
    return counts


def count_curve_units(score, scen, isN, T, unit, n_units, cap=CAP, gap=GAP):
    """As count_curve, plus per-unit chunk counts (nT x n_units, int32). unit[t] is the unit of frame t."""
    score, scen, isN, excl, order = _prep(score, scen, isN)
    T = np.asarray(T, dtype=np.float64)
    unit = np.ascontiguousarray(unit, dtype=np.int64)
    if unit.min() < 0 or unit.max() >= n_units:
        raise ValueError("unit index out of range")
    return _sweep(order, score, scen, isN, excl, T, int(cap), int(gap), unit, int(n_units), True)


def runs_direct(score, scen, isN, tau, gap=GAP):
    """Direct (slow) definition, used only in tests: list of (first, last) runs at threshold tau."""
    runs = []
    cur = None
    for t in range(len(score)):
        if not (isN[t] and score[t] >= tau):
            continue
        if cur is not None and scen[t] == scen[cur[1]] and t - cur[1] <= gap + 1 and all(isN[cur[1] + 1:t]):
            cur[1] = t
        else:
            if cur is not None:
                runs.append(tuple(cur))
            cur = [t, t]
    if cur is not None:
        runs.append(tuple(cur))
    return runs
