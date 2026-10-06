"""Synthetic calibration of motion candidate M1 (amendment v1.2.2, section 4). Label-free; reads no image or data file.

Generates the six families F1 to F6 exactly as section 4 specifies, evaluates the frozen rule and M1 on identical
arrays, pools counts over the 200 replicates of each family, and applies the three criteria. Writes result.json next
to this file. Nothing here is tuned: every constant comes from the adopted protocol or the frozen configuration.

Usage: python calibration/v1_2_2_m1/calibrate_m1.py [--workers N]
"""
import argparse
import datetime
import json
import os
import platform
import sys
from fractions import Fraction
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "src"))

from tsfpilot import config as C            # noqa: E402
from tsfpilot import motion as M            # noqa: E402

PROTOCOL = "docs/stage2/AMENDMENT_v1.2.2_PROTOCOL.md"
PROTOCOL_SHA256 = "276fe9838efb6f6e334705b131d16c93f5d3c8d681b23fba57e15bb3fa25a704"   # DL-0016
SEED = 20261007
N_FRAMES = 2000
N_REPLICATES = 200
WARMUP_LAST = 20             # frames 2 to 20 are warm-up (section 4, Sets; DL-0016 V-2)
FAMILIES = {1: "F1 steady", 2: "F2 alternating", 3: "F3 alternating + drops", 4: "F4 steady + failures",
            5: "F5 alternating + failures", 6: "F6 slow + drops"}


def trace(family, rep):
    """One synthetic trace. Returns dx, dy, r, has (frame t at index t - 1) and the event mask."""
    rng = np.random.default_rng([SEED, family, rep])
    noise = rng.normal(0, 2, N_FRAMES)
    u = rng.random(N_FRAMES)
    w = rng.uniform(-400, 400, N_FRAMES)
    k = rng.choice([-2, -1, 1, 2], N_FRAMES)
    t = np.arange(1, N_FRAMES + 1)
    if family in (1, 4):
        b = np.full(N_FRAMES, -118.0)
    elif family in (2, 3, 5):
        b = np.where(t % 2 == 0, -117.0, -140.0)
    else:
        b = np.full(N_FRAMES, -39.0)
    true = b.copy()
    event = np.zeros(N_FRAMES, bool)
    if family == 3:
        dbl = u < 0.01
        dup = (u >= 0.01) & (u < 0.015)
        true[dbl] = 2 * b[dbl]
        true[dup] = 0.0
        event = dbl | dup
    elif family == 6:
        dbl = u < 0.02
        tri = (u >= 0.02) & (u < 0.03)
        true[dbl] = 2 * b[dbl]
        true[tri] = 3 * b[tri]
        event = dbl | tri
    dx = true + noise
    if family in (4, 5):
        uni = u < 0.05
        ali = (u >= 0.05) & (u < 0.10)
        dx[uni] = w[uni]
        dx[ali] = b[ali] + 85 * k[ali]
        event = uni | ali
    has = np.ones(N_FRAMES, bool)
    has[0] = False                              # frame 1 has no estimate
    dx[0] = 0.0
    event[0] = False
    return dx, np.zeros(N_FRAMES), np.ones(N_FRAMES), has, event


def sets(event):
    """Event, clean frames as boolean masks over frames 1..2000, warm-up excluded from both."""
    after = np.arange(1, N_FRAMES + 1) > WARMUP_LAST
    affected = event.copy()
    affected[1:] |= event[:-1]
    return event & after, after & ~affected


def evaluate(args):
    family, rep = args
    mc = C.load()["motion"]
    dx, dy, r, has, event = trace(family, rep)
    ev, clean = sets(event)
    out = {}
    for name, flags_fn, status_fn in (("frozen", M.frozen_consistency_flags, M.statuses),
                                      ("m1", M.m1_consistency_flags, M.m1_statuses)):
        cons, _ = flags_fn(dx, dy, has, mc)
        st, _ = status_fn(dx, dy, r, has, 0.0, mc)
        rel = st == M.RELIABLE
        out[name] = {"clean_n": int(clean.sum()), "clean_consistent": int((cons & clean).sum()),
                     "clean_reliable": int((rel & clean).sum()),
                     "event_n": int(ev.sum()), "event_inconsistent": int((~cons & ev).sum()),
                     "event_not_reliable": int((~rel & ev).sum())}
    return family, out


def pooled(results):
    tot = {f: {rule: {} for rule in ("frozen", "m1")} for f in FAMILIES}
    for family, out in results:
        for rule, d in out.items():
            for key, v in d.items():
                tot[family][rule][key] = tot[family][rule].get(key, 0) + v
    return tot


