"""Section 6 coreset rules on synthetic features (CPU): the chunked projection (D5) changes nothing, the seed
fully determines the result, and saved coresets are hash-checked."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from tsfpilot import coreset as CS                              # noqa: E402
from tsfpilot.official import module                            # noqa: E402

DCFG = {"coreset_percentage": 0.01, "coreset_starting_points": 10, "coreset_projection_dim": 128,
        "coreset_chunk_rows": 3000}


@pytest.fixture(scope="module")
def feats():
    rng = np.random.default_rng(7)
    return rng.standard_normal((20000, 256)).astype(np.float32)


def official_indices(features, seed):
    """The unmodified official sampler, seeded the same way, with its indices captured."""
    sampler = module("sampler").ApproximateGreedyCoresetSampler(0.01, "cpu", 10, 128)
    captured = {}
    original = sampler._compute_greedy_coreset_indices

    def keep(f):
        captured["idx"] = original(f)
        return captured["idx"]
    sampler._compute_greedy_coreset_indices = keep
    CS.seed_everything(seed)
    sampler.run(features)
    return captured["idx"]


def test_chunked_projection_gives_the_official_coreset(feats):
    idx, vec = CS.build(feats, 0, DCFG, "cpu")
    assert np.array_equal(idx, official_indices(feats, 0))
    assert np.array_equal(vec, feats[idx]) and len(idx) == 200


def test_seed_determines_the_coreset(feats):
    a, _ = CS.build(feats, 1, DCFG, "cpu")
    b, _ = CS.build(feats, 1, DCFG, "cpu")
    c, _ = CS.build(feats, 2, DCFG, "cpu")
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_projection_weights_are_the_official_ones(feats):
    """Same seed, same Linear weights: the projection of the first rows equals the official unchunked one."""
    torch.manual_seed(3)
    ours = CS.make_sampler(DCFG, "cpu")._reduce_features(torch.from_numpy(feats))
    torch.manual_seed(3)
    theirs = module("sampler").ApproximateGreedyCoresetSampler(0.01, "cpu", 10, 128)._reduce_features(
        torch.from_numpy(feats))
    assert torch.allclose(ours, theirs.detach(), rtol=0, atol=1e-5)


def test_index_to_source():
    rows = [("G2", "S_a", 5), ("G2", "S_a", 9), ("G3", "S_b", 2)]
    assert CS.index_to_source([0, 8000 + 101, 16000 + 7999], rows) == [
        ("S_a", 5, 0, 0), ("S_a", 9, 1, 1), ("S_b", 2, 79, 99)]


def test_saved_coreset_is_hash_checked(tmp_path, feats):
    idx, vec = CS.build(feats, 0, DCFG, "cpu")
    rec = CS.save(str(tmp_path), "A-G1", 0, idx, vec, {"note": "synthetic"})
    i2, v2 = CS.load(str(tmp_path), "A-G1", 0, rec)
    assert np.array_equal(i2, idx) and np.array_equal(v2, vec)
    v2[0, 0] += 1
    np.save(tmp_path / "coreset_A-G1_seed0_vectors.npy", v2)
    with pytest.raises(ValueError, match="hashes"):
        CS.load(str(tmp_path), "A-G1", 0, rec)
