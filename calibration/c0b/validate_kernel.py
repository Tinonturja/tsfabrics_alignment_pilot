"""Check the fast kernel against the exact Fraction reference (ref_metrics, no thinning) on the real layout."""
import numpy as np
from fractions import Fraction as Fr
from c0b_kernel import Layout, Evaluator
from ref_metrics import all_metrics

rng = np.random.default_rng(1)
for fold in ['A-G1', 'A-G4']:
    L = Layout(fold); E = Evaluator(L); bad = 0
    full_scen = np.full(L.n, -1)
    for i, st in enumerate(L.start):
        full_scen[st:st + L.Ns[i]] = i
    for trial in range(4):
        x = rng.normal(size=int(L.Ns.sum()))
        if trial % 2:
            x = np.convolve(x, np.ones(9) / 9, 'same') + 0.3 * rng.normal(size=x.size)
        offs = np.array([0 if trial == 0 else int(rng.integers(1, N)) for N in L.Ns])
        full = np.full(L.n, -np.inf)
        for i, st in enumerate(L.start):
            seg = x[L.fscen == i]
            full[st:st + L.Ns[i]] = np.roll(seg, offs[i])
        ref = all_metrics(full, full_scen, L.isN, L.passes)['P3']
        fast = Fr(int(E.area(E.prepare(x), offs)), L.n_pass * L.NN)
        bad += (ref != fast)
        print(fold, trial, 'ref', float(ref), 'fast', float(fast), 'equal', ref == fast, flush=True)
    print(fold, 'mismatches', bad, flush=True)
