"""Stage 2 acceptance tests (section 23: AT-01, AT-02, AT-03, AT-04a, AT-04b, AT-06b; fixtures fixed in DL-0013).
AT-03, AT-04b and AT-06b follow amendment v1.2.2, section 3 C2 to C4 (DL-0016).

"rel" is max|a - b| / max|b| over all elements. Each function returns a JSON-ready record with "pass".
Tolerances and fixture sizes are the section 23 and v1.2.2 values; tests check them against the texts and the
configuration (stage2_acceptance).
"""
import hashlib
import json
import math
import os

import numpy as np
import torch

from . import detector as D
from . import motion as M
from . import scoring as S
from .variants import warp
from .motion import RELIABLE

AT01_FRAME = 1
AT02_FRAMES = tuple(range(1, 6))
AT02_REL = 1e-5
AT03_FRAME = 1
AT03_STRIDE = 4
AT03_QUERIES = 2000
AT03_REL = 1e-4
AT03_FALLBACK_N = 1026             # v1.2.2 C3: 1,024 products plus the two additions combining the three terms
U32 = 2.0 ** -24
GAMMA = AT03_FALLBACK_N * U32 / (1 - AT03_FALLBACK_N * U32)
F64_TERM = 1024 * 2.0 ** -53       # relative error allowance of the float64 reference
AT04_FRAMES = tuple(range(1, 11))
AT04B_BATCH = 4                    # v1.2.2 C2: batches {1-4}, {5-8}, {9-10} against batch size 1
AT04B_FEATURES_REL = 1e-6
AT04B_MAPS_REL = 1e-4
AT06B_SCENARIOS = ("T1_S164_I192_1", "T1_S164_I193_1")   # v1.2.2 C4, in this order
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


def smallest_index_argmin(dist):
    """Index of the first minimum (the smallest-index minimiser of v1.2.2 C3)."""
    return int(torch.nonzero(dist == dist.min())[0, 0])


def at03_fallback_bound(q64, b64, arg64, arg32, d64):
    """v1.2.2 C3: E(b) = gamma_1026 (||q||^2 + ||b||^2 + 2 |q|.|b|) + 1,024 x 2^-53 x d64(q, b*), in float64.
    Returns max(E(b*), E(b^)) per query. |q|.|b| is the inner product of the absolute values."""
    qn = (q64 * q64).sum(dim=1)

    def E(idx):
        b = b64[idx]
        return GAMMA * (qn + (b * b).sum(dim=1) + 2 * (q64.abs() * b.abs()).sum(dim=1)) + F64_TERM * d64
    return torch.maximum(E(arg64), E(arg32))


def at03(features_frame1, cs, fold, chunk=2000):
    """fp32 nearest squared distance against float64 brute force on 2,000 cells of validation frame 1.
    Primary criterion (section 23): max|d32 - d64| / max d64 <= 1e-4. If it fails, the v1.2.2 C3 fallback decides:
    every query must satisfy |d32 - d64| <= max(E(b*), E(b^)). Both results are recorded. Argmin agreement is
    reported, not gated. A faiss IndexFlatL2 cross-check is added when faiss is installed."""
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
        arg64[i] = smallest_index_argmin(dist)
        d64[i] = dist[arg64[i]]
    arg32 = arg32.to(q.device).long()
    abs_err = (d32.double().to(q.device) - d64).abs()
    bound = at03_fallback_bound(q64, b64, arg64, arg32, d64)
    err = float(abs_err.max() / d64.max())
    primary = err <= AT03_REL
    fallback = bool((abs_err <= bound).all())
    ratio = (abs_err / bound).cpu().numpy()
    qn = (q64 * q64).sum(dim=1).cpu().numpy()
    d64n = d64.cpu().numpy()
    rec = {"test": "AT-03", "fold": fold, "frame": AT03_FRAME, "cells": f"0, {AT03_STRIDE}, ..., 7996",
           "max_abs_err_over_max_d64": err, "tolerance": AT03_REL, "primary_pass": bool(primary),
           "fallback": {"rule": "v1.2.2 C3", "n": AT03_FALLBACK_N, "gamma": GAMMA, "pass": fallback,
                        "queries_over_bound": int((abs_err > bound).sum()), "max_err_over_bound": float(ratio.max()),
                        "applied": not primary},
           "argmin_agreement": float((arg32 == arg64).double().mean()), "pass": bool(primary or fallback),
           # diagnostics: the fp32 expansion loses accuracy when ||q||^2 is large compared with the distances
           # (validation queries only: no statistic of the coreset, which holds bank features, is recorded)
           "max_d64": float(d64n.max()), "median_d64": float(np.median(d64n)), "max_query_sqnorm": float(qn.max()),
           "max_abs_err": float(abs_err.max())}
    try:
        import faiss
        index = faiss.IndexFlatL2(cs.vectors.shape[1])
        index.add(cs.vectors.cpu().numpy())
        dfa, _ = index.search(q.cpu().numpy(), 1)
        rec["faiss_rel_to_ours"] = rel(d32.cpu().numpy(), dfa[:, 0])
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


