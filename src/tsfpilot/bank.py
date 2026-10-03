"""Normal memory-bank frame selection (section 4; rule unchanged from v1.1 A6).

Eligible: label in {1, 2} and |f - d| > margin for every defect frame d (strict).
Capacity list: scan eligible frames ascending; take a frame if it is the first or f >= last + spacing.
Allocation: 100 per training-side group, scenarios in lexicographic order, water-fill (equal split, remainder to
the earliest, cap at capacity, redistribute the shortfall, repeat).
Selection: C[floor((j + 0.5) c / q)] for j = 0 .. q - 1.
Margins and spacings are the frozen table values (bank audit CSV).
"""
import numpy as np

from .frames import defect_frames


def eligible(labels, defects, margin, normal_labels=(1, 2)):
    N = len(labels)
    ok = np.isin(labels, normal_labels)
    if defects and margin is not None:
        d = np.asarray(defects)
        f = np.arange(1, N + 1)
        near = np.zeros(N, bool)
        for x in d:                                     # |f - d| <= margin is excluded
            lo, hi = max(1, x - margin), min(N, x + margin)
            near[lo - 1:hi] = True
        ok &= ~near
    return (np.flatnonzero(ok) + 1).tolist()


def capacity_list(elig, spacing):
    C = []
    for f in elig:
        if not C or f >= C[-1] + spacing:
            C.append(f)
    return C


def waterfill(total, caps):
    names = sorted(caps)
    q = {s: 0 for s in names}
    remaining = total
    while remaining > 0:
        open_ = [s for s in names if q[s] < caps[s]]
        if not open_:
            break
        share, rem = divmod(remaining, len(open_))
        given = 0
        for i, s in enumerate(open_):
            add = min(share + (1 if i < rem else 0), caps[s] - q[s])
            q[s] += add
            given += add
        remaining -= given
        if given == 0:
            break
    return q


def select(C, q):
    c = len(C)
    return [C[((2 * j + 1) * c) // (2 * q)] for j in range(q)]      # floor((j + 0.5) c / q), integer form


def build_bank(fold, cfg, labels_by_scen, table):
    """table: dict scenario -> (margin or None, spacing) from the frozen bank audit CSV.
    Returns dict with per-scenario eligible counts, capacities, quotas and selected frames."""
    fc = cfg["folds"][fold]
    out = {"eligible": {}, "capacity": {}, "quota": {}, "frames": {}}
    for group in sorted(fc["bank_groups"]):
        caps = {}
        clists = {}
        for s in sorted(fc["bank_groups"][group]):
            margin, spacing = table[s]
            lab = labels_by_scen[s]
            e = eligible(lab, defect_frames(lab, s, cfg["data"]["label_override"]), margin,
                         tuple(cfg["data"]["normal_labels"]))
            C = capacity_list(e, spacing)
            out["eligible"][s] = len(e)
            out["capacity"][s] = len(C)
            caps[s] = len(C)
            clists[s] = C
        q = waterfill(cfg["bank"]["per_group_total"], caps)
        for s, qs in q.items():
            out["quota"][s] = qs
            out["frames"][s] = select(clists[s], qs)
    return out
