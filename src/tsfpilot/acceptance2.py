"""Stage 2 acceptance tests (section 23: AT-01, AT-02, AT-03, AT-04a, AT-04b, AT-06b; fixtures fixed in DL-0013).

"rel" is max|a - b| / max|b| over all elements. Each function returns a JSON-ready record with "pass".
Tolerances and fixture sizes are the section 23 values; tests/test_stage2_spec.py checks them against the text.
"""
import numpy as np
import torch

from . import detector as D
from . import scoring as S
from .variants import warp
from .windows import shifts_at
from .motion import RELIABLE

AT01_FRAME = 1
AT02_FRAMES = tuple(range(1, 6))
AT02_REL = 1e-5
AT03_FRAME = 1
AT03_STRIDE = 4
AT03_QUERIES = 2000
AT03_REL = 1e-4
AT04_FRAMES = tuple(range(1, 11))
AT04B_REL = 1e-6
AT06B_PAIRS = 200
AT06B_MIN_HOLDING = 190            # 95% of 200


def rel(a, b):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return float(np.abs(a - b).max() / np.abs(b).max())


def at01(trace, map_shape):
    shapes = dict(trace)
    expected = {"layer2": (1, 512, 80, 100), "layer3": (1, 1024, 40, 50), "features": (8000, 1024)}
    ok = all(shapes[k] == v for k, v in expected.items()) and tuple(map_shape) == (80, 100)
    return {"test": "AT-01", "frame": AT01_FRAME, "trace": [[k, list(v)] for k, v in trace],
            "map_shape": list(map_shape), "pass": bool(ok)}


def official_patchcore(net, device):
    """The official PatchCore object (fcaa92f) around its own copy of the backbone. Its hooks attach to `net`,
    so `net` must not be the backbone used by the pipeline."""
    from .official import module
    pc = module("patchcore").PatchCore(device)
    pc.load(backbone=net, layers_to_extract_from=["layer2", "layer3"], device=device, input_shape=(3, 640, 800),
            pretrain_embed_dimension=1024, target_embed_dimension=1024, patchsize=3)
    return pc


def at02(net, pc, gate, dcfg, device):
    """D4 order (MeanMapper, then bilinear) against the official order (bilinear on unfolded features, then
    MeanMapper), one validation frame at a time."""
    worst = 0.0
    per_frame = []
    for f in AT02_FRAMES:
        batch = gate.batch("validation", None, [(gate.val_scenario, f)])
        ours = D.extract(net, batch.images, dcfg, device).reshape(-1, 1024).cpu().numpy()
        x = D.to_input(batch.images, dcfg["imagenet_mean"], dcfg["imagenet_std"], device)
        with torch.no_grad():
            ref = np.asarray(pc._embed(x))
        r = rel(ours, ref)
        per_frame.append({"frame": f, "rel": r})
        worst = max(worst, r)
    return {"test": "AT-02", "frames": list(AT02_FRAMES), "per_frame": per_frame, "max_rel": worst,
            "tolerance": AT02_REL, "pass": worst <= AT02_REL}


def at03(features_frame1, cs, fold, chunk=2000):
    """fp32 nearest squared distance against float64 brute force on 2,000 cells of validation frame 1.
    Argmin agreement is reported, not gated. A faiss IndexFlatL2 cross-check is added when faiss is installed."""
    q = features_frame1[::AT03_STRIDE]
    if len(q) != AT03_QUERIES:
        raise ValueError(f"expected {AT03_QUERIES} queries, got {len(q)}")
    d32, arg32 = S.nearest_sq_dist(q, cs, chunk, with_argmin=True)
    q64 = q.double()
    b64 = cs.vectors.double()
    d64 = torch.empty(len(q), dtype=torch.float64, device=q.device)
    arg64 = torch.empty(len(q), dtype=torch.int64, device=q.device)
    for i in range(len(q)):
        dist = ((b64 - q64[i]) ** 2).sum(dim=1)
        d64[i], arg64[i] = dist.min(dim=0)
    d32, d64 = d32.cpu().numpy(), d64.cpu().numpy()
    err = float(np.abs(d32 - d64).max() / d64.max())
    qn = (q64 * q64).sum(dim=1).cpu().numpy()
    rec = {"test": "AT-03", "fold": fold, "frame": AT03_FRAME, "cells": f"0, {AT03_STRIDE}, ..., 7996",
           "max_abs_err_over_max_d64": err, "tolerance": AT03_REL,
           "argmin_agreement": float((arg32.cpu() == arg64.cpu()).double().mean()), "pass": err <= AT03_REL,
           # diagnostics: the fp32 expansion loses accuracy when ||q||^2 is large compared with the distances
           # (validation queries only: no statistic of the coreset, which holds bank features, is recorded)
           "max_d64": float(d64.max()), "median_d64": float(np.median(d64)), "max_query_sqnorm": float(qn.max()),
           "max_abs_err": float(np.abs(d32 - d64).max())}
    try:
        import faiss
        index = faiss.IndexFlatL2(cs.vectors.shape[1])
        index.add(cs.vectors.cpu().numpy())
        dfa, _ = index.search(q.cpu().numpy(), 1)
        rec["faiss_rel_to_ours"] = rel(d32, dfa[:, 0])
    except ImportError:
        rec["faiss_rel_to_ours"] = None
    return rec


