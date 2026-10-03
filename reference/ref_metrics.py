"""REFERENCE (audit) implementation of Research Gate v1.2 sections 12-15.
Not experiment code. Exact rational arithmetic for every quantity that enters a decision.

Inputs
  score   : float array, one value per frame of the fold timeline (all scenarios concatenated)
  scen    : int array, scenario id per frame (events never cross scenarios)
  isnormal: bool array, True for frames in N_f (label 1/2 and outside every pass window)
  passes  : list of (lo, hi, track_id) global inclusive frame ranges of the pass windows W_p
"""
from fractions import Fraction as Fr
import math
import numpy as np

GAP = 2        # up to 2 non-alarm N_f frames may separate two alarm frames of one run
D = 25         # duration cap: a run of span L contributes ceil(L / D) events

def _runs_direct(score, scen, isnormal, tau):
    """Direct definition (section 12): list of (first, last) merged alarm runs at threshold tau."""
    runs = []; cur = None
    for t in range(len(score)):
        if not (isnormal[t] and score[t] >= tau):
            continue
        if cur is not None and scen[t] == scen[cur[1]] and t - cur[1] <= GAP + 1 \
           and all(isnormal[cur[1] + 1:t]):
            cur[1] = t
        else:
            if cur is not None: runs.append(tuple(cur))
            cur = [t, t]
    if cur is not None: runs.append(tuple(cur))
    return runs

def count_direct(score, scen, isnormal, tau, cap=D):
    runs = _runs_direct(score, scen, isnormal, tau)
    if cap is None: return len(runs)
    return sum(math.ceil((b - a + 1) / cap) for a, b in runs)

def sweep_counts(score, scen, isnormal, taus, cap=D):
    """Union-find sweep over descending thresholds; tracks each component's span. Returns {tau: count}."""
    n = len(score); parent = list(range(n)); lo = list(range(n)); hi = list(range(n))
    active = np.zeros(n, bool); total = 0
    excl = np.cumsum(~np.asarray(isnormal))           # excluded frames up to and including t
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def c(a, b): return 1 if cap is None else math.ceil((b - a + 1) / cap)
    order = np.argsort(-np.asarray(score), kind='stable'); k = 0; out = {}
    for tau in sorted(set(taus), reverse=True):
        while k < n and score[order[k]] >= tau:
            t = int(order[k]); k += 1
            if not isnormal[t]: continue
            active[t] = True; total += 1
            for u in range(max(0, t - GAP - 1), min(n, t + GAP + 2)):
                if u == t or not active[u] or scen[u] != scen[t]: continue
                a, b = min(u, t), max(u, t)
                if excl[b - 1] - excl[a] != 0: continue   # an excluded frame lies strictly between
                ru, rt = find(u), find(t)
                if ru == rt: continue
                total -= c(lo[ru], hi[ru]) + c(lo[rt], hi[rt])
                parent[ru] = rt; lo[rt] = min(lo[ru], lo[rt]); hi[rt] = max(hi[ru], hi[rt])
                total += c(lo[rt], hi[rt])
        out[tau] = total
    return out

def curves(score, scen, isnormal, passes, cap=D, thin=None):
    score = np.asarray(score, float); isnormal = np.asarray(isnormal, bool)
    q = np.array([score[a:b + 1].max() for a, b, _ in passes])
    trk = [p[2] for p in passes]; tracks = sorted(set(trk))
    z = np.array([max(q[i] for i in range(len(q)) if trk[i] == k) for k in tracks])
    cand = np.unique(np.r_[score[isnormal], q])
    if thin is not None:     # audit-only approximation for large simulations; never used for decisions
        cand = np.unique(np.r_[np.quantile(cand, np.linspace(0, 1, thin)), q])
    T = [math.inf] + sorted(cand.tolist(), reverse=True)
    cnt = sweep_counts(score, scen, isnormal, T, cap)
    nN = int(isnormal.sum()); nP = len(q); nK = len(z)
    FA = [Fr(1000 * cnt[t], nN) for t in T]
    env = []; m = Fr(0)
    for f in FA: m = max(m, f); env.append(m)
    Rp = [Fr(int((q >= t).sum()), nP) for t in T]
    Rt = [Fr(int((z >= t).sum()), nK) for t in T]
    return T, env, Rp, Rt

def P1(env, Rp, cap=Fr(50)):
    j = next(i for i, r in enumerate(Rp) if r >= Fr(4, 5))
    return min(env[j], cap), env[j] > cap
def P2(env, Rt, f=Fr(2)):
    j = max(i for i, e in enumerate(env) if e <= f)
    return Rt[j]
def P3(env, Rp, fmax=Fr(10)):
    xs, ys = [], []
    for x, y in zip(env, Rp):
        if x > fmax: break
        if xs and x == xs[-1]: ys[-1] = max(ys[-1], y)
        else: xs.append(x); ys.append(max(y, ys[-1] if ys else Fr(0)))
    area = Fr(0)
    for i, (x, y) in enumerate(zip(xs, ys)):
        area += y * ((xs[i + 1] if i + 1 < len(xs) else fmax) - x)
    return area / fmax
def all_metrics(score, scen, isnormal, passes, cap=D, thin=None):
    T, env, Rp, Rt = curves(score, scen, isnormal, passes, cap, thin)
    return dict(P1=P1(env, Rp), P2=P2(env, Rt), P3=P3(env, Rp))
