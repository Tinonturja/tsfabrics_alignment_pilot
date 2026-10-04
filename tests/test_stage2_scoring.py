"""Section 6 distances on CPU: the fp32 expansion against float64 brute force, and the purpose guard."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from tsfpilot import scoring as S                               # noqa: E402


def brute64(q, b):
    q = q.astype(np.float64)
    b = b.astype(np.float64)
    return np.array([((b - x) ** 2).sum(axis=1).min() for x in q])


def test_squared_distance_matches_float64_brute_force():
    rng = np.random.default_rng(0)
    b = np.abs(rng.standard_normal((3000, 64))).astype(np.float32)        # non-negative like pooled ReLU features
    q = np.abs(rng.standard_normal((500, 64))).astype(np.float32)
    q[:5] = b[:5]                                                          # exact matches: distance 0
    cs = S.Coreset(b, "cpu")
    d32, arg = S.nearest_sq_dist(torch.from_numpy(q), cs, chunk=128, with_argmin=True)
    d64 = brute64(q, b)
    assert np.abs(d32.numpy() - d64).max() / d64.max() <= 1e-4            # the AT-03 criterion
    assert np.all(d32.numpy()[:5] >= 0) and np.allclose(d32.numpy()[:5], 0, atol=1e-4)
    assert (arg.numpy()[:5] == np.arange(5)).all()


def test_chunking_does_not_change_results():
    rng = np.random.default_rng(1)
    b = rng.standard_normal((700, 32)).astype(np.float32)
    q = torch.from_numpy(rng.standard_normal((333, 32)).astype(np.float32))
    cs = S.Coreset(b, "cpu")
    assert torch.equal(S.nearest_sq_dist(q, cs, chunk=50), S.nearest_sq_dist(q, cs, chunk=333))


def test_maps_shape_and_frame_score():
    rng = np.random.default_rng(2)
    cs = S.Coreset(rng.standard_normal((100, 16)).astype(np.float32), "cpu")
    f = torch.from_numpy(rng.standard_normal((2, 8000, 16)).astype(np.float32))
    m = S.anomaly_maps(f, "validation", cs)
    assert m.shape == (2, 80, 100) and m.dtype == np.float32
    assert np.array_equal(S.frame_scores(m), m.reshape(2, -1).max(1))


def test_bank_features_cannot_be_scored():
    cs = S.Coreset(np.zeros((4, 8), np.float32), "cpu")
    with pytest.raises(PermissionError):
        S.anomaly_maps(torch.zeros((1, 8000, 8)), "bank", cs)
