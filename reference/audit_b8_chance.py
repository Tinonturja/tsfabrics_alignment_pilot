"""AUDIT: chance baseline on the real pass layout (synthetic scores)."""
import numpy as np
from layout import build, SC
from ref_metrics import all_metrics
from ref_chance import draw_offsets, collapsed
PER = {'T1_S148_I108_1':153,'T1_S148_I108_2':156,'T1_S174_I108_1':59,'T1_S174_I111_1':176,'T1_S177_I108_1':176,
       'T1_S478_I118_1':477,'T1_S478_I118_2':487,'T1_S555_I117_1':556}
rng = np.random.default_rng(99)
def shifted(score, L, offs):
    out = score.copy()
    for si, d in enumerate(offs):
        idx = np.flatnonzero(L['scen'] == si); out[idx] = np.roll(score[idx], int(d))
    return out
for fi, fold in enumerate(['A-G1', 'A-G4']):
    L = build(fold); isn = L['isn']; scen = L['scen']; passes = [(p[0], p[1], p[2]) for p in L['passes']]
    specs = [(s, N, PER[s]) for s, N, _ in SC[fold]]
    n = L['n']
    rnd = rng.normal(size=n)
    strong = rng.normal(size=n); weak = rng.normal(size=n)
    for (lo, hi, tr, s, e, sc, k) in L['passes']: strong[s:e + 1] += 2.0; weak[s:e + 1] += 0.6
    for name, sc in [('random V0', rnd), ('weak-signal V0', weak), ('strong-signal V0', strong)]:
        obs = all_metrics(sc, scen, isn, passes, thin=500)['P3']
        res = {}
        for restrict in (True, False):
            O = draw_offsets(specs, fi, 0, restrict)
            null = [all_metrics(shifted(sc, L, O[b]), scen, isn, passes, thin=500)['P3'] for b in range(200)]
            col, p = collapsed(obs, null)
            nv = np.array([float(v) for v in null])
            res[restrict] = (col, float(p), np.median(nv), np.quantile(nv, 0.95), nv.max())
        print(f"{fold} {name:16s} P3={float(obs):.3f} | phase-restricted shifts: collapsed={res[True][0]} p={res[True][1]:.3f} null med {res[True][2]:.3f} q95 {res[True][3]:.3f} max {res[True][4]:.3f}"
              f" | unrestricted: collapsed={res[False][0]} null q95 {res[False][3]:.3f} max {res[False][4]:.3f}")
