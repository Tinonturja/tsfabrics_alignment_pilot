"""AT-05 (phase-correlation sign, magnitude, input safety) and the tau_r / oracle rules of section 7."""
import cv2
import numpy as np

from conftest import CFG
from tsfpilot.motion import RELIABLE, oracle_dx, phase_correlate, raw_scenario, standardise, tau_r


def texture(seed=5):
    rng = np.random.default_rng(seed)
    t = rng.normal(size=(640, 2000)).astype(np.float32)
    t = cv2.GaussianBlur(t, (0, 0), 3.0)
    t = (t - t.min()) / (t.max() - t.min()) * 255
    return t.astype(np.uint8)


def test_at05_sign_magnitude_and_inputs_untouched():
    tex = texture()
    prev = tex[:, 500:1300]
    for true_dx, a in ((-10, 510), (7, 493)):
        cur = tex[:, a:a + 800]                       # I_t(x) = I_(t-1)(x - dx)
        P, C = standardise(prev), standardise(cur)
        P0, C0 = P.copy(), C.copy()
        dx, dy, r = phase_correlate(P, C)
        assert abs(dx - true_dx) <= 0.1, (true_dx, dx)
        assert abs(dy) <= 0.1
        assert P.tobytes() == P0.tobytes() and C.tobytes() == C0.tobytes()
        assert 0 < r <= 1


def test_raw_scenario_on_synthetic_video():
    tex = texture(6)
    # frame i shows tex[:, 1100 - 40 i : 1900 - 40 i], so I_i(x) = I_(i-1)(x - 40): dx = +40 by the sign convention
    frames = [tex[:, 1100 - 40 * i:1900 - 40 * i] for i in range(20)]
    dx, dy, r, has = raw_scenario(frames)
    assert not has[0] and has[1:].all()
    assert np.all(np.abs(dx[1:] - 40) <= 0.2)
    frames_left = frames[::-1]                         # leftward motion -> dx = -40
    dxl, _, _, _ = raw_scenario(frames_left)
    assert np.all(np.abs(dxl[1:] + 40) <= 0.2)


def test_tau_r_rule():
    mcfg = CFG["motion"]
    rng = np.random.default_rng(1)
    n = 3000
    dx = np.full(n, -100.0) + rng.normal(0, 1, n); dy = np.zeros(n)
    r = rng.uniform(0, 1, n); has = np.ones(n, bool); has[0] = False
    bad = r < 0.3                                     # low-response pairs are wrong
    dx[bad] = rng.uniform(-400, 400, bad.sum())
    t = tau_r([(dx, dy, r, has)], mcfg)
    assert t is not None and 0.2 <= t <= 0.35
    assert tau_r([(dx[:900], dy[:900], r[:900], has[:900])], mcfg) is None      # fewer than 1000 pairs


def test_c0c_motion_invalid_rule():
    from tsfpilot.motion import motion_invalid
    ok = [np.zeros(380, bool), np.r_[np.ones(20, bool)]]            # 20 of 400 = exactly 5%: valid
    assert not motion_invalid(0.3, ok)
    bad = [np.zeros(379, bool), np.ones(21, bool)]                  # 21 of 400 = 5.25%: invalid
    assert motion_invalid(0.3, bad)
    assert motion_invalid(None, ok)                                 # tau_r undefined


def test_oracle_dx_needs_five_values():
    mcfg = CFG["motion"]
    n = 50
    dx = np.full(n, -80.0); st = np.zeros(n, np.int8)
    st[20:24] = RELIABLE                              # only 4 reliable values anywhere
    o = oracle_dx(dx, st, mcfg)
    assert np.isnan(o).all()
    st[24] = RELIABLE
    o = oracle_dx(dx, st, mcfg)
    assert np.isfinite(o[9]) and np.isnan(o[8])       # window [j-15, j+15] must contain frames 20..24
