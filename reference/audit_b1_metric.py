"""AUDIT (not experiment code): behaviour of the capped FA-event metric on the real pilot pass layout.
Detectors are synthetic score traces; no TSFabrics scores are used."""
import numpy as np, math
from layout import build
from ref_metrics import all_metrics, _runs_direct
rng = np.random.default_rng(12)
def ma_scen(x, scen, K):
    out = np.empty_like(x)
    for s in np.unique(scen):
        idx = np.flatnonzero(scen == s); v = x[idx]; c = np.cumsum(np.r_[0, v]); t = np.arange(len(v))
        lo = np.maximum(0, t - K + 1); out[idx] = (c[t + 1] - c[lo]) / (t + 1 - lo)
    return out
def detectors(L, K):
    n = L['n']; scen = L['scen']; P = L['passes']
    x = rng.normal(size=n)
    drift = np.zeros(n); e = rng.normal(size=n) * 0.0447
    for t in range(1, n): drift[t] = 0.999 * drift[t - 1] + e[t]
    trans = rng.normal(size=n); pers = rng.normal(size=n)
    for (lo, hi, tr, s, e_, sc, k) in P:
        trans[(s + e_) // 2] += 3.0
        pers[s:e_ + 1] += 1.5
    return {'constant': np.zeros(n), 'slow drift': drift + 0.05 * rng.normal(size=n), 'random iid': x,
            'transient signal V0': trans, 'transient signal MA(K)': ma_scen(trans, scen, K),
            'persistent signal V0': pers, 'persistent signal MA(K)': ma_scen(pers, scen, K)}
for fold in ['A-G1', 'A-G4']:
    L = build(fold); K = int(np.median(L['k'])); isn = L['isn']; scen = L['scen']
    passes = [(p[0], p[1], p[2]) for p in L['passes']]
    print(f"\n=== {fold}  (|N_f|={isn.sum()}, passes={len(passes)}, K={K}); P3 [P1] per cap, mean of 3 draws")
    acc = {}
    for rep in range(3):
        for name, sc in detectors(L, K).items():
            for cap in (None, 25, 50):
                m = all_metrics(sc, scen, isn, passes, cap=cap, thin=1500)
                acc.setdefault((name, cap), []).append((float(m['P3']), float(m['P1'][0])))
    for name in ['constant', 'slow drift', 'random iid', 'transient signal V0', 'transient signal MA(K)', 'persistent signal V0', 'persistent signal MA(K)']:
        row = []
        for cap in (None, 25, 50):
            a = np.array(acc[(name, cap)]).mean(0); row.append(f"{a[0]:.3f} [{a[1]:5.1f}]")
        print(f"  {name:26s} uncapped {row[0]} | D=25 {row[1]} | D=50 {row[2]}")
# single-source nuisance: one fabric-fixed normal-frame source visible v frames, amplitude well above noise
print("\n=== One persistent nuisance source in normal frames: length of the alarm run it creates")
for fold, v, K in [('A-G1 speed', 7, 7), ('A-G4 speed', 21, 21)]:
    lens = {'V0': [], 'MA(K)': []}
    for rep in range(200):
        n = 400; x = rng.normal(size=n) * 0.3; x[200:200 + v] += 3.0
        for name, tr in (('V0', x), ('MA(K)', ma_scen(x, np.zeros(n, int), K))):
            tau = 1.0 if name == 'V0' else 3.0 * 0.5    # threshold at half the source's full-window level
            runs = [r for r in _runs_direct(tr, np.zeros(n, int), np.ones(n, bool), tau) if r[0] <= 200 + v + K and r[1] >= 195]
            lens[name].append(max(b - a + 1 for a, b in runs) if runs else 0)
    for name in lens:
        Ls = np.array(lens[name])
        print(f"  {fold} v={v} K={K} {name:6s}: median run {int(np.median(Ls))} frames -> D=25 counts {math.ceil(np.median(Ls)/25)}, D=50 counts {math.ceil(np.median(Ls)/50)}")