def frac(a, b):
    return Fraction(a, b) if b else None


def criteria(tot):
    rows = []

    def add(name, family, measure, value, limit, ok):
        rows.append({"criterion": name, "family": FAMILIES[family], "measure": measure,
                     "value": None if value is None else float(value), "limit": float(limit), "pass": bool(ok)})

    for f in (1, 2, 6):
        d = tot[f]["m1"]
        for key, label in (("clean_consistent", "item 3 clean consistent"), ("clean_reliable", "item 4 clean reliable")):
            p = frac(d[key], d["clean_n"])
            add("1", f, label, p, 0.99, p is not None and p >= Fraction(99, 100))
    for f in (4, 5):
        d = tot[f]["m1"]
        for key, label in (("event_inconsistent", "item 3 event inconsistent"),
                           ("event_not_reliable", "item 4 event not reliable")):
            p = frac(d[key], d["event_n"])
            add("2", f, label, p, 0.90, p is not None and p >= Fraction(90, 100))
    for f in (1, 4):
        m, z = tot[f]["m1"], tot[f]["frozen"]
        for key, label in (("clean_consistent", "item 3 clean: M1 minus frozen"),
                           ("clean_reliable", "item 4 clean: M1 minus frozen")):
            diff = frac(m[key], m["clean_n"]) - frac(z[key], z["clean_n"])
            add("3", f, label, diff, -0.01, diff >= Fraction(-1, 100))
    m, z = tot[4]["m1"], tot[4]["frozen"]
    for key, label in (("event_inconsistent", "item 3 event: M1 minus frozen"),
                       ("event_not_reliable", "item 4 event: M1 minus frozen")):
        diff = frac(m[key], m["event_n"]) - frac(z[key], z["event_n"])
        add("3", 4, label, diff, -0.01, diff >= Fraction(-1, 100))
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 1)
    args = ap.parse_args()
    got = C.file_sha256(C.repo_path(PROTOCOL))
    if got != PROTOCOL_SHA256:
        raise SystemExit(f"protocol hash {got} differs from the adopted text (DL-0016)")
    cfg = C.load()
    jobs = [(f, r) for f in FAMILIES for r in range(N_REPLICATES)]
    with Pool(args.workers) as pool:
        results = pool.map(evaluate, jobs, chunksize=10)
    tot = pooled(results)
    rows = criteria(tot)
    verdict = "PASS" if all(r["pass"] for r in rows) else "FAIL"
    files = [os.path.relpath(__file__, REPO), "src/tsfpilot/motion.py"]
    rec = {"what": "v1.2.2 section 4 synthetic calibration of M1",
           "date_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "protocol_sha256": got, "config_sha256": cfg["_sha256"],
           "code_sha256": {p: C.file_sha256(C.repo_path(p)) for p in files},
           "python": platform.python_version(), "numpy": np.__version__,
           "seed": SEED, "frames": N_FRAMES, "replicates": N_REPLICATES, "warmup_last_frame": WARMUP_LAST,
           "verdict": verdict, "criteria": rows,
           "pooled_counts": {FAMILIES[f]: tot[f] for f in FAMILIES},
           "not_gated": "F3 is reported, not gated; frozen-rule proportions are reported for comparison"}
    path = os.path.join(HERE, "result.json")
    with open(path, "w") as fh:
        json.dump(rec, fh, indent=1)
    for f in FAMILIES:
        line = [FAMILIES[f].ljust(26)]
        for rule in ("frozen", "m1"):
            d = tot[f][rule]
            parts = [f"clean cons {100 * d['clean_consistent'] / d['clean_n']:.2f}%",
                     f"clean rel {100 * d['clean_reliable'] / d['clean_n']:.2f}%"]
            if d["event_n"]:
                parts += [f"event incons {100 * d['event_inconsistent'] / d['event_n']:.2f}%",
                          f"event not-rel {100 * d['event_not_reliable'] / d['event_n']:.2f}%"]
            line.append(f"{rule}: " + ", ".join(parts))
        print(" | ".join(line))
    for r in rows:
        print(f"criterion {r['criterion']} {r['family']:26s} {r['measure']:34s} {r['value']:+.5f} "
              f"limit {r['limit']:+.2f} {'PASS' if r['pass'] else 'FAIL'}")
    print(f"M1 calibration {verdict}; result {path} sha256 {C.file_sha256(path)}")


if __name__ == "__main__":
    main()
