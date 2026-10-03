"""Chance baseline C0b (section 19 as amended by v1.2.1).

V0's frame-score trace is circularly shifted within each test scenario, over the whole scenario including
pass-window frames: shifted = numpy.roll(x_s, d_s). Labels, passes, windows, N_f, tracks, thresholds and the metric
stay fixed. 200 shifts per fold and coreset seed; each shift draws one offset per scenario.
v1.2.1: offsets uniform on {0, ..., N_s - 1}: rng = Generator(PCG64([20260925, fold_index, seed_index])); for each
test scenario in lexicographic order, rng.integers(0, N_s, 200); columns stacked into a 200 x S array.
Collapse iff k = #{P3_shift >= P3(V0)} >= 10 (exact rational comparison), i.e. p = (1 + k) / 201 > 0.05.
"""
import hashlib
from fractions import Fraction

import numpy as np

from .metrics import p3_only


def offsets(Ns, fold_index, seed_index, n_shifts=200, seed_base=20260925):
    rng = np.random.Generator(np.random.PCG64([seed_base, fold_index, seed_index]))
    return np.stack([rng.integers(0, int(N), n_shifts) for N in Ns], 1).astype(np.int64)


def offsets_sha256(O):
    return hashlib.sha256(np.ascontiguousarray(O, dtype=np.int64).tobytes()).hexdigest()


def shift_trace(x, L, d):
    out = np.empty_like(np.asarray(x, np.float64))
    for si in range(len(L.names)):
        a, b = int(L.start[si]), int(L.start[si] + L.Ns[si])
        out[a:b] = np.roll(np.asarray(x, np.float64)[a:b], int(d[si]))
    return out


def c0b(v0, L, fold_index, seed_index, cfg, p3_obs=None):
    cc = cfg["chance"]
    O = offsets(L.Ns, fold_index, seed_index, cc["n_shifts"], cc["seed_base"])
    if p3_obs is None:
        p3_obs = p3_only(v0, L)
    null = [p3_only(shift_trace(v0, L, O[b]), L) for b in range(O.shape[0])]
    k = sum(1 for v in null if v >= p3_obs)
    return {"collapsed": k >= cc["collapse_k"], "k": k, "p": Fraction(1 + k, 1 + len(null)),
            "P3_obs": p3_obs, "null": null, "offsets": O, "offsets_sha256": offsets_sha256(O)}
