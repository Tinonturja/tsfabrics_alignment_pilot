"""CALIBRATION CODE. Completion runs, pre-registered diagnostics (PROTOCOL.md D1/D2, ADDENDUM-1 D3/D4),
amendment candidate A1 and the power check. Synthetic, label-independent traces only (signal traces for power
use the frozen pass-window layout, never TSFabrics scores or images).
Usage: python3 amend.py <tag> <scheme> <obs> <n> <folds> <families...>
  scheme: v12 | nophase | uniform       obs: zero | seam       folds: A-G1,A-G4
"""
import sys, os, time, json, csv
import numpy as np
from scipy.stats import beta
from c0b_kernel import Layout, Evaluator
from ref_chance import draw_offsets, allowed_offsets
from nulls import gen, FAMILIES, ar1_burn

FOLDS = ['A-G1', 'A-G4']
EXTRA = ['C3_circ0.99', 'C4_circ0.999', 'S_0.25', 'S_0.5']


def cp(k, n, a=0.05):
    lo = 0.0 if k == 0 else beta.ppf(a / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - a / 2, k + 1, n - k)
    return lo, hi


def circ_ar(rng, N, phi):
    """Circular-stationary Gaussian AR(1)-spectrum trace: circulant covariance, unit variance. No seam exists."""
    w = rng.normal(size=N)
    f = np.arange(N)
    S = (1 - phi ** 2) / np.abs(1 - phi * np.exp(-2j * np.pi * f / N)) ** 2
    x = np.fft.ifft(np.fft.fft(w) * np.sqrt(S)).real
    return x


def offsets(scheme, specs, fi, seed_idx):
    if scheme == 'v12':
        return draw_offsets(specs, fi, seed_idx, phase_restrict=True)
    if scheme == 'nophase':
        return draw_offsets(specs, fi, seed_idx, phase_restrict=False)
    if scheme == 'uniform':      # candidate A1: uniform on the full cyclic group of each scenario
        rng = np.random.Generator(np.random.PCG64([20260925, fi, seed_idx]))
        return np.stack([rng.integers(0, N, 200) for _, N, P in specs], 1)
    raise ValueError(scheme)


def one_obs_offset(scheme, rng, specs):
    if scheme == 'uniform':
        return np.array([rng.integers(0, N) for _, N, P in specs], np.int64)
    pr = scheme == 'v12'
    out = []
    for _, N, P in specs:
        a = allowed_offsets(N, P, pr); out.append(a[rng.integers(0, len(a))])
    return np.array(out, np.int64)


def trace(fam, rng, L, inwin):
    if fam in FAMILIES:
        return gen(fam, rng, L.Ns, L.P)
    if fam.startswith('C3'):
        return np.concatenate([circ_ar(rng, int(N), 0.99) for N in L.Ns])
    if fam.startswith('C4'):
        return np.concatenate([circ_ar(rng, int(N), 0.999) for N in L.Ns])
    if fam.startswith('S_'):
        d = float(fam[2:])
        x = np.concatenate([ar1_burn(rng, int(N), 0.9) for N in L.Ns])
        return x + d * inwin
    raise ValueError(fam)


def run(tag, scheme, obs, n, folds, fams):
    os.makedirs('results', exist_ok=True); rows = []
    allf = FAMILIES + EXTRA
    for fold in folds:
        fi = FOLDS.index(fold); L = Layout(fold); E = Evaluator(L)
        specs = [(nm, int(N), int(P)) for nm, N, P in zip(L.names, L.Ns, L.P)]
        O = offsets(scheme, specs, fi, int(os.environ.get("SEED", 0)))   # secondary runs set SEED=1,2
        inwin = (L.win[L.start[L.fscen] + L.flocal] >= 0).astype(float)
        for fam in fams:
            famidx = allf.index(fam); ks = []; t0 = time.time()
            for i in range(n):
                # identical trace stream to run_calibration.py primary for N1..N9 (mode code 0), so v12/zero reproduces it
                rng = np.random.default_rng([777, fi, famidx, i, 0 if obs == 'zero' else 3])
                x = trace(fam, rng, L, inwin); prep = E.prepare(x)
                oo = np.zeros(len(specs), np.int64) if obs == 'zero' else one_obs_offset(scheme, rng, specs)
                a_obs = E.area(prep, oo)
                ks.append(sum(1 for b in range(200) if E.area(prep, O[b]) >= a_obs))
            ks = np.array(ks); fp = int((ks < 10).sum()); lo, hi = cp(fp, n)
            verdict = 'PASS' if hi <= 0.075 else ('FAIL' if lo > 0.075 else 'INDETERMINATE')
            rows.append(dict(tag=tag, scheme=scheme, obs=obs, fold=fold, family=fam, n=n, not_collapsed=fp,
                             rate=fp / n, cp_lo=lo, cp_hi=hi, verdict=verdict, median_k=float(np.median(ks)),
                             frac_k200=float((ks == 200).mean()), seconds=round(time.time() - t0, 1)))
            print(json.dumps(rows[-1]), flush=True)
            with open(f'results/{tag}.csv', 'w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


if __name__ == '__main__':
    tag, scheme, obs, n, folds = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5].split(',')
    run(tag, scheme, obs, n, folds, sys.argv[6:])
