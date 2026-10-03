"""CALIBRATION CODE. Runs the pre-specified C0b calibration (PROTOCOL.md) and writes results/*.csv.
Usage: python3 run_calibration.py <mode> <n_traces> [families...]
mode: primary (seed-0 offsets), seed1, seed2, seam (D1), unrestricted (D2), timing"""
import sys, os, time, json
import numpy as np
from scipy.stats import beta
from c0b_kernel import Layout, Evaluator
from ref_chance import draw_offsets, allowed_offsets
from nulls import gen, FAMILIES

FOLDS = ['A-G1', 'A-G4']


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi


def run(mode, n, fams):
    os.makedirs('results', exist_ok=True)
    rows = []
    for fi, fold in enumerate(FOLDS):
        L = Layout(fold); E = Evaluator(L)
        specs = [(nm, int(N), int(P)) for nm, N, P in zip(L.names, L.Ns, L.P)]
        seed_idx = {'seed1': 1, 'seed2': 2}.get(mode, 0)
        O = draw_offsets(specs, fi, seed_idx, phase_restrict=(mode != 'unrestricted'))
        for fam in fams:
            famidx = FAMILIES.index(fam); ks = []; t0 = time.time()
            for i in range(n):
                rng = np.random.default_rng([777, fi, famidx, i, {'primary': 0, 'seed1': 1, 'seed2': 2, 'seam': 3, 'unrestricted': 4, 'timing': 5}[mode]])
                x = gen(fam, rng, L.Ns, L.P); prep = E.prepare(x)
                if mode == 'seam':       # observed trace also carries one allowed-shift seam (D1)
                    obs_off = np.array([allowed_offsets(N, P)[rng.integers(0, len(allowed_offsets(N, P)))] for _, N, P in specs])
                else:
                    obs_off = np.zeros(len(specs), np.int64)
                a_obs = E.area(prep, obs_off)
                k = 0
                for b in range(O.shape[0]):
                    if E.area(prep, O[b]) >= a_obs:
                        k += 1
                ks.append(k)
            ks = np.array(ks); fp = int((ks < 10).sum()); lo, hi = cp(fp, n)
            verdict = 'PASS' if hi <= 0.075 else ('FAIL' if lo > 0.075 else 'INDETERMINATE')
            rows.append(dict(mode=mode, fold=fold, family=fam, n=n, false_pass=fp, rate=fp / n, cp_lo=lo, cp_hi=hi,
                             verdict=verdict, median_k=float(np.median(ks)), frac_k200=float((ks == 200).mean()),
                             seconds=round(time.time() - t0, 1)))
            print(json.dumps(rows[-1]), flush=True)
    import csv
    with open(f'results/c0b_{mode}_{"_".join(fams) if len(fams) < 3 else "all"}_n{n}.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    mode = sys.argv[1]; n = int(sys.argv[2]); fams = sys.argv[3:] or FAMILIES
    run(mode, n, fams)