def maps_for(net, gate, frames, batch_size, coresets, dcfg, device):
    """Maps of validation frames under every coreset, in batches of `batch_size`. coresets: {(fold, seed): Coreset}."""
    out = {k: [] for k in coresets}
    for a in range(0, len(frames), batch_size):
        batch = gate.batch("validation", None, [(gate.val_scenario, f) for f in frames[a:a + batch_size]])
        feats = D.extract(net, batch.images, dcfg, device)
        for k, cs in coresets.items():
            out[k].append(S.anomaly_maps(feats, batch.purpose, cs))
    return {k: np.concatenate(v) for k, v in out.items()}


def at04a(net, gate, coresets, dcfg, device):
    first = maps_for(net, gate, AT04_FRAMES, dcfg["batch_size"], coresets, dcfg, device)
    second = maps_for(net, gate, AT04_FRAMES, dcfg["batch_size"], coresets, dcfg, device)
    per = {f"{k[0]} seed {k[1]}": bool(np.array_equal(first[k], second[k])) for k in coresets}
    return {"test": "AT-04a", "frames": list(AT04_FRAMES), "batch_size": dcfg["batch_size"],
            "bit_identical": per, "pass": all(per.values())}, first


def at04b(net, gate, coresets, dcfg, device, maps_batch4):
    single = maps_for(net, gate, AT04_FRAMES, 1, coresets, dcfg, device)
    per = {f"{k[0]} seed {k[1]}": rel(single[k], maps_batch4[k]) for k in coresets}
    f1 = D.extract(net, gate.batch("validation", None, [(gate.val_scenario, f) for f in AT04_FRAMES[:4]]).images,
                   dcfg, device)
    f2 = torch.cat([D.extract(net, gate.batch("validation", None, [(gate.val_scenario, f)]).images, dcfg, device)
                    for f in AT04_FRAMES[:4]])
    return {"test": "AT-04b", "frames": list(AT04_FRAMES), "rel_maps": per,
            "rel_features_frames_1_to_4": rel(f2.cpu().numpy(), f1.cpu().numpy()),
            "tolerance": AT04B_REL, "pass": max(per.values()) <= AT04B_REL}


def at06b_frames(status):
    """DL-0013: the earliest run of 200 consecutive reliable frames; if none exists, the first 200 reliable frames
    in time order. Returns (0-based frame indices t, each meaning the pair (t - 1, t), rule used)."""
    rel_idx = np.flatnonzero(np.asarray(status) == RELIABLE)
    run = 0
    for t in range(len(status)):
        run = run + 1 if status[t] == RELIABLE else 0
        if run == AT06B_PAIRS:
            return list(range(t - AT06B_PAIRS + 1, t + 1)), "consecutive run"
    if len(rel_idx) >= AT06B_PAIRS:
        return [int(t) for t in rel_idx[:AT06B_PAIRS]], "first reliable frames (no run of 200)"
    return None, f"only {len(rel_idx)} reliable frames"


def block_mean(img_u8):
    """(640, 800) uint8 -> (80, 100) float64, mean of each 8 x 8 block."""
    return np.asarray(img_u8, np.float64).reshape(80, 8, 100, 8).mean(axis=(1, 3))


def warp_prefers_forward(prev80, cur80, U):
    """MSE(img_t, W(img_(t-1), U)) < MSE(img_t, W(img_(t-1), -U)) on the columns valid for both shifts."""
    cols = np.arange(prev80.shape[1])
    both = (cols + U >= 0) & (cols + U <= 99) & (cols - U >= 0) & (cols - U <= 99)
    if not both.any():
        return False, np.nan, np.nan
    fwd = warp(prev80, U, 0.0)[:, both]
    rev = warp(prev80, -U, 0.0)[:, both]
    target = cur80[:, both]
    mse_f = float(np.mean((target - fwd) ** 2))
    mse_r = float(np.mean((target - rev) ** 2))
    return mse_f < mse_r, mse_f, mse_r


def at06b(gate, vmotion, fold, tau):
    if tau is None:
        return {"test": "AT-06b", "fold": fold, "applicable": False, "pass": None,
                "note": "tau_r undefined: the fold is motion-invalid and V4 always falls back to V2 (DL-0013)"}
    frames, rule = at06b_frames(vmotion["status"])
    if frames is None:
        return {"test": "AT-06b", "fold": fold, "applicable": True, "pass": False, "rule": rule}
    u = np.asarray(vmotion["dx"], np.float64) / 8.0
    holding, rows = 0, []
    cache = {}

    def img(frame):
        if frame not in cache:
            cache[frame] = block_mean(gate.validation_image(frame))
        return cache[frame]
    for t in frames:
        U = shifts_at(u, t, 2)[1]
        ok, mf, mr = warp_prefers_forward(img(t), img(t + 1), U)          # 0-based t is frame t + 1
        holding += int(ok)
        rows.append([t + 1, int(U), mf, mr, bool(ok)])
    return {"test": "AT-06b", "fold": fold, "applicable": True, "rule": rule, "frames": [frames[0] + 1,
            frames[-1] + 1], "holding": holding, "required": AT06B_MIN_HOLDING, "pairs": rows,
            "pass": holding >= AT06B_MIN_HOLDING}