def batches(frames, size):
    return [list(frames[a:a + size]) for a in range(0, len(frames), size)]


def at04b_verdict(features_1, features_4, maps_1, maps_4):
    """v1.2.2 C2: both parts required. features_*: arrays over frames 1 to 10; maps_*: {(fold, seed): array}."""
    rf = rel(features_1, features_4)
    per = {f"{k[0]} seed {k[1]}": rel(maps_1[k], maps_4[k]) for k in maps_4}
    return {"rel_features": rf, "features_tolerance": AT04B_FEATURES_REL, "rel_maps": per,
            "maps_tolerance": AT04B_MAPS_REL,
            "pass": bool(rf <= AT04B_FEATURES_REL and max(per.values()) <= AT04B_MAPS_REL)}


def at04b(net, gate, coresets, dcfg, device, maps_batch4):
    """Validation frames 1 to 10, batch size 1 against batch size 4 ({1-4}, {5-8}, {9-10}). maps_batch4 are the
    AT-04a maps, computed with the same batch composition."""
    if dcfg["batch_size"] != AT04B_BATCH:
        raise ValueError(f"AT-04b compares against batch size {AT04B_BATCH}, config has {dcfg['batch_size']}")

    def feats(size):
        out = []
        for keys in batches(AT04_FRAMES, size):
            b = gate.batch("validation", None, [(gate.val_scenario, f) for f in keys])
            out.append(D.extract(net, b.images, dcfg, device).cpu().numpy())
        return np.concatenate(out)
    f4 = feats(AT04B_BATCH)
    f1 = feats(1)
    maps_1 = maps_for(net, gate, AT04_FRAMES, 1, coresets, dcfg, device)
    rec = at04b_verdict(f1, f4, maps_1, maps_batch4)
    return dict({"test": "AT-04b", "frames": list(AT04_FRAMES), "batches": batches(AT04_FRAMES, AT04B_BATCH)}, **rec)


def at06b_select(statuses):
    """v1.2.2 C4, from statuses alone. statuses: [(scenario, status array)] in the order I192, I193.
    1. the earliest run of 200 consecutive reliable frames in I192; 2. else in I193 (runs never cross scenarios);
    3. else the first 200 reliable frames of I192 in time order, then of I193; 4. else None (AT-06b FAIL).
    Returns ([(scenario, t)], rule) with t the 1-based reliable frame of the pair (t - 1, t)."""
    for scen, st in statuses:
        run = 0
        for i in range(len(st)):
            run = run + 1 if st[i] == RELIABLE else 0
            if run == AT06B_PAIRS:
                return [(scen, j + 1) for j in range(i - AT06B_PAIRS + 1, i + 1)], f"consecutive run in {scen}"
    chosen = []
    for scen, st in statuses:
        for i in np.flatnonzero(np.asarray(st) == RELIABLE):
            chosen.append((scen, int(i) + 1))
            if len(chosen) == AT06B_PAIRS:
                return chosen, "first reliable frames (no run of 200)"
    return None, f"only {len(chosen)} reliable frames in {', '.join(s for s, _ in statuses)}"


def block_mean(img_u8):
    """(640, 800) uint8 -> (80, 100) float64, mean of each 8 x 8 block."""
    return np.asarray(img_u8, np.float64).reshape(80, 8, 100, 8).mean(axis=(1, 3))


