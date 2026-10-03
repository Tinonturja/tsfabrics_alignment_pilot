"""AT-15 as amended by v1.2.1: offset fixtures, support, behaviour on synthetic real-layout cases, and agreement
with the calibration package."""
import sys

import numpy as np
import pytest

from conftest import CAL, CFG, synthetic_layout
from tsfpilot.chance import c0b, offsets, offsets_sha256, shift_trace
from tsfpilot.metrics import p3_only

FIXTURE = {  # PREREGISTRATION_AMENDMENT_v1.2.1.md, section C6
    ("A-G1", 0): "2182b12659c5608cf72e99b01a1fbd2bd1ac35c979d7fd913619d55b3bd2138b",
    ("A-G1", 1): "894acd0c45f65322a93192ced2d36ce7da9c89b409af3efef4804adbc6294a38",
    ("A-G1", 2): "519638b9d8b3a66564b67c5aaaf5e76b66784a6b7f96c7defdd0c3e98ef67155",
    ("A-G4", 0): "f3c86cd13135f966319b4b183e0af6baa80b267b028e9ef894d7e4dc472a979c",
    ("A-G4", 1): "65aaaf6fd6145b97607d00815cd000e3444d50a177a35eeccb779b3db02940ac",
    ("A-G4", 2): "28f1fc386a2257e1e08e8044621217d381dd0b9b7864af9e5f9d5140bce49962",
}
FIRST_ROWS = {"A-G1": [[2469, 118, 286, 6833, 16396], [519, 309, 148, 14196, 10598], [2010, 1080, 486, 10825, 1055]],
              "A-G4": [[1613, 415, 13001], [2073, 2449, 8417], [221, 519, 140]]}


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_at15_offsets_reproduce_and_lie_in_support(layouts, fold):
    L = layouts[fold]
    fi = CFG["folds"][fold]["index"]
    for seed in (0, 1, 2):
        O = offsets(L.Ns, fi, seed)
        assert O.shape == (200, len(L.names))
        assert offsets_sha256(O) == FIXTURE[(fold, seed)]
        assert (O >= 0).all() and (O < L.Ns[None, :]).all()
    assert offsets(L.Ns, fi, 0)[:3].tolist() == FIRST_ROWS[fold]


def test_shift_is_numpy_roll_within_scenarios(layouts):
    L = layouts["A-G4"]
    x = np.arange(L.n, dtype=float)
    d = [5, 0, L.Ns[2] - 1]
    y = shift_trace(x, L, d)
    for si in range(3):
        a, b = L.start[si], L.start[si] + L.Ns[si]
        assert np.array_equal(y[a:b], np.roll(x[a:b], d[si]))


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_at15_random_collapses_strong_does_not(layouts, fold):
    L = layouts[fold]
    fi = CFG["folds"][fold]["index"]
    rng = np.random.default_rng(99 + fi)
    rnd = rng.normal(size=L.n)
    strong = rng.normal(size=L.n)
    for a, b in zip(L.s_glob, L.e_glob):
        strong[a:b + 1] += 2.0
    assert c0b(rnd, L, fi, 0, CFG)["collapsed"]
    r = c0b(strong, L, fi, 0, CFG)
    assert not r["collapsed"] and r["k"] == 0


def _calibration_modules():
    if CAL not in sys.path:
        sys.path.insert(0, CAL)
    import c0b_kernel  # noqa: F401
    import nulls       # noqa: F401
    return sys.modules["c0b_kernel"], sys.modules["nulls"]


def _agreement(n_traces, family="N1_iid", fold="A-G1"):
    K, N = _calibration_modules()
    fi = CFG["folds"][fold]["index"]
    KL = K.Layout(fold); E = K.Evaluator(KL)
    L = synthetic_layout(fold)
    O = offsets(L.Ns, fi, 0)
    out = []
    for i in range(n_traces):
        rng = np.random.default_rng([777, fi, N.FAMILIES.index(family), i, 0])
        x = N.gen(family, rng, KL.Ns, KL.P)
        prep = E.prepare(x)
        a_obs = E.area(prep, np.zeros(len(KL.Ns), np.int64))
        k_cal = sum(1 for b in range(200) if E.area(prep, O[b]) >= a_obs)
        r = c0b(x, L, fi, 0, CFG)
        out.append((k_cal, r["k"]))
    return out


def test_at15_agrees_with_calibration_kernel_first_traces():
    pairs = _agreement(8)
    assert all(a == b for a, b in pairs), pairs


@pytest.mark.slow
def test_at15_calibration_regression_cell():
    """Amendment C6: N1_iid, A-G1, 200 traces, seeds [777, 0, 0, i, 0]: 6 of 200 not collapsed."""
    pairs = _agreement(200)
    assert all(a == b for a, b in pairs)
    assert sum(1 for _, k in pairs if k < 10) == 6
