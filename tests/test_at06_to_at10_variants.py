"""AT-06a, AT-07, AT-08, AT-09, AT-10 (sections 8 to 10). Synthetic maps and motion only."""
import math

import numpy as np
import pytest

from conftest import CFG
from tsfpilot.motion import HELD, RELIABLE, UNKNOWN, statuses
from tsfpilot.variants import aligned_map, plan, scenario_variants, unaligned_map, warp
from tsfpilot.windows import k_series, lag_perm, shifts_at

H, W = 80, 100


def reliable_motion(n, dx):
    dxa = np.full(n, float(dx)); dxa[0] = np.nan
    st = np.full(n, RELIABLE, np.int8); st[0] = UNKNOWN
    return dxa, st


# ---------------- AT-06a ----------------
def test_at06a_impulse():
    b, A, K = 2.0, 50.0, 8
    n = 12
    maps = np.full((n, H, W), b, np.float64)
    for f in range(n):
        x = 95 - 5 * f
        if 0 <= x < W:
            maps[f, 40, x] = A
    dxa, st = reliable_motion(n, -40.0)
    u = dxa / 8.0
    t = 11
    Us = shifts_at(u, t, K)
    assert Us == [5 * i for i in range(K)]
    mu0 = -999.0                       # any invalid read would show up
    v4 = aligned_map(maps, plan("V4", t, K, Us), mu0)
    rev = aligned_map(maps, plan("REV", t, K, Us), mu0)
    v2 = unaligned_map(maps, t, K)
    assert abs(v4[40, 40] - A) <= 1e-12
    assert abs(rev[40, 40] - (A + (K - 1) * b) / K) <= 1e-12
    assert abs(v2[40, 40] - (A + (K - 1) * b) / K) <= 1e-12


# ---------------- AT-07 ----------------
@pytest.fixture(scope="module")
def rand_maps():
    rng = np.random.default_rng(3)
    return rng.gamma(4.0, 1.0, (40, H, W)).astype(np.float32)


def test_at07_identities(rand_maps):
    n = rand_maps.shape[0]
    rng = np.random.default_rng(4)
    K = np.minimum(rng.integers(1, 26, n), np.arange(1, n + 1))
    # U forced to 0: dx = 0 everywhere -> V4 == V2 exactly
    dx0, st = reliable_motion(n, 0.0)
    v = scenario_variants(rand_maps, K, dx0, st, mu0=1.0, dx_oracle=np.zeros(n))
    assert np.max(np.abs(v["V4"] - v["V2"])) <= 1e-12
    # V1 == V0 when K = 1
    v1 = scenario_variants(rand_maps, np.ones(n, int), dx0, st, mu0=1.0, dx_oracle=np.zeros(n))
    assert np.max(np.abs(v1["V1"] - v1["V0"])) <= 1e-12
    # V2 == V0 for identical maps
    same = np.repeat(rand_maps[:1], n, axis=0)
    v2 = scenario_variants(same, K, dx0, st, mu0=1.0, dx_oracle=np.zeros(n))
    assert np.max(np.abs(v2["V2"] - v2["V0"])) <= 1e-12
    # lagperm == V4 when K <= 2
    dxm, stm = reliable_motion(n, -61.3)
    K2 = np.minimum(np.full(n, 2), np.arange(1, n + 1))
    v3 = scenario_variants(rand_maps, K2, dxm, stm, mu0=1.0, dx_oracle=np.full(n, -61.3))
    assert np.max(np.abs(v3["LAG"] - v3["V4"])) <= 1e-12
    # V4-reverse(a) == V4(mirror(a))
    va = scenario_variants(rand_maps, K, dxm, stm, mu0=1.0, dx_oracle=np.full(n, -61.3))
    vm = scenario_variants(rand_maps[:, :, ::-1].copy(), K, dxm, stm, mu0=1.0, dx_oracle=np.full(n, -61.3))
    known = ~va["mu"]
    assert known.sum() > 20
    assert np.max(np.abs(va["REV"][known] - vm["V4"][known])) <= 1e-12
    # map-level check of the mirror identity
    t, k = 30, 9
    Us = shifts_at(dxm / 8.0, t, k)
    a = aligned_map(rand_maps, plan("REV", t, k, Us), 1.0)
    m = aligned_map(rand_maps[:, :, ::-1].copy(), plan("V4", t, k, Us), 1.0)
    assert np.max(np.abs(a - m[:, ::-1])) <= 1e-12


# ---------------- AT-08 ----------------
def test_at08_lag_permutation():
    for K in range(1, 26):
        pi = lag_perm(K)
        assert sorted(pi) == list(range(K)) and pi[0] == 0
        if K >= 3:
            assert all(pi[i] != i for i in range(1, K))
            # a single (K-1)-cycle on 1..K-1
            seen, x = set(), 1
            for _ in range(K - 1):
                seen.add(x); x = pi[x]
            assert x == 1 and seen == set(range(1, K))
        assert all(p <= K - 1 for p in pi)


