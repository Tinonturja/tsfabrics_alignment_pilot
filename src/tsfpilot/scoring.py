"""Anomaly maps (section 6, Distance, Patch score, Frame score and Map rows; deviation D6).

a_t(r, c) = min over coreset vectors b of the squared L2 distance, computed as
max(0, ||q||^2 + ||b||^2 - 2 q.b) in float32 with TF32 off, queries in chunks of 2,000. This is the quantity
faiss.IndexFlatL2 returns, which is what the official scorer averages over n_nn = 1 neighbour.
Maps stay raw: (80, 100) float32, no upsampling, no blur (D3). The frame score s_t is the map maximum.

Only validation features may be scored in Stage 2 (section 24). Bank features carry purpose 'bank' and are refused.
"""
import numpy as np
import torch

from .detector import GRID


class Coreset:
    """A coreset on the scoring device with its squared norms precomputed."""

    def __init__(self, vectors, device):
        self.vectors = torch.as_tensor(np.ascontiguousarray(vectors), dtype=torch.float32, device=device)
        self.sqnorm = (self.vectors * self.vectors).sum(dim=1)


def nearest_sq_dist(queries, cs, chunk=2000, with_argmin=False):
    """Minimum squared distance of each query row (N, D) float32 to the coreset. Returns (N,) float32 tensor."""
    out = torch.empty(len(queries), dtype=torch.float32, device=queries.device)
    arg = torch.empty(len(queries), dtype=torch.int64, device=queries.device) if with_argmin else None
    for a in range(0, len(queries), chunk):
        q = queries[a:a + chunk]
        d = (q * q).sum(dim=1, keepdim=True) + cs.sqnorm[None, :] - 2.0 * (q @ cs.vectors.T)
        best = d.clamp_min_(0.0).min(dim=1)
        out[a:a + chunk] = best.values
        if with_argmin:
            arg[a:a + chunk] = best.indices
    return (out, arg) if with_argmin else out


def anomaly_maps(features, purpose, cs, chunk=2000):
    """features: (B, 8000, D) float32 tensor of one detector batch. Returns (B, 80, 100) float32 numpy maps."""
    if purpose != "validation":
        raise PermissionError(f"Stage 2 scores validation frames only; got purpose {purpose!r}")
    B = features.shape[0]
    d = nearest_sq_dist(features.reshape(-1, features.shape[-1]), cs, chunk)
    return d.reshape(B, *GRID).cpu().numpy()


def frame_scores(maps):
    return np.asarray(maps).reshape(len(maps), -1).max(axis=1)
