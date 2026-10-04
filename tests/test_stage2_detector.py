"""Section 6 feature path on CPU with random weights: our D4 path against the official PatchCore code (fcaa92f).
The real-weight, real-frame version of this comparison is AT-02 on Kaggle."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("faiss")             # the official common.py imports faiss at import time
pytest.importorskip("timm")              # the official backbones.py imports timm

from conftest import CFG                                     # noqa: E402
from tsfpilot import detector as D                           # noqa: E402
from tsfpilot.official import module                         # noqa: E402

H, W = 64, 80                            # layer2 grid 8 x 10, layer3 grid 4 x 5


@pytest.fixture(scope="module")
def nets():
    torch.manual_seed(0)
    ours = D.load_backbone("cpu", pretrained=False)
    theirs = D.load_backbone("cpu", pretrained=False)
    theirs.load_state_dict(ours.state_dict())                # same weights, separate object (official hooks attach to it)
    pc = module("patchcore").PatchCore("cpu")
    pc.load(backbone=theirs, layers_to_extract_from=["layer2", "layer3"], device="cpu", input_shape=(3, H, W),
            pretrain_embed_dimension=1024, target_embed_dimension=1024, patchsize=3)
    return ours, pc


@pytest.fixture(scope="module")
def frames():
    rng = np.random.default_rng(1)
    return rng.integers(0, 256, size=(3, H, W), dtype=np.uint8)


def test_unfold_order_matches_official_patchify():
    x = torch.randn(2, 5, 6, 7)
    official = module("patchcore").PatchMaker(3, stride=1).patchify(x)    # (B, L, C, 3, 3)
    assert torch.equal(D.unfold3(x), official.reshape(2 * 42, 5 * 9))


def test_feature_path_matches_official_embed(nets, frames):
    ours, pc = nets
    dcfg = CFG["detector"]
    x = D.to_input(frames, dcfg["imagenet_mean"], dcfg["imagenet_std"], "cpu")
    with torch.no_grad():
        l2, l3 = D.layer_outputs(ours, x)
        mine = D.patch_features(l2, l3, 1024).reshape(-1, 1024).numpy()
    ref = np.asarray(pc._embed(x))                                       # interpolate first, then MeanMapper
    assert mine.shape == ref.shape == (3 * 8 * 10, 1024)
    rel = np.abs(mine - ref).max() / np.abs(ref).max()
    assert rel <= 1e-5, rel


def test_layer_outputs_equal_the_hooked_official_layers(nets, frames):
    ours, pc = nets
    dcfg = CFG["detector"]
    x = D.to_input(frames, dcfg["imagenet_mean"], dcfg["imagenet_std"], "cpu")
    with torch.no_grad():
        l2, l3 = D.layer_outputs(ours, x)
        hooked = pc.forward_modules["feature_aggregator"](x)
    assert torch.allclose(l2, hooked["layer2"], rtol=0, atol=1e-5)
    assert torch.allclose(l3, hooked["layer3"], rtol=0, atol=1e-5)


def test_eval_mode_makes_frames_independent_of_their_batch(nets, frames):
    ours, _ = nets
    dcfg = CFG["detector"]
    with torch.no_grad():
        together = D.patch_features(*D.layer_outputs(ours, D.to_input(frames, dcfg["imagenet_mean"],
                                                                       dcfg["imagenet_std"], "cpu")), 1024)
        alone = D.patch_features(*D.layer_outputs(ours, D.to_input(frames[1:2], dcfg["imagenet_mean"],
                                                                    dcfg["imagenet_std"], "cpu")), 1024)
    rel = ((together[1] - alone[0]).abs().max() / alone[0].abs().max()).item()
    assert rel <= 1e-6, rel                  # same measure as AT-04b; on CPU about 4e-7 here


def test_input_tensor_is_gray_replicated_and_normalised():
    img = np.full((1, 4, 4), 255, np.uint8)
    dcfg = CFG["detector"]
    x = D.to_input(img, dcfg["imagenet_mean"], dcfg["imagenet_std"], "cpu")
    expected = [(1.0 - m) / s for m, s in zip(dcfg["imagenet_mean"], dcfg["imagenet_std"])]
    assert x.shape == (1, 3, 4, 4) and x.dtype == torch.float32
    assert np.allclose(x[0, :, 0, 0].numpy(), expected, atol=1e-6)


def test_full_resolution_shapes():
    """AT-01's shapes at 640 x 800, random weights (the GPU run repeats this with the real weights)."""
    torch.manual_seed(0)
    net = D.load_backbone("cpu", pretrained=False)
    img = np.zeros((640, 800), np.uint8)
    trace, l2, l3, f = D.shape_trace(net, img, CFG["detector"], "cpu")
    shapes = dict(trace)
    assert shapes["layer2"] == (1, 512, 80, 100)
    assert shapes["layer3"] == (1, 1024, 40, 50)
    assert shapes["features"] == (8000, 1024)
