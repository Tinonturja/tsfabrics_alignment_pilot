"""PatchCore-derived feature path (section 6).

uint8 gray frame (640, 800) -> float32 / 255, three identical channels, ImageNet mean and std, no resize (D1, D2)
-> WRN-50-2 (IMAGENET1K_V1, eval, no gradients) -> layer2 (512, 80, 100) and layer3 (1024, 40, 50)
-> 3 x 3 patches (Unfold, stride 1, padding 1; flatten order (c, ki, kj)) -> MeanMapper to 1024 per layer
-> layer3 upsampled bilinearly (align_corners False) from 40 x 50 to 80 x 100 AFTER its MeanMapper (D4)
-> stack the two layers, Aggregator 2048 -> 1024 -> (8000, 1024) per frame, cell index 100 r + c.

The official code reads layer2 and layer3 with forward hooks and stops the network after layer3. Calling the
torchvision modules in order up to layer3 is the same computation; AT-02 compares this path with the official
PatchCore._embed on real validation frames.
"""
import hashlib
import os

import numpy as np
import torch
import torch.nn.functional as F

GRID = (80, 100)
LAYER3_GRID = (40, 50)


def set_determinism():
    """Section 6, Seeding row: deterministic cuDNN, no autotuning, no TF32 anywhere."""
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False


def determinism_flags():
    return {"cudnn.deterministic": torch.backends.cudnn.deterministic,
            "cudnn.benchmark": torch.backends.cudnn.benchmark,
            "cudnn.allow_tf32": torch.backends.cudnn.allow_tf32,
            "cuda.matmul.allow_tf32": torch.backends.cuda.matmul.allow_tf32}


def load_backbone(device, pretrained=True):
    """torchvision wide_resnet50_2 with IMAGENET1K_V1 weights, eval mode, frozen. pretrained=False gives random
    weights for the CPU tests only."""
    import torchvision
    weights = torchvision.models.Wide_ResNet50_2_Weights.IMAGENET1K_V1 if pretrained else None
    net = torchvision.models.wide_resnet50_2(weights=weights)
    net.eval().requires_grad_(False)
    return net.to(device)


def weights_file_sha256():
    """SHA-256 of the downloaded IMAGENET1K_V1 checkpoint, for the run record."""
    import torchvision
    url = torchvision.models.Wide_ResNet50_2_Weights.IMAGENET1K_V1.url
    path = os.path.join(torch.hub.get_dir(), "checkpoints", os.path.basename(url))
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return {"file": os.path.basename(url), "sha256": h.hexdigest()}


def to_input(images_u8, mean, std, device):
    """(B, H, W) uint8 -> (B, 3, H, W) float32, scaled to [0, 1] then ImageNet-normalised."""
    x = torch.from_numpy(np.ascontiguousarray(images_u8)).to(device=device, dtype=torch.float32) / 255.0
    x = x.unsqueeze(1).expand(-1, 3, -1, -1)
    m = torch.tensor(mean, dtype=torch.float32, device=device).view(1, 3, 1, 1)
    s = torch.tensor(std, dtype=torch.float32, device=device).view(1, 3, 1, 1)
    return (x - m) / s


def layer_outputs(net, x):
    """The torchvision ResNet forward pass up to layer3 (conv1, bn1, relu, maxpool, layer1, layer2, layer3)."""
    x = net.maxpool(net.relu(net.bn1(net.conv1(x))))
    l2 = net.layer2(net.layer1(x))
    l3 = net.layer3(l2)
    return l2, l3


def unfold3(x):
    """(B, C, H, W) -> (B * H * W, C * 9): one row per cell, columns in (c, ki, kj) order, c outermost."""
    B, C, H, W = x.shape
    u = F.unfold(x, kernel_size=3, stride=1, padding=1)          # (B, C * 9, H * W)
    return u.transpose(1, 2).reshape(B * H * W, C * 9)


def mean_map(rows, dim):
    """The official MeanMapper: adaptive average pooling of each flattened row to `dim` values."""
    return F.adaptive_avg_pool1d(rows.reshape(len(rows), 1, -1), dim).squeeze(1)


def patch_features(l2, l3, dim=1024):
    """(B, 8000, dim) features from the two layer outputs."""
    B = l2.shape[0]
    grid2, grid3 = tuple(l2.shape[2:]), tuple(l3.shape[2:])
    f2 = mean_map(unfold3(l2), dim)                                   # (B * 8000, dim)
    f3 = mean_map(unfold3(l3), dim)                                   # (B * 2000, dim) on the 40 x 50 grid
    f3 = f3.reshape(B, *grid3, dim).permute(0, 3, 1, 2)
    f3 = F.interpolate(f3, size=grid2, mode="bilinear", align_corners=False)   # D4: after MeanMapper
    f3 = f3.permute(0, 2, 3, 1).reshape(B * grid2[0] * grid2[1], dim)
    both = torch.stack([f2, f3], dim=1).reshape(len(f2), 1, 2 * dim)  # (N, 2, dim) flattened as the Aggregator does
    return F.adaptive_avg_pool1d(both, dim).reshape(B, grid2[0] * grid2[1], dim)


@torch.no_grad()
def extract(net, images_u8, dcfg, device):
    """Features (B, 8000, 1024) float32 on `device` for a batch of decoded frames."""
    x = to_input(images_u8, dcfg["imagenet_mean"], dcfg["imagenet_std"], device)
    l2, l3 = layer_outputs(net, x)
    if tuple(l2.shape[2:]) != GRID or tuple(l3.shape[2:]) != LAYER3_GRID:
        raise ValueError(f"unexpected feature grids {tuple(l2.shape)} and {tuple(l3.shape)}")
    return patch_features(l2, l3, dcfg["target_embed_dimension"])


@torch.no_grad()
def shape_trace(net, image_u8, dcfg, device):
    """Layer-by-layer shapes for one frame (the audit trace behind AT-01)."""
    x = to_input(image_u8[None], dcfg["imagenet_mean"], dcfg["imagenet_std"], device)
    trace = [("input", tuple(x.shape))]
    h = net.conv1(x)
    trace.append(("conv1", tuple(h.shape)))
    h = net.maxpool(net.relu(net.bn1(h)))
    trace.append(("maxpool", tuple(h.shape)))
    h = net.layer1(h)
    trace.append(("layer1", tuple(h.shape)))
    l2 = net.layer2(h)
    trace.append(("layer2", tuple(l2.shape)))
    l3 = net.layer3(l2)
    trace.append(("layer3", tuple(l3.shape)))
    trace.append(("unfold layer2", tuple(unfold3(l2).shape)))
    trace.append(("unfold layer3", tuple(unfold3(l3).shape)))
    f = patch_features(l2, l3, dcfg["target_embed_dimension"])
    trace.append(("features", tuple(f.shape[1:])))
    return trace, l2, l3, f[0]
