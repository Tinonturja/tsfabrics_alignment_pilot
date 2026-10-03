"""AT-11 (metrics vs reference on 1,000 random timelines plus hand cases) and AT-13 (real layout, constant score)."""
import math
from fractions import Fraction as Fr

import numpy as np
import pytest

from conftest import import_ref
from tsfpilot.events import count_curve, count_curve_units, runs_direct
from tsfpilot.metrics import all_metrics, c0a_saturated, curve
from tsfpilot.passes import FoldLayout

ref = import_ref("ref_metrics")


def toy_layout(scen, isN, windows, tracks):
    """Minimal FoldLayout for random timelines. windows: list of (lo, hi) global inclusive; tracks: ids."""
    n = len(scen)
    tr = sorted(set(tracks))
    L = FoldLayout(fold="toy", names=[str(i) for i in range(int(scen.max()) + 1)], Ns=np.bincount(scen),
                   start=np.zeros(1, np.int64), n=n, scen=scen.astype(np.int32), local=np.arange(1, n + 1),
                   label=np.ones(n, np.int64), isN=isN.astype(bool), pass_ids=[f"p{i}" for i in range(len(windows))],
                   pass_scen=np.zeros(len(windows), int), s_glob=np.array([w[0] for w in windows]),
                   e_glob=np.array([w[1] for w in windows]), w_lo=np.array([w[0] for w in windows]),
                   w_hi=np.array([w[1] for w in windows]), pass_track=np.array([tr.index(t) for t in tracks]),
                   pass_labels=["[4]"] * len(windows), tracks=tr, carry=np.zeros(len(windows), bool))
    return L


