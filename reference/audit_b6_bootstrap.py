"""AUDIT: does a contiguous-block bootstrap capture rotation-periodic false-alarm dependence?
Synthetic FA events with fabric-fixed recurring sources on the real pilot scenario lengths and periods."""
import numpy as np
SC = {'A-G1': [(3262, 153), (4804, 156), (617, 59), (18630, 176), (16431, 176)],
      'A-G4': [(3247, 477), (3204, 487), (18465, 556)]}
rng = np.random.default_rng(3)
def generate(fold, hot_frac, hot_p, base_p, drift_sd):
    ev = []; ph_all = []
    for N, P in SC[fold]:
        hot = rng.random(P) < hot_frac                      # fabric locations that recur as FA sources (new fabric each draw)
        p = np.where(hot, hot_p, base_p)
        # rotation phase with random-walk drift of the rotation length
        lengths = np.maximum(1, np.round(P * (1 + drift_sd * rng.normal(size=N // P + 3)))).astype(int)
        phase = np.concatenate([np.arange(Lr) * P // Lr for Lr in lengths])[:N]
        ev.append(rng.random(N) < p[phase]); ph_all.append(phase)
    return ev, ph_all
def boot_se(ev, ph, scheme, L=1200, width=50, B=400):
    units = []                                              # (events, frames) per resampling unit, pooled over the fold
    for e, phs in zip(ev, ph):
        if scheme == 'block':
            for a in range(0, len(e), L): units.append((e[a:a + L].sum(), len(e[a:a + L])))
        else:                                               # phase clusters: frames sharing a rotation-phase bin
            b = phs // width
            for k in np.unique(b): m = b == k; units.append((e[m].sum(), m.sum()))
    u = np.array(units, float); n = len(u)
    idx = rng.integers(0, n, (B, n)); r = u[idx, 0].sum(1) / u[idx, 1].sum(1)
    return r.std(), n
for fold in SC:
    for label, hf, hp in [('no recurring sources', 0.0, 0.0), ('weak recurring sources', 0.03, 0.05), ('strong recurring sources', 0.03, 0.3)]:
        true = []
        for _ in range(300):
            ev, _ = generate(fold, hf, hp, 0.003, 0.03); true.append(sum(e.sum() for e in ev) / sum(len(e) for e in ev))
        sd = np.std(true); res = {}
        for sch, L in [('block', 600), ('block', 1200), ('block', 2400), ('phase', None)]:
            ses = []
            for _ in range(40):
                ev, ph = generate(fold, hf, hp, 0.003, 0.03); se, n = boot_se(ev, ph, sch, L=L or 0)
                ses.append(se)
            res[f"{sch}{'' if L is None else L}"] = (np.mean(ses) / sd, n)
        print(f"{fold} {label:26s} | bootstrap SE / true SD: " + "  ".join(f"{k}={v[0]:.2f} (n={v[1]})" for k, v in res.items()))
