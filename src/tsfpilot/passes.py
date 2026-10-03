"""Evaluation units (sections 11, 18): pass windows W_p, the normal set N_f, tracks, carry-over flags,
rotation-phase clusters (scheme P) and 1,200-frame blocks (scheme B).

Test labels are used only here, to define evaluation units (section 5 rule 2).

Timeline: the fold's test scenarios concatenated in the configured order (lexicographic); global index g,
local 1-based frame t = g - start[s] + 1.
"""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class FoldLayout:
    fold: str
    names: list
    Ns: np.ndarray
    start: np.ndarray
    n: int
    scen: np.ndarray            # int32 per frame
    local: np.ndarray           # 1-based frame index per frame
    label: np.ndarray           # int per frame
    isN: np.ndarray             # bool, N_f
    pass_ids: list
    pass_scen: np.ndarray
    s_glob: np.ndarray          # pass start (global, inclusive)
    e_glob: np.ndarray          # pass end (global, inclusive)
    w_lo: np.ndarray            # window start (global, inclusive) = s_glob
    w_hi: np.ndarray            # window end (global, inclusive)
    pass_track: np.ndarray      # index into tracks
    pass_labels: list
    tracks: list
    carry: np.ndarray           # carry-over-affected flag per pass
    unit_P: np.ndarray = field(default=None)
    n_P: int = 0
    unit_B: np.ndarray = field(default=None)
    n_B: int = 0
    nN_P: np.ndarray = field(default=None)
    nN_B: np.ndarray = field(default=None)

    @property
    def n_passes(self):
        return len(self.pass_ids)

    @property
    def n_tracks(self):
        return len(self.tracks)

    @property
    def nN(self):
        return int(self.isN.sum())

    def windows(self):
        return list(zip(self.w_lo.tolist(), self.w_hi.tolist()))


def window_end(s, e, N, K_local, s_next, grace_max=24, grace=True):
    """Section 11: W_p = [s, min(g, s_next - 1, N)], g = max{t in [e, min(e + 24, N)] : t - K_t + 1 <= e}.
    s, e, N, s_next are 1-based local frames; K_local[t - 1] = K_t. grace=False gives S1's [s, e]."""
    if not grace:
        return e
    g = e
    for t in range(e, min(e + grace_max, N) + 1):
        if t - int(K_local[t - 1]) + 1 <= e:
            g = t
    return min(g, s_next - 1, N)


def phase_units(labels, P, anchor_labels=(2, 5), width=50):
    """Section 18 scheme P for one scenario. labels: int per frame (index 0 = frame 1). Returns bin index per frame."""
    N = len(labels)
    isa = np.isin(labels, anchor_labels)
    starts = [i + 1 for i in range(N) if isa[i] and (i == 0 or not isa[i - 1])]      # 1-based run starts
    acc = []
    for a in starts:
        if not acc or not (2 * (a - acc[-1]) < P):
            acc.append(a)
    phi = np.empty(N, np.int64)
    j = -1
    for i in range(N):
        t = i + 1
        while j + 1 < len(acc) and acc[j + 1] <= t:
            j += 1
        if not acc:
            phi[i] = (t - 1) % P
        elif j < 0:
            phi[i] = (t - acc[0]) % P          # Python % is the mathematical modulo
        else:
            phi[i] = (t - acc[j]) % P
    return phi // width, acc


def build_layout(fold, cfg, passes_df, labels_by_scen, K_by_scen, grace=True):
    fc = cfg["folds"][fold]
    names = list(fc["test"])
    if names != sorted(names):
        raise ValueError("test scenarios must be in lexicographic order")
    Ns = np.array([len(labels_by_scen[s]) for s in names], np.int64)
    start = np.concatenate([[0], np.cumsum(Ns)[:-1]]).astype(np.int64)
    n = int(Ns.sum())
    scen = np.concatenate([np.full(N, i, np.int32) for i, N in enumerate(Ns)])
    local = np.concatenate([np.arange(1, N + 1) for N in Ns]).astype(np.int64)
    label = np.concatenate([np.asarray(labels_by_scen[s], np.int64) for s in names])

    df = passes_df[passes_df.scenario.isin(names)].copy()
    df["si"] = df.scenario.map({s: i for i, s in enumerate(names)})
    df = df.sort_values(["si", "pass_start"]).reset_index(drop=True)
    tracks = sorted(df.candidate_track_id.unique().tolist())
    tix = {k: i for i, k in enumerate(tracks)}
    in_window = np.zeros(n, bool)
    rows = []
    for si, g in df.groupby("si", sort=True):
        g = g.sort_values("pass_start")
        N = int(Ns[si]); K = np.asarray(K_by_scen[names[si]])
        starts = g.pass_start.tolist(); ends = g.pass_end.tolist()
        for j, r in enumerate(g.itertuples()):
            s, e = int(r.pass_start), int(r.pass_end)
            s_next = starts[j + 1] if j + 1 < len(starts) else N + 1
            end = window_end(s, e, N, K, s_next, cfg["passes"]["grace_max"], grace)
            carry = j > 0 and (s - int(K[s - 1]) + 1 <= int(ends[j - 1]))
            off = int(start[si])
            lo, hi = off + s - 1, off + end - 1
            if in_window[lo:hi + 1].any():
                raise ValueError("pass windows overlap")
            in_window[lo:hi + 1] = True
            rows.append((r.pass_id, si, off + s - 1, off + e - 1, lo, hi, tix[r.candidate_track_id], r.labels, carry))
    isN = np.isin(label, cfg["data"]["normal_labels"]) & ~in_window

    L = FoldLayout(fold=fold, names=names, Ns=Ns, start=start, n=n, scen=scen, local=local, label=label, isN=isN,
                   pass_ids=[r[0] for r in rows], pass_scen=np.array([r[1] for r in rows]),
                   s_glob=np.array([r[2] for r in rows]), e_glob=np.array([r[3] for r in rows]),
                   w_lo=np.array([r[4] for r in rows]), w_hi=np.array([r[5] for r in rows]),
                   pass_track=np.array([r[6] for r in rows]), pass_labels=[r[7] for r in rows], tracks=tracks,
                   carry=np.array([r[8] for r in rows], bool))
    # resampling units (section 18)
    uP = np.empty(n, np.int64); keysP = {}
    uB = np.empty(n, np.int64); keysB = {}
    bl = cfg["bootstrap"]["block_length"]; pw = cfg["bootstrap"]["phase_bin"]
    for si, s in enumerate(names):
        a, b = int(start[si]), int(start[si] + Ns[si])
        bins, _ = phase_units(label[a:b], cfg["periods"][s], tuple(cfg["data"]["cutline_anchor_labels"]), pw)
        for i in range(a, b):
            kp = (si, int(bins[i - a])); kb = (si, (i - a) // bl)
            uP[i] = keysP.setdefault(kp, len(keysP)); uB[i] = keysB.setdefault(kb, len(keysB))
    # units are numbered in sorted (scenario index, bin) order, independent of discovery order
    for u, keys in ((uP, keysP), (uB, keysB)):
        remap = np.empty(len(keys), np.int64)
        for rank, key in enumerate(sorted(keys)):
            remap[keys[key]] = rank
        u[:] = remap[u]
    L.unit_P, L.n_P, L.unit_B, L.n_B = uP, len(keysP), uB, len(keysB)
    L.nN_P = np.bincount(uP[isN], minlength=L.n_P).astype(np.int64)
    L.nN_B = np.bincount(uB[isN], minlength=L.n_B).astype(np.int64)
    return L


def read_passes(path):
    return pd.read_csv(path)
