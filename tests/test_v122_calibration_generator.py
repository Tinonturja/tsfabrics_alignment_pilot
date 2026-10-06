"""Amendment v1.2.2 section 4: the synthetic generator and the frame sets follow the adopted text. No rule is
evaluated here."""
import importlib.util
import os

import numpy as np

from conftest import REPO

_spec = importlib.util.spec_from_file_location("calibrate_m1", os.path.join(REPO, "calibration", "v1_2_2_m1",
                                                                            "calibrate_m1.py"))
cal = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cal)


def draws(family, rep):
    rng = np.random.default_rng([20261007, family, rep])
    return (rng.normal(0, 2, 2000), rng.random(2000), rng.uniform(-400, 400, 2000),
            rng.choice([-2, -1, 1, 2], 2000))


def test_frame_one_has_no_estimate_and_r_dy_constant():
    for f in cal.FAMILIES:
        dx, dy, r, has, ev = cal.trace(f, 0)
        assert not has[0] and has[1:].all() and (r == 1).all() and (dy == 0).all() and not ev[0]


def test_bases_and_noise():
    t = np.arange(1, 2001)
    alt = np.where(t % 2 == 0, -117.0, -140.0)
    for f, base in ((1, np.full(2000, -118.0)), (2, alt), (6, None)):
        noise, u, w, k = draws(f, 3)
        dx, _, _, _, ev = cal.trace(f, 3)
        if base is not None:
            assert np.array_equal(dx[1:], (base + noise)[1:]) and not ev.any()


def test_drop_families():
    noise, u, w, k = draws(3, 5)
    dx, _, _, _, ev = cal.trace(3, 5)
    t = np.arange(1, 2001)
    b = np.where(t % 2 == 0, -117.0, -140.0)
    dbl, dup = u < 0.01, (u >= 0.01) & (u < 0.015)
    exp = np.where(dbl, 2 * b, np.where(dup, 0.0, b)) + noise
    assert np.array_equal(dx[1:], exp[1:]) and np.array_equal(ev[1:], (dbl | dup)[1:])
    noise, u, w, k = draws(6, 5)
    dx, _, _, _, ev = cal.trace(6, 5)
    dbl, tri = u < 0.02, (u >= 0.02) & (u < 0.03)
    exp = np.where(dbl, -78.0, np.where(tri, -117.0, -39.0)) + noise
    assert np.array_equal(dx[1:], exp[1:]) and np.array_equal(ev[1:], (dbl | tri)[1:])


def test_failure_families_replace_without_noise():
    for f in (4, 5):
        noise, u, w, k = draws(f, 9)
        dx, _, _, _, ev = cal.trace(f, 9)
        t = np.arange(1, 2001)
        b = np.full(2000, -118.0) if f == 4 else np.where(t % 2 == 0, -117.0, -140.0)
        uni, ali = u < 0.05, (u >= 0.05) & (u < 0.10)
        exp = np.where(uni, w, np.where(ali, b + 85 * k, b + noise))
        assert np.array_equal(dx[1:], exp[1:]) and np.array_equal(ev[1:], (uni | ali)[1:])


def test_sets():
    ev = np.zeros(2000, bool)
    ev[[9, 19, 99, 1999]] = True            # frames 10, 20, 100, 2000
    events, clean = cal.sets(ev)
    assert list(np.flatnonzero(events) + 1) == [100, 2000]
    assert not clean[:20].any()              # warm-up
    assert not clean[20] and clean[21]       # frame 21 follows the event at frame 20
    assert not clean[99] and not clean[100] and clean[101]
    assert not clean[1999] and clean.sum() == 1980 - 4
