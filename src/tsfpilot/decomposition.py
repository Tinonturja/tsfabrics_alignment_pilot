"""False-alarm decomposition C6 (section 16). EXPLORATORY: no role in C0 to C7 or any outcome.

Validation baselines per fold and seed: b1 = mean map; M3 = 3x3 maximum clipped at the borders; b3 = mean M3.
Events: V0's FA runs at tau*_V0 (V0's P1 threshold), each classified at its first frame t_e at
p = (y*, x*) = argmax a_(t_e) (first row-major index on ties). Uses future frames (declared; analysis only).
"""
import numpy as np

from .windows import shifts_at

CLASSES = ("global-driven", "ambiguous-geometry", "ambiguous-coincident", "diffuse", "camera-fixed",
           "persistent-local", "transient", "ambiguous")


def m3(a):
    """3x3 maximum, clipped at the borders (equivalent to scipy maximum_filter(size=3, mode='nearest'))."""
    p = np.pad(a, 1, mode="constant", constant_values=-np.inf)
    H, W = a.shape
    out = np.full((H, W), -np.inf)
    for dy in range(3):
        for dx in range(3):
            np.maximum(out, p[dy:dy + H, dx:dx + W], out=out)
    return out


def baselines(val_maps):
    b1 = np.mean(val_maps, axis=0, dtype=np.float64)
    b3 = np.mean([m3(np.asarray(v, np.float64)) for v in val_maps], axis=0)
    return b1, b3


def classify(maps, te, K_te, u, known, b1, b3, tau_star, dcfg):
    """maps: (N, 80, 100) of one scenario; te: 0-based first frame of the event; K_te = K_(t_e);
    u = dx / 8 per frame; known: bool motion-known per frame."""
    a = np.asarray(maps[te], np.float64)
    H, W = a.shape
    s = float(a.max())
    med_b1 = float(np.median(b1))
    if s - (float(np.median(a)) - med_b1) < tau_star:
        return "global-driven"
    ys, xs = np.unravel_index(int(np.argmax(a)), a.shape)       # argmax returns the first row-major index
    E0 = a[ys, xs] - b1[ys, xs]
    E0_min = dcfg["floor_fraction"] * (tau_star - med_b1)
    path = []
    for j in range(1, K_te + 1):
        t = te + j
        if t >= len(maps) or not all(known[te + 1:t + 1]):
            break
        x = xs - shifts_at(u, t, j + 1)[j]
        if not (0 <= x <= W - 1):
            break
        path.append((j, x))
    if len(path) < dcfg["min_path"] or E0 < E0_min:
        return "ambiguous-geometry"
    if all(abs(x - xs) <= 1 for _, x in path):
        return "ambiguous-coincident"
    M = {j: m3(np.asarray(maps[te + j], np.float64)) for j, _ in path}
    off = dcfg["null_row_offset"]
    rows = [r for r in (ys + off, ys - off) if 0 <= r < H]
    rho = float(np.median([(M[j][ys, x] - b3[ys, x]) / E0 for j, x in path]))
    rho0 = float(np.median([np.mean([M[j][r, x] - b3[r, x] for r in rows]) / E0 for j, x in path]))
    rcam = float(np.median([(M[j][ys, xs] - b3[ys, xs]) / E0 for j, _ in path]))
    if rho0 >= dcfg["diffuse"]:
        return "diffuse"
    if rcam >= dcfg["camera"] and rcam - rho0 >= dcfg["separation"] and rcam > rho:
        return "camera-fixed"
    if rho >= dcfg["persistent"] and rho - rho0 >= dcfg["separation"]:
        return "persistent-local"
    if rho < dcfg["transient"] and rcam < dcfg["transient"]:
        return "transient"
    return "ambiguous"
