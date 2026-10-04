"""Stage 2 CPU tests: validation constants, the deployment rule, tau_r bookkeeping, AT-06b logic and the
section 23 numbers. Synthetic data only."""
import re

import numpy as np
import pytest

from conftest import CFG, REPO
from tsfpilot import acceptance2 as AT
from tsfpilot import stage2_motion as SM
from tsfpilot import validation as V
from tsfpilot.events import runs_direct
from tsfpilot.motion import HELD, RELIABLE, UNKNOWN


def test_map_constants_on_known_maps():
    rng = np.random.default_rng(0)
    maps = rng.random((12, 80, 100)).astype(np.float32)
    c = V.map_constants(maps)
    assert c["mu0"] == pytest.approx(float(maps.astype(np.float64).mean()), abs=1e-12)
    assert np.allclose(c["b1"], maps.astype(np.float64).mean(0))
    assert c["tau_cell"] == pytest.approx(np.percentile(maps.astype(np.float64), 99.9))
    assert c["b1_column_profile"].shape == (100,)
    corner = [max(x[0, 0], x[0, 1], x[1, 0], x[1, 1]) for x in maps.astype(np.float64)]   # clipped 3 x 3 max
    assert np.isclose(np.mean(corner), c["b3"][0, 0])


def test_map_constants_refuse_bad_maps():
    with pytest.raises(ValueError):
        V.map_constants(np.zeros((3, 80, 100), np.float64))
    bad = np.zeros((3, 80, 100), np.float32)
    bad[0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        V.map_constants(bad)


def direct_tau2(score, fa_max=2):
    """Smallest tau whose enveloped capped event count satisfies 1000 x Count <= 2 x N, by brute force."""
    N = len(score)
    T = [np.inf] + sorted(set(score), reverse=True)
    env = 0
    best = T[0]
    for tau in T:
        runs = runs_direct(score, np.zeros(N, int), np.ones(N, bool), tau)
        count = sum(-(-(b - a + 1) // 25) for a, b in runs)
        env = max(env, count)
        if 1000 * env <= fa_max * N:
            best = tau
    return best


@pytest.mark.parametrize("seed", range(20))
def test_tau2_threshold_matches_direct_definition(seed):
    rng = np.random.default_rng(seed)
    n = int(rng.integers(300, 1300))
    score = np.round(rng.random(n), 2)                                 # ties on purpose
    tau, _, _ = V.tau2_threshold(score, np.ones(n, bool))
    assert tau == direct_tau2(score)


def test_tau_r_record_counts_agree_with_the_rule():
    rng = np.random.default_rng(3)
    raw = {}
    for s in sorted(set().union(*(SM.access.tau_r_scenarios(CFG, f) for f in CFG["folds"]))):
        n = 400
        dx = -85 + rng.normal(0, 1, n)
        r = rng.uniform(0.3, 0.9, n)
        bad = rng.random(n) < 0.1
        dx[bad] = rng.uniform(-400, 400, bad.sum())
        r[bad] = rng.uniform(0.0, 0.35, bad.sum())
        has = np.ones(n, bool)
        has[0] = False
        raw[s] = (dx, np.zeros(n), r, has)
    for fold in CFG["folds"]:
        rec = SM.tau_r_record(raw, CFG, fold)
        assert rec["tau_r"] is not None
        assert rec["pairs_at_tau"] >= 1000 and 100 * rec["consistent_at_tau"] >= 95 * rec["pairs_at_tau"]
        assert set(rec["scenarios"]).isdisjoint(CFG["folds"][fold]["test"])


def test_at06b_frame_selection():
    st = np.full(600, RELIABLE, np.int8)
    st[0] = UNKNOWN
    st[50] = HELD
    frames, rule = AT.at06b_frames(st)
    assert rule == "consecutive run" and frames == list(range(51, 251))
    st2 = np.where(np.arange(600) % 3 == 0, HELD, RELIABLE).astype(np.int8)
    frames2, rule2 = AT.at06b_frames(st2)
    assert rule2.startswith("first reliable") and len(frames2) == 200 and frames2[0] == 1
    frames3, _ = AT.at06b_frames(np.full(150, RELIABLE, np.int8))
    assert frames3 is None


def textured_frames(dx_px, n=3, seed=0):
    """Frames of a smooth random texture moving by dx_px per frame: I_t(x) = I_(t-1)(x - dx)."""
    rng = np.random.default_rng(seed)
    width = 800 + abs(dx_px) * n + 64
    tex = rng.random((640, width))
    k = np.ones(9) / 9
    tex = np.apply_along_axis(lambda r: np.convolve(r, k, "same"), 1, tex)
    start = 0 if dx_px < 0 else dx_px * n
    return [(255 * tex[:, start - t * dx_px: start - t * dx_px + 800]).astype(np.uint8) for t in range(n)]


@pytest.mark.parametrize("dx", [-85, -39, -120])
def test_forward_warp_wins_on_a_moving_texture(dx):
    f0, f1 = textured_frames(dx, 2)
    U = int(np.floor(-dx / 8 + 0.5))
    ok, mse_f, mse_r = AT.warp_prefers_forward(AT.block_mean(f0), AT.block_mean(f1), U)
    assert ok and mse_f < mse_r
    ok_rev, _, _ = AT.warp_prefers_forward(AT.block_mean(f0), AT.block_mean(f1), -U)
    assert not ok_rev                                   # the wrong sign must lose


def test_section_23_numbers_match_the_preregistration():
    text = open(f"{REPO}/PREREGISTRATION.md").read()
    row = {m.group(1): m.group(0) for m in re.finditer(r"^\| (AT-0\d[ab]?) \|.*$", text, re.M)}
    assert "1 validation frame" in row["AT-01"]
    assert "5 validation frames" in row["AT-02"] and "rel <= 1e-5" in row["AT-02"]
    assert AT.AT02_REL == 1e-5 and len(AT.AT02_FRAMES) == 5
    assert "2,000 validation queries" in row["AT-03"] and "<= 1e-4" in row["AT-03"]
    assert AT.AT03_QUERIES == 2000 and AT.AT03_REL == 1e-4 and 8000 // AT.AT03_STRIDE == AT.AT03_QUERIES
    assert "10 validation frames" in row["AT-04a"] and "bit-identical" in row["AT-04a"]
    assert "rel <= 1e-6" in row["AT-04b"] and AT.AT04B_REL == 1e-6 and len(AT.AT04_FRAMES) == 10
    assert "200 consecutive reliable" in row["AT-06b"] and ">= 95% of pairs" in row["AT-06b"]
    assert AT.AT06B_PAIRS == 200 and AT.AT06B_MIN_HOLDING == 190