def test_at08_lag_terms_match_v4_and_misalignment_floor():
    rng = np.random.default_rng(8)
    for _ in range(400):
        K = int(rng.integers(3, 26)); n = K + 5
        dx = -rng.uniform(38, 161, n); dx[0] = np.nan
        u = dx / 8.0
        t = n - 1
        Us = shifts_at(u, t, K)
        v4 = plan("V4", t, K, Us); lag = plan("LAG", t, K, Us)
        # same shifts (so same validity masks, prior-fill counts and source columns) term by term
        assert [s for _, s in v4] == [s for _, s in lag]
        # same multiset of source frames
        assert sorted(f for f, _ in v4) == sorted(f for f, _ in lag)
        pi = lag_perm(K)
        for i in range(1, K):
            delta = Us[pi[i]] - Us[i]
            assert abs(delta) >= math.floor(abs(dx[t - i]) / 8) or i == K - 1
        # i = K - 1 maps to lag 1: its misalignment spans K - 2 frames of motion
        assert abs(Us[1] - Us[K - 1]) >= math.floor(min(abs(dx[1:])) / 8)


# ---------------- AT-09 ----------------
def _pipeline(maps, dx_raw, dy_raw, r_raw, has, mcfg, wcfg):
    st, dxv = statuses(dx_raw, dy_raw, r_raw, has, 0.3, mcfg)
    k, K = k_series(dxv, st, wcfg)
    v = scenario_variants(maps, K, dxv, st, mu0=1.5, with_oracle=False)
    return v, k, K, st


def test_at09_causality_and_k(rand_maps):
    rng = np.random.default_rng(9)
    n = rand_maps.shape[0]
    dx = -rng.uniform(80, 120, n); dy = rng.normal(0, 1, n); r = rng.uniform(0.2, 0.9, n)
    has = np.ones(n, bool); has[0] = False
    r[20:28] = 0.0                                  # 5 held frames, then 3 unknown frames
    mcfg, wcfg = CFG["motion"], CFG["windows"]
    v, k, K, st = _pipeline(rand_maps, dx, dy, r, has, mcfg, wcfg)
    assert (st == UNKNOWN).sum() == 4
    assert list(K[:3]) == [min(k[0], 1), min(k[1], 2), min(k[2], 3)]
    for t in (5, 17, 30):
        maps2 = rand_maps.copy(); maps2[t + 1:] = rng.gamma(4.0, 1.0, maps2[t + 1:].shape)
        dx2 = dx.copy(); dx2[t + 1:] = -rng.uniform(10, 300, n - t - 1)
        r2 = r.copy(); r2[t + 1:] = rng.uniform(0, 1, n - t - 1)
        v2, _, K2, _ = _pipeline(maps2, dx2, dy, r2, has, mcfg, wcfg)
        assert K2[t] == K[t]
        for name in ("V0", "V1", "V2", "V4", "REV", "LAG"):
            assert v2[name][t] == v[name][t]
    # motion-unknown fallback returns V2 exactly
    assert v["mu"].any()
    for name in ("V4", "REV", "LAG"):
        assert np.array_equal(v[name][v["mu"]], v["V2"][v["mu"]])


def test_motion_status_rules():
    mcfg = CFG["motion"]
    n = 30
    dx = np.full(n, -100.0); dy = np.zeros(n); r = np.full(n, 0.8); has = np.ones(n, bool); has[0] = False
    r[10:17] = 0.0                                 # 7 unreliable frames after reliable history
    st, dxv = statuses(dx, dy, r, has, 0.5, mcfg)
    assert st[0] == UNKNOWN
    assert all(st[1:10] == RELIABLE)
    assert list(st[10:15]) == [HELD] * 5 and all(dxv[10:15] == -100.0)
    assert list(st[15:17]) == [UNKNOWN] * 2
    # consistency: an outlier after >= 5 reliable estimates is not reliable
    dx2 = dx.copy(); dx2[20] = -150.0
    st2, _ = statuses(dx2, dy, r, has, 0.5, mcfg)
    assert st2[20] == HELD
    # k: 10 until 5 reliable estimates; 25 when stopped; floor(800/m + 0.5) otherwise
    st3 = np.full(n, RELIABLE, np.int8); st3[0] = UNKNOWN
    k, K = k_series(np.full(n, -100.0), st3, CFG["windows"])
    assert list(k[:5]) == [10] * 5 and k[5] == 8 and K[2] == 3
    k0, _ = k_series(np.zeros(n), st3, CFG["windows"])
    assert k0[10] == 25


# ---------------- AT-10 ----------------
def test_at10_prior_fill_counts():
    rng = np.random.default_rng(10)
    mu0 = -12345.0
    for _ in range(300):
        U = int(rng.integers(-130, 131))
        A = rng.uniform(0, 1, (H, W))
        w = warp(A, U, mu0)
        filled = int((w == mu0).sum())
        assert filled == 80 * min(abs(U), W)
        wr = warp(A, -U, mu0)
        assert np.array_equal(w == mu0, (wr == mu0)[:, ::-1])          # C-REV masks are mirrored
    # a whole aligned map: filled cells = 80 x sum_i #invalid columns(U_i)
    K, t = 9, 9
    maps = rng.uniform(0, 1, (10, H, W))
    Us = [0, 13, 27, 41, 55, 69, 83, 97, 111]
    cnt = sum(int((warp(maps[t - i], Us[i], mu0) == mu0).sum()) for i in range(K))
    assert cnt == 80 * sum(min(abs(x), W) for x in Us)
