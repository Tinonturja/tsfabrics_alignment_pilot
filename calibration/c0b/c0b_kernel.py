"""CALIBRATION CODE (not experiment code). Fast exact P3 for circularly shifted traces on the frozen pass layout.
P3 is computed in integer units: area100 = sum y*100*dx over the FA_env<=10 region; P3 = area100/(n_pass*|N_f|)."""
import numpy as np
from numba import njit
from layout import build, SC

PER = {'T1_S148_I108_1': 153, 'T1_S148_I108_2': 156, 'T1_S174_I108_1': 59, 'T1_S174_I111_1': 176,
       'T1_S177_I108_1': 176, 'T1_S478_I118_1': 477, 'T1_S478_I118_2': 487, 'T1_S555_I117_1': 556}


class Layout:
    def __init__(self, fold):
        L = build(fold); self.fold = fold
        self.n = L['n']; self.isN = L['isn'].astype(np.bool_)
        self.win = np.full(self.n, -1, np.int64)
        for p, (lo, hi, tr, s, e, sc, k) in enumerate(L['passes']):
            self.win[lo:hi + 1] = p
        self.n_pass = len(L['passes']); self.NN = int(self.isN.sum())
        self.excl_cum = np.cumsum(~self.isN).astype(np.int64)
        self.names = [s for s, N, dx in SC[fold]]
        self.Ns = np.array([N for s, N, dx in SC[fold]], np.int64)
        self.P = np.array([PER[s] for s in self.names], np.int64)
        starts = []; off = 0
        for N in self.Ns:
            starts.append(off); off += N + 4
        self.start = np.array(starts, np.int64)
        self.fscen = np.concatenate([np.full(N, i, np.int64) for i, N in enumerate(self.Ns)])
        self.flocal = np.concatenate([np.arange(N, dtype=np.int64) for N in self.Ns])
        self.passes = [(lo, hi, tr) for (lo, hi, tr, s, e, sc, k) in L['passes']]
        self.pass_scen = np.array([self.names.index(sc) for (lo, hi, tr, s, e, sc, k) in L['passes']])
        self.pass_local = [(s - self.start[self.names.index(sc)], e - self.start[self.names.index(sc)])
                           for (lo, hi, tr, s, e, sc, k) in L['passes']]


@njit(cache=True)
def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


@njit(cache=True)
def _c(a, b):
    return (b - a + 1 + 24) // 25


@njit(cache=True)
def area100(vals, sc, li, off, start, Ns, isN, win, excl, n_pass, NN,
            active, parent, lo, hi, det, touched):
    M = vals.shape[0]; cnt = 0; env = 0; ndet = 0
    x_cur = 0; y_cur = 0; area = 0; nt = 0
    for k in range(M):
        s = sc[k]
        pos = start[s] + (li[k] + off[s]) % Ns[s]
        w = win[pos]
        if w >= 0:
            if not det[w]:
                det[w] = True
                ndet += 1
        elif isN[pos]:
            active[pos] = True; parent[pos] = pos; lo[pos] = pos; hi[pos] = pos
            touched[nt] = pos; nt += 1; cnt += 1
            for u in range(pos - 3, pos + 4):
                if u == pos or u < 0 or u >= isN.shape[0]:
                    continue
                if not active[u]:
                    continue
                a = min(u, pos); b = max(u, pos)
                if excl[b - 1] - excl[a] != 0:
                    continue
                ru = _find(parent, u); rt = _find(parent, pos)
                if ru == rt:
                    continue
                cnt -= _c(lo[ru], hi[ru]) + _c(lo[rt], hi[rt])
                parent[ru] = rt
                if lo[ru] < lo[rt]:
                    lo[rt] = lo[ru]
                if hi[ru] > hi[rt]:
                    hi[rt] = hi[ru]
                cnt += _c(lo[rt], hi[rt])
        if k + 1 == M or vals[k + 1] < vals[k]:          # threshold boundary
            if cnt > env:
                env = cnt
            if 100 * env > NN:
                break
            if env > x_cur:
                area += y_cur * 100 * (env - x_cur)
                x_cur = env
            y_cur = ndet
    area += y_cur * (NN - 100 * x_cur)
    for i in range(nt):
        active[touched[i]] = False
    for p in range(det.shape[0]):
        det[p] = False
    return area


class Evaluator:
    def __init__(self, L):
        self.L = L; n = L.n
        self.active = np.zeros(n, np.bool_); self.parent = np.zeros(n, np.int64)
        self.lo = np.zeros(n, np.int64); self.hi = np.zeros(n, np.int64)
        self.det = np.zeros(L.n_pass, np.bool_); self.touched = np.zeros(n, np.int64)

    def prepare(self, trace):
        """trace: 1-D array over real frames in scenario order (concatenated, no separators)."""
        o = np.argsort(-trace, kind='stable')
        return trace[o].copy(), self.L.fscen[o].copy(), self.L.flocal[o].copy()

    def area(self, prep, offsets):
        v, s, l = prep; L = self.L
        return area100(v, s, l, np.asarray(offsets, np.int64), L.start, L.Ns, L.isN, L.win, L.excl_cum,
                       L.n_pass, L.NN, self.active, self.parent, self.lo, self.hi, self.det, self.touched)
