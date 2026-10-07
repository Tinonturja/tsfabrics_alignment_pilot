"""Stage 2 motion: raw phase correlation on training-side scenarios, tau_r per fold, validation statuses.

Section 4 ("tau_r source"), section 7 items 1 to 5 and 9, section 8 (k_t, K_t). Label-free and detector-free.
Raw estimates (dx, dy, r) of a scenario do not depend on the fold, so each scenario is processed once. Only the
fold's own tau_r scenario list enters its tau_r. The per-frame arrays of the other fold's test scenarios are used
for nothing else.
"""
import itertools
import os
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from . import access
from . import motion as M
from .windows import k_series


def _fold_allowing(cfg, scenario):
    for fold in sorted(cfg["folds"]):
        if scenario in access.tau_r_scenarios(cfg, fold):
            return fold
    raise access.ForbiddenFrame(f"{scenario} is in no fold's tau_r list")


def _raw_worker(args):
    root, cfg, scenario, max_frames = args
    import cv2
    cv2.setNumThreads(1)
    gate = access.FrameGate(root, cfg)
    fold = _fold_allowing(cfg, scenario)
    frames = itertools.islice(gate.motion_frames(fold, scenario), max_frames)     # max_frames None = all
    dx, dy, r, has = M.raw_scenario(frames, tuple(cfg["motion"]["crop_rows"]), cfg["motion"]["std_min"])
    return scenario, {"dx": dx, "dy": dy, "r": r, "has_est": has}, gate.read_summary()


def raw_motion(root, cfg, out_dir, workers=2, max_frames=None):
    """Raw (dx, dy, r, has_est) for every scenario in either fold's tau_r list, saved as motion_<scenario>.npz.
    Existing files are reused, so an interrupted run resumes. max_frames is for smoke runs only."""
    os.makedirs(out_dir, exist_ok=True)
    scenarios = sorted(set().union(*(access.tau_r_scenarios(cfg, f) for f in cfg["folds"])))
    todo = [s for s in scenarios if not os.path.exists(os.path.join(out_dir, f"motion_{s}.npz"))]
    reads = []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for scenario, arrays, log in ex.map(_raw_worker, [(root, cfg, s, max_frames) for s in todo]):
            np.savez(os.path.join(out_dir, f"motion_{scenario}.npz"), **arrays)
            reads += log
    raw = {}
    for s in scenarios:
        z = np.load(os.path.join(out_dir, f"motion_{s}.npz"))
        raw[s] = (z["dx"], z["dy"], z["r"], z["has_est"])
    return raw, reads


def check_rule(cfg):
    """v1.2.2: the frozen section 7 rule is the only one in force (M1 not adopted, DL-0017)."""
    rule = cfg["motion"].get("rule", "frozen")
    if rule != "frozen":
        raise ValueError(f"motion rule {rule!r} is not implemented in Stage 2 (DL-0017)")


def tau_r_record(raw, cfg, fold):
    """tau_r for one fold (section 7 item 3) with the counts that justify it."""
    check_rule(cfg)
    mcfg = cfg["motion"]
    names = access.tau_r_scenarios(cfg, fold)
    tau = M.tau_r([raw[s] for s in names], mcfg)
    rs, cons = [], []
    for s in names:
        dx, dy, r, has = raw[s]
        prev = []
        for i in range(len(dx)):
            if not has[i]:
                continue
            c = abs(dx[i]) <= mcfg["max_abs_dx"] and abs(dy[i]) <= mcfg["max_abs_dy"]
            if c and len(prev) >= mcfg["consistency_min_history"]:
                c = M._consistent(dx[i], prev, mcfg)
            rs.append(r[i])
            cons.append(c)
            prev.append(float(dx[i]))
    rs, cons = np.asarray(rs), np.asarray(cons, bool)
    rec = {"fold": fold, "scenarios": names, "pairs": int(len(rs)), "tau_r": tau}
    if tau is not None:
        sel = rs >= tau
        rec.update(pairs_at_tau=int(sel.sum()), consistent_at_tau=int(cons[sel].sum()))
        if not (rec["pairs_at_tau"] >= mcfg["tau_r_min_pairs"]
                and 100 * rec["consistent_at_tau"] >= round(100 * mcfg["tau_r_min_consistent"]) * rec["pairs_at_tau"]):
            raise RuntimeError(f"{fold}: tau_r counts do not satisfy the rule that selected it")
    return rec


def frames_without_estimate(raw):
    """U-I1: frames after frame 1 with no phase-correlation estimate (constant crop, or the frame right after one)."""
    return {s: int((~v[3][1:]).sum()) for s, v in raw.items()}


def scenario_motion(raw_s, tau, cfg):
    """Statuses, dx, k_t, K_t and oracle dx of one scenario under a fold's tau_r (sections 7 and 8)."""
    check_rule(cfg)
    dx_raw, dy_raw, r_raw, has = raw_s
    status, dx = M.statuses(dx_raw, dy_raw, r_raw, has, tau, cfg["motion"])
    k, K = k_series(dx, status, cfg["windows"])
    return {"status": status, "dx": dx, "k": k, "K": K, "dx_oracle": M.oracle_dx(dx, status, cfg["motion"])}