def random_case(rng):
    n = int(np.exp(rng.uniform(np.log(30), np.log(4000))))
    scen = np.sort(rng.integers(0, 3, n))
    # place 1..12 disjoint windows; everything else is normal except a few random exclusions
    isN = rng.random(n) > 0.02
    windows, tracks = [], []
    pos = 0
    nw = int(rng.integers(1, 13))
    for _ in range(nw):
        lo = pos + int(rng.integers(0, max(2, n // nw))); hi = lo + int(rng.integers(0, 10))
        if hi >= n:
            break
        windows.append((lo, hi)); tracks.append(f"k{int(rng.integers(0, 3))}")
        isN[lo:hi + 1] = False
        pos = hi + 1
    if not windows:
        windows, tracks = [(n - 1, n - 1)], ["k0"]
        isN[n - 1] = False
    kind = rng.integers(0, 5)
    if kind == 0:
        s = rng.normal(size=n)
    elif kind == 1:
        s = rng.integers(0, 6, n).astype(float)                 # heavy ties
    elif kind == 2:
        s = np.convolve(rng.normal(size=n + 8), np.ones(9) / 9, "valid")[:n]
    elif kind == 3:
        s = np.round(rng.normal(size=n), 1)
        for lo, hi in windows:
            s[lo:hi + 1] += 3.0
    else:
        s = rng.normal(size=n)
        for lo, hi in windows:
            s[lo:hi + 1] += rng.uniform(0, 5)
    if not isN.any():
        isN[0] = True
    return s, scen, isN, windows, tracks


def test_at11_random_timelines_equal_reference():
    rng = np.random.default_rng(20261003)
    bad = []
    for case in range(1000):
        s, scen, isN, windows, tracks = random_case(rng)
        L = toy_layout(scen, isN, windows, tracks)
        got = all_metrics(s, L)
        exp = ref.all_metrics(s, scen, isN, [(a, b, t) for (a, b), t in zip(windows, tracks)])
        if (got["P1"], got["P1_censored"]) != exp["P1"] or got["P2"] != exp["P2"] or got["P3"] != exp["P3"]:
            bad.append(case)
        assert isinstance(got["P3"], Fr) and isinstance(got["P2"], Fr) and isinstance(got["P1"], Fr)
    assert bad == []


def test_at11_event_sweep_equals_direct_definition():
    rng = np.random.default_rng(7)
    for _ in range(500):
        n = int(rng.integers(5, 120))
        s = rng.integers(0, 6, n).astype(float)
        isN = rng.random(n) > 0.15
        scen = np.sort(rng.integers(0, 3, n))
        T = np.concatenate([[np.inf], np.unique(s)[::-1]])
        cnt = count_curve(s, scen, isN, T, cap=4)
        for j, tau in enumerate(T):
            exp = sum(math.ceil((b - a + 1) / 4) for a, b in runs_direct(s, scen, isN, tau))
            assert cnt[j] == exp


def test_at11_unit_attribution_sums_to_total():
    rng = np.random.default_rng(11)
    for _ in range(300):
        n = int(rng.integers(20, 400))
        s = np.convolve(rng.normal(size=n + 20), np.ones(21) / 21, "valid")[:n]
        isN = rng.random(n) > 0.05
        scen = np.sort(rng.integers(0, 2, n))
        unit = (np.arange(n) // int(rng.integers(5, 60))).astype(np.int64)
        T = np.concatenate([[np.inf], np.unique(s)[::-1]])
        cnt, U = count_curve_units(s, scen, isN, T, unit, int(unit.max()) + 1, cap=25)
        assert np.array_equal(U.sum(1), cnt)
        # chunk rule at one threshold, checked directly
        j = len(T) // 2
        exp = np.zeros(int(unit.max()) + 1, int)
        for a, b in runs_direct(s, scen, isN, T[j]):
            for c0 in range(a, b + 1, 25):
                exp[unit[c0]] += 1
        assert np.array_equal(U[j], exp)


def test_at11_hand_cases():
    # section 15 reference cases, through the implementation
    s = np.r_[np.arange(10.0), [-1, -1, -1], [8.5], [-1], [3.5]]
    isN = np.r_[np.ones(10, bool), np.zeros(6, bool)]
    scen = np.zeros(len(s), int)
    L = toy_layout(scen, isN, [(13, 13), (15, 15)], ["a", "b"])
    m = all_metrics(s, L)
    assert (m["P3"], m["P1"], m["P1_censored"], m["P2"]) == (Fr(0), Fr(50), True, Fr(0))
    s2 = s.copy(); s2[13] = 100; s2[15] = 100
    m = all_metrics(s2, L)
    assert (m["P1"], m["P1_censored"], m["P2"], m["P3"]) == (Fr(0), False, Fr(1), Fr(1))
    s3 = s.copy(); s3[13] = 100; s3[15] = -0.5
    assert all_metrics(s3, L)["P3"] == Fr(1, 2)
    s4 = np.r_[np.zeros(1000), [5.0]]; s4[500] = 5.0
    isN4 = np.r_[np.ones(1000, bool), [False]]
    L4 = toy_layout(np.zeros(1001, int), isN4, [(1000, 1000)], ["a"])
    assert all_metrics(s4, L4)["P3"] == Fr(9, 10)


def test_c0a_integer_rule():
    # 19/20 of passes detected at tau_2 -> saturated; 18/20 -> not
    n = 200
    scen = np.zeros(n + 40, int)
    isN = np.r_[np.ones(n, bool), np.zeros(40, bool)]
    windows = [(n + 2 * i, n + 2 * i) for i in range(20)]
    s = np.r_[np.zeros(n), np.zeros(40)]
    for i, (a, _) in enumerate(windows):
        s[a] = 1.0 if i < 19 else -1.0
    L = toy_layout(scen, isN, windows, [f"t{i}" for i in range(20)])
    assert c0a_saturated(curve(s, L))
    s[windows[18][0]] = -1.0
    assert not c0a_saturated(curve(s, L))


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_at13_constant_score_gives_zero_p3(layouts, fold):
    L = layouts[fold]
    s = np.zeros(L.n)
    m = all_metrics(s, L)
    assert m["P3"] == 0
    # D = 25 rule active: at tau = 0 every N_f run counts ceil(L / 25), not 1
    c = m["curve"]
    runs = runs_direct(s, L.scen, L.isN, 0.0)
    capped = sum(math.ceil((b - a + 1) / 25) for a, b in runs)
    assert c.C[-1] == capped and capped > len(runs)


@pytest.mark.parametrize("fold", ["A-G1", "A-G4"])
def test_at11_real_layout_equals_reference(layouts, fold):
    L = layouts[fold]
    rng = np.random.default_rng(31)
    passes = [(int(a), int(b), L.tracks[k]) for a, b, k in zip(L.w_lo, L.w_hi, L.pass_track)]
    for kind in range(2):
        x = rng.normal(size=L.n)
        if kind == 1:
            x = np.convolve(rng.normal(size=L.n + 24), np.ones(25) / 25, "valid")[:L.n]
            for a, b in zip(L.s_glob, L.e_glob):
                x[a:b + 1] += 0.3
        got = all_metrics(x, L)
        exp = ref.all_metrics(x, L.scen, L.isN, passes)
        assert (got["P1"], got["P1_censored"]) == exp["P1"] and got["P2"] == exp["P2"] and got["P3"] == exp["P3"]
