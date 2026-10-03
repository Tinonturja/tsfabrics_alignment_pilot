"""AUDIT: phase-cluster bootstrap when the rotation phase must be estimated (fixed period vs cutline anchors)."""
import numpy as np
from audit_b6_bootstrap import SC
rng = np.random.default_rng(8)
def gen(fold, hf=0.03, hp=0.3, base=0.003, dsd=0.03, miss=0.10):
    out = []
    for N, P in SC[fold]:
        hot = rng.random(P) < hf; p = np.where(hot, hp, base)
        lengths = np.maximum(1, np.round(P * (1 + dsd * rng.normal(size=N // P + 3)))).astype(int)
        starts = np.r_[0, np.cumsum(lengths)][:-1]
        true_ph = np.concatenate([np.arange(Lr) * P // Lr for Lr in lengths])[:N]
        ev = rng.random(N) < p[true_ph]
        anchors = [s for s in starts if s < N and rng.random() > miss]          # cutline runs, 10% missed
        t = np.arange(N); last = np.full(N, -1)
        for a in anchors: last[a:] = a
        first = anchors[0] if anchors else 0
        anc_ph = np.where(last >= 0, (t - last) % P, (t - first) % P)
        out.append((ev, true_ph, t % P, anc_ph))
    return out
def se(data, which, w=50, B=400):
    units = []
    for d in data:
        ev = d[0]; ph = d[which]; b = ph // w
        for k in np.unique(b): m = b == k; units.append((ev[m].sum(), m.sum()))
    u = np.array(units, float); idx = rng.integers(0, len(u), (B, len(u)))
    return (u[idx, 0].sum(1) / u[idx, 1].sum(1)).std()
for fold in SC:
    true = [ (lambda d: sum(x[0].sum() for x in d) / sum(len(x[0]) for x in d))(gen(fold)) for _ in range(300)]
    sd = np.std(true); r = {1: [], 2: [], 3: []}
    for _ in range(40):
        d = gen(fold)
        for k in r: r[k].append(se(d, k))
    print(f"{fold} strong recurring sources, drift 3%/rotation, 10% anchors missed | SE/trueSD: true phase {np.mean(r[1])/sd:.2f} | fixed-period phase {np.mean(r[2])/sd:.2f} | cutline-anchored phase {np.mean(r[3])/sd:.2f}")
