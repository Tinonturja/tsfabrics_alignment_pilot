"""Section 18: bootstrap replicates reduce to the exact metrics when every unit is drawn once, attribution sums,
draw order and reproducibility."""
import numpy as np
import pytest

from conftest import CFG
from tsfpilot.bootstrap import draws, fold_cis, variant_replicates
from tsfpilot.metrics import all_metrics


def identity_weights(L, reps=3):
    return {"tracks": np.ones((reps, L.n_tracks), np.int64), "B": np.ones((reps, L.n_B), np.int64),
            "P": np.ones((reps, L.n_P), np.int64)}


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_identity_draw_equals_exact_metrics(layouts, fold):
    L = layouts[fold]
    rng = np.random.default_rng(5)
    for kind in range(3):
        x = rng.normal(size=L.n)
        if kind == 1:
            x = np.convolve(rng.normal(size=L.n + 30), np.ones(31) / 31, "valid")[:L.n]
        if kind == 2:
            for a, b in zip(L.s_glob, L.e_glob):
                x[a:b + 1] += 1.0
        m = all_metrics(x, L)
        rep = variant_replicates(x, L, identity_weights(L))
        for scheme in ("P", "B"):
            P1, P2, P3 = rep[scheme]
            assert np.allclose(P1, float(m["P1"]), rtol=0, atol=1e-12)
            assert np.allclose(P2, float(m["P2"]), rtol=0, atol=1e-12)
            assert np.allclose(P3, float(m["P3"]), rtol=0, atol=1e-12)


def test_draws_are_reproducible_and_ordered(layouts):
    cfg = dict(CFG); cfg["bootstrap"] = dict(CFG["bootstrap"], replicates=5)
    a = draws(layouts, cfg); b = draws(layouts, cfg)
    for f in ("A-G1", "A-G4"):
        for k in ("tracks", "B", "P"):
            assert np.array_equal(a[f][k], b[f][k])
            assert (a[f][k].sum(1) == a[f][k].shape[1]).all()      # n draws with replacement from n units
    # order: fold A-G1 first, then A-G4; within a replicate tracks, blocks, clusters
    rng = np.random.default_rng(CFG["bootstrap"]["seed"])
    L = layouts["A-G1"]
    t0 = np.bincount(rng.integers(0, L.n_tracks, L.n_tracks), minlength=L.n_tracks)
    b0 = np.bincount(rng.integers(0, L.n_B, L.n_B), minlength=L.n_B)
    p0 = np.bincount(rng.integers(0, L.n_P, L.n_P), minlength=L.n_P)
    assert np.array_equal(a["A-G1"]["tracks"][0], t0) and np.array_equal(a["A-G1"]["B"][0], b0)
    assert np.array_equal(a["A-G1"]["P"][0], p0)


def test_fold_cis_and_lb(layouts):
    L = layouts["A-G4"]
    cfg = dict(CFG); cfg["bootstrap"] = dict(CFG["bootstrap"], replicates=40)
    W = draws(layouts, cfg)["A-G4"]
    rng = np.random.default_rng(2)
    base = rng.normal(size=L.n)
    sig = base.copy()
    for a, b in zip(L.s_glob, L.e_glob):
        sig[a:b + 1] += 1.5
    rep = {"V1": variant_replicates(base, L, W), "V4": variant_replicates(sig, L, W)}
    for c in ("V2", "REV", "LAG"):
        rep[c] = rep["V1"]
    ci = fold_cis(rep, cfg)
    assert ci["P"]["dP3"][0] <= ci["P"]["dP3"][1]
    from tsfpilot.exact import q9
    assert ci["LB_f"] == min(q9(ci["P"]["dP3"][0]), q9(ci["B"]["dP3"][0]))
    assert float(ci["LB_f"]) > 0          # a strong injected gain has a positive lower bound
