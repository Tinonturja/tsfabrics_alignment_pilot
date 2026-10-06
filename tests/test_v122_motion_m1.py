"""Amendment v1.2.2, section 3 C1: motion candidate M1, and the frozen-rule flag function used by the section 4
calibration (DL-0016, V-1)."""
import numpy as np
import pytest

from conftest import CFG
from tsfpilot import motion as M

MC = CFG["motion"]


def scenario(rng, n, base, fail=0.1, r_spread=True):
    dx = base + rng.normal(0, 2, n)
    bad = rng.random(n) < fail
    dx[bad] = rng.uniform(-450, 450, bad.sum())
    dy = rng.normal(0, 1, n)
    dy[rng.random(n) < 0.02] = 30.0
    r = rng.random(n) if r_spread else np.ones(n)
    r[bad] *= 0.6                 # failures tend to have a lower response, so tau_r varies between seeds
    has = np.ones(n, bool)
    has[0] = False
    has[rng.random(n) < 0.01] = False
    return dx, dy, r, has


@pytest.mark.parametrize("min_pairs", [1000, 50])
def test_frozen_flags_reproduce_tau_r(min_pairs):
    mc = dict(MC, tau_r_min_pairs=min_pairs)
    seen = set()
    for seed in range(40):
        rng = np.random.default_rng([7, seed])
        scen = [scenario(rng, 700, b, fail=rng.uniform(0, 0.3)) for b in (-118, -39, -86)]
        rs, cons = [], []
        for dx, dy, r, has in scen:
            f, est = M.frozen_consistency_flags(dx, dy, has, mc)
            rs.extend(r[est]); cons.extend(f[est])
        expected = M.tau_r(scen, mc)
        assert M.grid_tau(rs, cons, mc) == expected
        seen.add(expected)
    assert len(seen) > 2          # the comparison covered several tau values, including undefined ones


def test_two_frame_sum_defined_only_with_both_estimates():
    dx = np.array([0.0, -10, -20, -30, -40])
    has = np.array([False, True, True, False, True])
    s = M.two_frame_sum(dx, has)
    assert np.isnan(s[0]) and np.isnan(s[1]) and s[2] == -30 and np.isnan(s[3]) and np.isnan(s[4])


def test_band_is_choice_b():
    assert M.m1_band(-236.0, MC) == pytest.approx(23.6)
    assert M.m1_band(-78.0, MC) == 8
    assert M.m1_band(0.0, MC) == 8


def alternating(n=200):
    dx = np.where(np.arange(1, n + 1) % 2 == 0, -116.0, -142.0)
    has = np.ones(n, bool); has[0] = False
    return dx, np.zeros(n), np.ones(n), has


def test_alternation_passes_m1_and_fails_frozen():
    dx, dy, r, has = alternating()
    f1, est = M.m1_consistency_flags(dx, dy, has, MC)
    assert f1[est].all()
    st, _ = M.m1_statuses(dx, dy, r, has, 0.0, MC)
    assert (st[2:] == M.RELIABLE).all() and st[0] == M.UNKNOWN and st[1] == M.UNKNOWN
    f0, _ = M.frozen_consistency_flags(dx, dy, has, MC)
    assert not f0[est].all()


def test_isolated_error_flags_two_sums():
    n = 60
    dx = np.full(n, -118.0); has = np.ones(n, bool); has[0] = False
    dx[30] = -60.0
    f, _ = M.m1_consistency_flags(dx, np.zeros(n), has, MC)
    assert not f[30] and not f[31] and f[29] and f[32]
    st, _ = M.m1_statuses(dx, np.zeros(n), np.ones(n), has, 0.0, MC)
    assert st[30] == M.HELD and st[31] == M.HELD and st[32] == M.RELIABLE


def test_band_boundary_is_inclusive():
    n = 30
    dx = np.full(n, -118.0); has = np.ones(n, bool); has[0] = False
    # median S = -236, B = 23.6; the sum at frame 21 (index 20) is dx[20] + dx[19]
    for delta, ok in ((23.5, True), (23.7, False), (-23.5, True), (-23.7, False)):
        d = dx.copy(); d[20] = -118.0 + delta
        f, _ = M.m1_consistency_flags(d, np.zeros(n), has, MC)
        assert bool(f[20]) is ok, delta


def test_h3_keeps_inconsistent_sums_h4_keeps_reliable_only():
    n = 40
    dx = np.full(n, -118.0); has = np.ones(n, bool); has[0] = False
    dx[10:13] = -300.0            # three bad frames make four bad sums
    f, _ = M.m1_consistency_flags(dx, np.zeros(n), has, MC)
    assert not f[10:14].any() and f[14:].all()
    st, _ = M.m1_statuses(dx, np.zeros(n), np.ones(n), has, 0.0, MC)
    assert (st[10:14] != M.RELIABLE).all() and (st[14:] == M.RELIABLE).all()


def test_predecessor_must_pass_basic_checks():
    n = 40
    dx = np.full(n, -118.0); dy = np.zeros(n); r = np.ones(n); has = np.ones(n, bool); has[0] = False
    r[20] = 0.1                   # frame 21 fails r >= tau, so frame 22 cannot be reliable
    st, _ = M.m1_statuses(dx, dy, r, has, 0.5, MC)
    assert st[20] == M.HELD and st[21] == M.HELD and st[22] == M.RELIABLE
    dy2 = dy.copy(); dy2[25] = 17.0
    st, _ = M.m1_statuses(dx, dy2, r, has, 0.5, MC)
    assert st[25] == M.HELD and st[26] == M.HELD


def test_held_and_unknown_rules_unchanged():
    n = 40
    dx = np.full(n, -118.0); has = np.ones(n, bool); has[0] = False
    has[10:20] = False
    st, dxv = M.m1_statuses(dx, np.zeros(n), np.ones(n), has, 0.0, MC)
    st0, _ = M.statuses(dx, np.zeros(n), np.ones(n), has, 0.0, MC)
    assert (st[10:15] == M.HELD).all() and (st[15:21] == M.UNKNOWN).all() and st[21] == M.RELIABLE
    assert (st0[10:15] == M.HELD).all() and (st0[15:20] == M.UNKNOWN).all()
    assert np.all(dxv[10:15] == -118.0)
    st, dxv = M.m1_statuses(dx, np.zeros(n), np.ones(n), has, None, MC)
    assert (st == M.UNKNOWN).all() and np.isnan(dxv).all()


def test_m1_tau_r_is_grid_rule_on_m1_flags():
    rng = np.random.default_rng(3)
    scen = [scenario(rng, 900, b, fail=0.05) for b in (-118, -39)]
    rs, cons = [], []
    for dx, dy, r, has in scen:
        f, est = M.m1_consistency_flags(dx, dy, has, MC)
        rs.extend(r[est]); cons.extend(f[est])
    assert M.m1_tau_r(scen, MC) == M.grid_tau(rs, cons, MC)