def _both_valid(ncols, U):
    cols = np.arange(ncols)
    return (cols + U >= 0) & (cols + U <= ncols - 1) & (cols - U >= 0) & (cols - U <= ncols - 1)


def warp_prefers_forward(prev80, cur80, U):
    """MSE(img_t, W(img_(t-1), U)) < MSE(img_t, W(img_(t-1), -U)) on the columns valid for both shifts.
    No column valid for both: the pair does not hold."""
    both = _both_valid(prev80.shape[1], U)
    if not both.any():
        return False, np.nan, np.nan
    fwd = warp(prev80, U, 0.0)[:, both]
    rev = warp(prev80, -U, 0.0)[:, both]
    target = cur80[:, both]
    mse_f = float(np.mean((target - fwd) ** 2))
    mse_r = float(np.mean((target - rev) ** 2))
    return mse_f < mse_r, mse_f, mse_r


def mse_zero_shift(prev80, cur80, U):
    """Reported, not gated: MSE between the two frames without warping, on the same columns as the comparison."""
    both = _both_valid(prev80.shape[1], U)
    if not both.any():
        return float("nan")
    return float(np.mean((cur80[:, both] - prev80[:, both]) ** 2))


def at06b_shift(dx_t):
    """U(t, 1) = floor(-dx_t / 8 + 0.5)."""
    return int(math.floor(-float(dx_t) / 8.0 + 0.5))


def _sha256_array(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def at06b(gate, raw, fold, tau, mcfg, out_dir):
    """v1.2.2 C4. raw: {scenario: (dx, dy, r, has_est)} from phase A. The selection is computed from statuses
    alone and written, with its hash, to out_dir before any image is read. Images come through the gate under
    purpose 'motion' and never reach the detector."""
    if tau is None:
        return {"test": "AT-06b", "fold": fold, "applicable": False, "pass": None,
                "note": "tau_r undefined: the fold is motion-invalid and V4 always falls back to V2 (DL-0013)"}
    statuses, dxs = [], {}
    for scen in AT06B_SCENARIOS:
        st, _ = M.statuses(*raw[scen], tau, mcfg)
        statuses.append((scen, st))
        dxs[scen] = np.asarray(raw[scen][0], np.float64)
    chosen, rule = at06b_select(statuses)
    selection = {"fold": fold, "tau_r": tau, "motion_rule": mcfg.get("rule", "frozen"), "rule": rule,
                 "scenarios": list(AT06B_SCENARIOS),
                 "status_sha256": {s: _sha256_array(st) for s, st in statuses},
                 "reliable_frames": {s: int(np.sum(st == RELIABLE)) for s, st in statuses},
                 "pairs": None if chosen is None else [[s, t, at06b_shift(dxs[s][t - 1])] for s, t in chosen]}
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"at06b_selection_{fold}.json")
    with open(path, "w") as f:
        json.dump(selection, f, indent=1)
    with open(path, "rb") as f:
        sel_sha = hashlib.sha256(f.read()).hexdigest()
    base = {"test": "AT-06b", "fold": fold, "applicable": True, "rule": rule, "selection_file": os.path.basename(path),
            "selection_sha256": sel_sha, "required": AT06B_MIN_HOLDING}
    if chosen is None:
        return dict(base, holding=0, pairs=[], **{"pass": False})
    cache = {}

    def img(scen, frame):
        if (scen, frame) not in cache:
            cache[(scen, frame)] = block_mean(gate.motion_image(fold, scen, frame))
        return cache[(scen, frame)]
    holding, rows = 0, []
    for scen, t, U in selection["pairs"]:
        prev, cur = img(scen, t - 1), img(scen, t)
        ok, mf, mr = warp_prefers_forward(prev, cur, U)
        holding += int(ok)
        rows.append([scen, t, U, mf, mr, mse_zero_shift(prev, cur, U), bool(ok)])
        if len(cache) > 4:
            cache.pop(next(iter(cache)))
    return dict(base, holding=holding, pairs=rows, columns=["scenario", "t", "U", "mse_U", "mse_minus_U",
                                                            "mse_zero_shift", "holds"],
                **{"pass": holding >= AT06B_MIN_HOLDING})
