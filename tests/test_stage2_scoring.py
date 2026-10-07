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


def test_chunking_changes_results_only_by_float32_rounding():
    # Replaces a bit-exact version that failed on Kaggle's CPU image (DL-0020): BLAS may pick a different kernel
    # for a different matrix shape, so different chunk sizes can differ by one float32 rounding step.
    rng = np.random.default_rng(1)
    b = rng.standard_normal((700, 32)).astype(np.float32)
    q = torch.from_numpy(rng.standard_normal((333, 32)).astype(np.float32))
    cs = S.Coreset(b, "cpu")
    x, y = S.nearest_sq_dist(q, cs, chunk=50), S.nearest_sq_dist(q, cs, chunk=333)
    assert float((x - y).abs().max() / y.abs().max()) <= 1e-6
    assert torch.equal(S.nearest_sq_dist(q, cs, chunk=50), x)            # same chunking: bit-identical


def test_frame_maps_do_not_depend_on_batch_composition():
    # 8,000 cells per frame and chunks of 2,000 (config query_chunk) make every chunk lie inside one frame with the
    # same shape, so a frame's map is bit-identical whichever batch it is scored in.
    import inspect
    from conftest import CFG
    assert 8000 % CFG["detector"]["query_chunk"] == 0
    assert inspect.signature(S.anomaly_maps).parameters["chunk"].default == CFG["detector"]["query_chunk"]
    rng = np.random.default_rng(3)
    cs = S.Coreset(rng.standard_normal((300, 16)).astype(np.float32), "cpu")
    f = torch.from_numpy(rng.standard_normal((3, 8000, 16)).astype(np.float32))
    together = S.anomaly_maps(f, "validation", cs)
    alone = np.concatenate([S.anomaly_maps(f[i:i + 1], "validation", cs) for i in range(3)])
    assert np.array_equal(together, alone)


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
