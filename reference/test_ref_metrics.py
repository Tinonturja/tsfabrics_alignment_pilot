"""Deterministic reference tests for ref_metrics (hand-computed expectations)."""
import math, numpy as np
from fractions import Fraction as Fr
from ref_metrics import count_direct, sweep_counts, all_metrics, _runs_direct
ok = True
def check(name, got, exp):
    global ok
    r = (got == exp); ok &= r
    print(f"{'PASS' if r else 'FAIL'}  {name}: got {got}, expected {exp}")
# 1. ceil boundaries: isolated runs of length 1, 25, 26, 50, 51 separated by 3 non-alarm normal frames
lens = [1, 25, 26, 50, 51]; s = []
for L in lens: s += [1.0] * L + [0.0] * 3
s = np.array(s); n = len(s); scen = np.zeros(n, int); isn = np.ones(n, bool)
check("ceil(L/25) for L=1,25,26,50,51", [math.ceil(L / 25) for L in lens], [1, 1, 2, 2, 3])
check("run count at tau=1 (uncapped)", count_direct(s, scen, isn, 1.0, cap=None), 5)
check("capped count at tau=1", count_direct(s, scen, isn, 1.0), 1 + 1 + 2 + 2 + 3)
# 2. merging: gap of 2 merges, gap of 3 does not
s = np.array([1, 1, 0, 0, 1, 1, 0, 0, 0, 1], float); n = len(s)
check("gap 2 merges, gap 3 splits (runs)", _runs_direct(s, np.zeros(n, int), np.ones(n, bool), 1.0), [(0, 5), (9, 9)])
# 3. excluded frame interrupts even when the gap is <= 2
s = np.array([1, 1, 1, 1], float); isn = np.array([True, True, False, True])
check("excluded frame splits", _runs_direct(s, np.zeros(4, int), isn, 1.0), [(0, 1), (3, 3)])
# 4. merged span length: alarms 0..19, gap 2, alarms 22..29 -> one run of span 30 -> 2 events
s = np.array([1] * 20 + [0, 0] + [1] * 8, float); n = len(s)
check("merged span 30 -> ceil(30/25)=2", count_direct(s, np.zeros(n, int), np.ones(n, bool), 1.0), 2)
# 5. never across scenarios
s = np.ones(6); sc = np.array([0, 0, 0, 1, 1, 1])
check("scenario boundary splits", _runs_direct(s, sc, np.ones(6, bool), 1.0), [(0, 2), (3, 5)])
# 6. sweep equals direct definition on random cases
rng = np.random.default_rng(0); bad = 0
for _ in range(1500):
    n = int(rng.integers(5, 90)); s = rng.integers(0, 5, n).astype(float)
    isn = rng.random(n) > 0.15; sc = np.sort(rng.integers(0, 3, n))
    taus = np.unique(np.r_[s, np.inf]); sw = sweep_counts(s, sc, isn, taus, cap=4)
    bad += sum(sw[t] != count_direct(s, sc, isn, t, cap=4) for t in taus)
check("union-find sweep vs direct definition (1,500 random cases, cap=4 to stress merges)", bad, 0)
# 7. hand-computed P1/P2/P3: 10 normal frames (one scenario), 2 passes in 2 tracks
#    normal scores 0..9 (frame i has score i), pass windows appended after 3 excluded separator frames
s = np.r_[np.arange(10.0), [-1, -1, -1], [8.5], [-1], [3.5]]
isn = np.r_[np.ones(10, bool), np.zeros(6, bool)]; sc = np.zeros(len(s), int)
passes = [(13, 13, 'a'), (15, 15, 'b')]
m = all_metrics(s, sc, isn, passes)
# thresholds desc: inf,9,8.5,8,...; normal frames 0..9 contiguous -> any tau gives ONE run of span (10-ceil(tau)).. capped 1 event
# FA = 1000*1/10 = 100 per 1000 as soon as any normal frame alarms (tau<=9) -> only tau=inf has FA<=10
check("P3 (only +inf point is <=10 FA)", m['P3'], Fr(0))
check("P1 (recall 0.8 needs both passes: tau=3.5 -> FA_env=100 -> capped 50, censored)", m['P1'], (Fr(50), True))
check("P2 (only +inf has FA_env<=2 -> track recall 0)", m['P2'], Fr(0))
# 8. perfect separation
s2 = s.copy(); s2[13] = 100; s2[15] = 100
m = all_metrics(s2, sc, isn, passes)
check("perfect separation P1,P2,P3", (m['P1'], m['P2'], m['P3']), ((Fr(0), False), Fr(1), Fr(1)))
# 9. one pass above all normal frames, one below: R=1/2 at FA 0; R=1 only at FA 100
s3 = s.copy(); s3[13] = 100; s3[15] = -0.5
m = all_metrics(s3, sc, isn, passes)
check("half separation P3 = 1/2", m['P3'], Fr(1, 2))
# 10. step integration with an interior point: 1000 normal frames, a single alarm frame at tau=5 -> FA 1 per 1000
s4 = np.r_[np.zeros(1000), [5.0]]; s4[500] = 5.0
isn4 = np.r_[np.ones(1000, bool), [False]]; sc4 = np.zeros(1001, int)
m = all_metrics(s4, sc4, isn4, [(1000, 1000, 'a')])
# tau=inf: (0,0); tau=5: pass detected, FA=1 -> (1,1); tau=0: FA from 999 frames in two runs -> huge
check("step integral: R=1 from FA=1 to 10 -> P3 = 9/10", m['P3'], Fr(9, 10))
print("ALL REFERENCE METRIC TESTS PASS" if ok else "SOME TESTS FAILED")
